# Unraid Testing

How to run the `:dev` image on Unraid while work continues on the `dev` branch. Each push
to `dev` builds `ghcr.io/anothermike-exe/arr-localize:dev`, and also `:dev-<sha>` so that
you can go back to one build.

## Before you start

1. Open the Radarr container in Unraid (Docker tab → Radarr → Edit).
2. Write down the host path and container path of each mapping for `/media` and for the
   Decypharr debrid mount.
3. Write down its `PUID` and `PGID`.
4. On the Unraid terminal, run this and make sure that the link target still exists:

   ```bash
   ls -lL "/mnt/user/media/movies/Wicked For Good (2025)/"
   ```

   Replace `/mnt/user/media` with the host path of the Radarr `/media` mapping.

## Add the container

Docker tab → **Add Container**. Set **Advanced View** on.

| Field | Value |
|---|---|
| Name | `ArrLocalize` |
| Repository | `ghcr.io/anothermike-exe/arr-localize:dev` |
| Network Type | `bridge` (no port is needed) |
| Console shell command | `Shell` |

### Paths

| Name | Container path | Host path | Access mode |
|---|---|---|---|
| Config | `/config` | `/mnt/user/appdata/ArrLocalize` | Read/Write |
| Media | the same as Radarr, `/media` | the same as Radarr | Read/Write |
| Debrid | the same as Radarr | the same as Radarr | **Read/Write - Slave** |

The container path of Media and Debrid must be the same as in Radarr. ArrLocalize opens the
path that Radarr gives, with no translation. On PlumServer this is `/mnt/user/rclone` →
`/mnt`, because the links point to `/mnt/realdebrid/__all__/...`. Check where a link points
with `docker exec Arr-Localize readlink "<file>"`. Use **Read/Write - Slave** for the debrid
mount, because it is an rclone FUSE mount that can start after the container.

### Variables

| Key | Value |
|---|---|
| `PUID` | the same as Radarr (Unraid default `99`) |
| `PGID` | the same as Radarr (Unraid default `100`) |
| `UMASK` | `002` |
| `TZ` | your timezone, for example `America/Los_Angeles` |
| `RADARR_URL` | `http://192.168.7.225:8003` |
| `RADARR_API_KEY` | from Radarr → Settings → General → Security |
| `SONARR_URL` | `http://192.168.7.225:8005` |
| `SONARR_API_KEY` | from Sonarr → Settings → General → Security |
| `LOCALIZE_EXECUTE` | `false` for the first start |
| `LOCALIZE_INTERVAL` | `300` while you test, `900` after |
| `LOCALIZE_TAG` | `seerr` |

Unraid does not read a `.env` file. Set each variable in the template.

## First start: dry-run

1. Click **Apply**.
2. Open the container console, or run on the Unraid terminal:

   ```bash
   docker exec ArrLocalize cat /config/supervisord.log
   ```

3. Expect these lines for a Seerr request that is still a symlink:

   ```
   radarr: Wicked: For Good
     plan   copy     /media/movies/Wicked For Good (2025)/...mkv
     plan   rescan   Wicked: For Good
     plan   untag    Wicked: For Good
   dry-run: nothing was changed. Use --execute to apply.
   ```

If you see "path not found, check the container mounts", the container path of Media or
Debrid is not the same as in Radarr.

## Turn on the copy

1. Edit the container, set `LOCALIZE_EXECUTE` to `true`, and click **Apply**.
2. After the next pass, check:
   - `ls -l` on the movie folder shows a regular file, not a link.
   - Radarr shows only the tag `1-plumsolutions` on the movie.
   - The movie still plays in Jellyfin.
   - `/mnt/user/appdata/ArrLocalize/history/` has one JSON file.

To put the tags back after a bad pass:

```bash
docker exec ArrLocalize arr-localize undo-tags <stamp> --execute
```

## Get a new dev build

After a push to `dev`, wait for **BuildImage** to pass on GitHub. Then, in the Docker tab,
click **Check for Updates**, then **apply update** on ArrLocalize. To go back to one
build, set the Repository to `ghcr.io/anothermike-exe/arr-localize:dev-<sha>`.
