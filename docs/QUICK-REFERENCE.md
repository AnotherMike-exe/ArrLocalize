# Quick Reference: ArrLocalize

> The commands you actually run on this project. Anything that is true of every
> Plum project belongs in the standards, not here.

---

## Daily commands

```bash
# Start / stop
docker compose up -d
docker compose down

# Logs
docker exec ArrLocalize cat /config/supervisord.log

# One pass by hand, inside the container (dry-run, then apply)
docker exec ArrLocalize arr-localize run
docker exec ArrLocalize arr-localize run --execute

# Add back the tags that one pass removed
docker exec ArrLocalize arr-localize undo-tags 20260925-221500 --execute

# Tests
.venv/bin/pytest tests/unit

# Lint / format
.venv/bin/ruff check . && .venv/bin/ruff format --check .

# Build
docker build -t arr-localize:dev .
```

## Endpoints and ports

ArrLocalize opens no port. It calls these endpoints on each Sonarr and Radarr instance:

| Call | Why |
|---|---|
| `GET tag`, `GET movie`, `GET series` | find the tagged titles |
| `GET episodefile?seriesId=`, `GET episode?seriesId=` | Sonarr files and the completion rule |
| `POST command` (`RescanMovie`, `RescanSeries`) | make the app read the new local file |
| `PUT movie/editor`, `PUT series/editor` | remove or add back the tag |

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `PUID` / `PGID` | `99` / `100` | Host user that owns `/media` (`id -u`, `id -g`). Use the same pair as Radarr. |
| `UMASK` | `002` | Group-writable files |
| `TZ` | `Etc/UTC` | Container timezone, used in the log stamps |
| `SONARR_URL` / `SONARR_API_KEY` | none | One Sonarr instance. Add `SONARR_<NAME>_URL` pairs for more. |
| `RADARR_URL` / `RADARR_API_KEY` | none | One Radarr instance. Add `RADARR_<NAME>_URL` pairs for more. |
| `LOCALIZE_TAG` | `seerr` | The tag that marks a title as a debrid grab |
| `LOCALIZE_INTERVAL` | `900` | Seconds between two passes |
| `LOCALIZE_EXECUTE` | `false` | `false` logs the plan only. `true` copies files and changes tags. |
| `LOCALIZE_HISTORY_DIR` | `/config/history` | Where each pass writes its rollback record |

Full list: [docs/DEV-SETUP.md](DEV-SETUP.md)

## Paths

| Path | Holds |
|---|---|
| `/config` | `supervisord.log`, and `history/` with one rollback record for each pass that wrote |
| `/media` | The media library. It must be the same host folder, at the same container path, as in Radarr and Sonarr. |
| the debrid mount | The Decypharr mount. It must have the same container path as in Radarr. Use `:rslave` for an rclone FUSE mount. |

`/data` is not used.

## Troubleshooting

### The log says "path not found, check the container mounts"
→ The container does not see the file at the path that Radarr or Sonarr gives.
→ Compare the volume lines with the Radarr container. The container paths must be the same.

### The log says "broken link, target is gone"
→ The debrid file is no longer in the Decypharr mount. ArrLocalize cannot copy it.
→ Search the title again in Radarr or Sonarr. The tag stays, so the new grab goes to Decypharr again.

### The log says "not enough space"
→ `/media` has less free space than the file size plus 5 %. Make space. The next pass tries again.

### Container will not start
→ Read `/config/supervisord.log` first
→ Check `PUID`/`PGID` can write `/config` and `/media`

### Permission errors on the volumes
→ `PUID`/`PGID` must match the host owner: `id -u`, `id -g`
→ ArrLocalize never changes the owner of `/media`. Fix the owner on the host.

## Project links

- [Architecture](ARCHITECTURE.md)
- [Dev setup](DEV-SETUP.md)
- [Unraid testing](UnraidTesting.md): run the `:dev` image on Unraid
- [Issues](https://github.com/AnotherMike-exe/ArrLocalize/issues)

---

**Scope note for whoever edits this file:** naming rules, Binhex conventions,
documentation layout, and the git workflow are Plum-wide standards and live in the
`plum-standards` skill. Do not restate them here — a copy in every repo is a copy
that goes stale.
