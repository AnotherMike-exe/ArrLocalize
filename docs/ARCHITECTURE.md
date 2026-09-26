# Architecture — ArrLocalize

How this project is built and why. `README.md` says what it does. This file says what
somebody must understand before they change it.

## Shape

A single container on the media server, next to Radarr and Sonarr. supervisord runs one
loop. Every `LOCALIZE_INTERVAL` seconds the loop makes one pass over each configured
instance. The container shares the `/media` and debrid mounts with Radarr, at the same
paths, so a path from the API is a path that it can open.

## Components

| Component | Does | Built with |
|---|---|---|
| `localize.plan()` | finds the tagged titles and makes the list of actions for each | Python |
| `localize.copy_over_link()` | copies the debrid file to a partial file, then swaps it over the link | Python stdlib |
| `cli.one_pass()` | plans every instance, writes the rollback record, runs the titles | Python |
| `history` | writes and reads the rollback records | JSON files |
| `ArrClient` | the Sonarr and Radarr v3 API | `arr-service` |
| supervisord | keeps the loop running and writes the log | Alpine package |

## Data flow

One Seerr request, from start to end:

```
Jellyfin search -> Seerrfin -> Seerr request
  -> Radarr adds the movie with tag "seerr"
  -> Radarr sends the grab to the client with tag "seerr": Decypharr
  -> Decypharr gives a symlink into the debrid mount, Radarr imports it (seconds)
  -> the user watches it from debrid
ArrLocalize pass:
  -> GET tag, GET movie -> the movie has "seerr" and its file is a symlink
  -> write /config/history/<stamp>.json
  -> copy the debrid file to <name>.localize.partial, fsync, check the size
  -> os.replace() the partial file over the symlink
  -> POST command RescanMovie
  -> PUT movie/editor, remove "seerr"
Later grabs for the movie have no tag -> they go to qBittorrent
```

A series is the same, with `GET episodefile` and `GET episode`. The tag comes off only
when every monitored episode that aired has a file, and every file is local.

## Data

| Store | Holds | Lives at | Survives a rebuild |
|---|---|---|---|
| Rollback records | each title's tags and each original link path and target | `/config/history/*.json` | yes, `/config` is a volume |
| Log | every plan and action | `/config/supervisord.log` | yes |

There is no schema and no migration. A record is only read by `undo-tags`.

## External dependencies

| Depends on | For | When it is down |
|---|---|---|
| Radarr, Sonarr | the tagged titles, rescan, tag changes | the pass fails and logs it. The loop tries again next interval. |
| The Decypharr debrid mount | the source of each copy | the link shows as broken. The title keeps its tag. |
| `/media` free space | the copy | the copy stops with "not enough space". The link stays. |
| Seerr | adding the `seerr` tag to a request | no effect on ArrLocalize. New requests go to qBittorrent. |

## Deployment

- Image: `ghcr.io/anothermike-exe/arr-localize`
- Host: the media server (192.168.7.225)
- Rollback: pin the previous image tag in `docker-compose.yml`. To add back tags that a
  pass removed, run `arr-localize undo-tags <stamp> --execute`.

## CI/CD and secrets

| Workflow | Triggers on | Does |
|---|---|---|
| `Review.yml` | pull request, push to `main` | ruff lint and format, pytest `tests/unit`, automated review |
| `BuildImage.yml` | push to `main`, tag `v*` | builds amd64 and arm64, pushes to GHCR: `latest` on `main`, the semver tags on a release |
| `dependabot.yml` | weekly | GitHub Actions, pip and Docker base image updates |

| Secret | Used by | Still to create |
|---|---|---|
| `ANTHROPIC_API_KEY` | `Review.yml` | yes |
| `GITHUB_TOKEN` | `BuildImage.yml` | no, GitHub gives it |

## Security model

- **Trust boundary**: no port is open. The container only makes outbound calls to Sonarr
  and Radarr on the LAN.
- **Authentication**: the API key of each instance, sent as `X-Api-Key`.
- **Secrets at runtime**: environment variables from `.env`, which is never committed.
- **Runs as**: supervisord runs as root to own `/config`. The loop runs as `PUID`/`PGID`.

## Known limits

- One copy at a time. A 60 GB remux at 200 MB/s takes about 5 minutes. A pass with many
  remuxes can run longer than `LOCALIZE_INTERVAL`, and the next pass then starts late.
- Space is checked for each file, not for the whole pass.
- A copy that stops half way (container restart) leaves a `.localize.partial` file.
  The next copy of that file writes over it.

## Decisions

### Use the arr-service client, not a copy of it

**Chose**: depend on `arr-service` at a pinned git tag.
**Over**: a copy of `client.py` and `config.py` in this repo.
**Because**: one copy of the API code. A fix in arr-service reaches ArrLocalize with a
version bump. See `docs/adr/0001-shared-arr-client.md`.
**Revisit when**: arr-service changes its public names often.

### Run on the server, in a container

**Chose**: a looping container with the same mounts as Radarr.
**Over**: running from a workstation over SMB, or a Radarr Custom Script.
**Because**: the API cannot copy files. Over SMB a remux crosses the network twice, and
SMB hides symlinks. A Custom Script blocks the import for the length of the copy.
**Revisit when**: Decypharr can copy the file to local storage after the import by itself.

### Remove the tag only when the title is complete

**Chose**: untag a series only when every aired, monitored episode is local.
**Over**: untag after the first import.
**Because**: the rest of the request still comes quickly from debrid.
**Revisit when**: no plan to.
