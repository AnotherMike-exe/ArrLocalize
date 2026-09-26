# ArrLocalize

> Stream a Seerr request from debrid at once, then keep a permanent local copy.

Decypharr gives Sonarr and Radarr a debrid download in seconds, but the file in the
library is only a symlink into the debrid mount. It breaks when the debrid cache or the
subscription stops. ArrLocalize finds each title that carries the `seerr` tag, copies the
debrid file over its symlink, rescans the title, and removes the tag. After that, upgrades
and new episodes go through your normal download client.

---

## Usage

1. In Radarr and Sonarr, give the Decypharr download client the tag `seerr`. Leave the
   normal client with no tags.
2. In Seerr, set the default tag `seerr` on each Radarr and Sonarr server.
3. Copy `.env.example` to `.env`, and fill in the URL and API key of each instance.
4. In `docker-compose.yml`, copy the `/media` and debrid mount lines from your Radarr
   container.
5. Start it:

```bash
docker compose up -d
docker exec ArrLocalize cat /config/supervisord.log
```

Working when: the log shows `plan   copy`, `plan   rescan` and `plan   untag` lines for a
title that you requested in Seerr. Then set `LOCALIZE_EXECUTE=true` and start the
container again.

Full setup is in [docs/DEV-SETUP.md](docs/DEV-SETUP.md).

## Details

The full tables of variables and paths are in
[docs/QUICK-REFERENCE.md](docs/QUICK-REFERENCE.md).

ArrLocalize opens no port. It writes its log to `/config/supervisord.log`, and one
rollback record for each pass that makes a change to `/config/history/`. Set `PUID` and
`PGID` to the same pair as Radarr, or the copies get the wrong owner.

Known limitations:

- A title stays tagged, and streams from debrid, until its copy is complete. A series
  stays tagged until every aired, monitored episode has a local file.
- The first start is a dry-run. Nothing changes until you set `LOCALIZE_EXECUTE=true`.
- The copy needs free space for the full file in `/media`, plus 5 %.

- [Architecture](docs/ARCHITECTURE.md) — system design and the decisions behind it
- [Dev setup](docs/DEV-SETUP.md) — from a clone to a running copy
- [Quick reference](docs/QUICK-REFERENCE.md) — commands, variables and paths

## Attributions

Built on [arr-service](https://github.com/AnotherMike-exe/arr-service) for the Sonarr and
Radarr v3 API client. Works with [Decypharr](https://github.com/sirrobot01/decypharr),
[Sonarr](https://sonarr.tv), [Radarr](https://radarr.video) and Seerr.

Licensed under [MIT](LICENSE).

---

**Repository**: https://github.com/AnotherMike-exe/ArrLocalize · **Maintainer**: Plum Solutions
