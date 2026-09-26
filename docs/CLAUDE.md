# CLAUDE.md — ArrLocalize

Project memory for Claude Code. Keep it true: a line that is wrong is worse than a line
that is missing, because it is trusted.

## What this is

A container on the media server. It replaces the Decypharr debrid symlinks that Sonarr
and Radarr import for Seerr requests with permanent local copies. Seerr tags each request
`seerr`, and only the Decypharr download client has that tag, so the request streams from
debrid at once. ArrLocalize then copies each file to `/media`, rescans the title, and
removes the tag, so that later grabs go through qBittorrent.

**Stage**: prototype
**Deployed on**: the media server (192.168.7.225), next to Radarr and Sonarr

## Stack

| Part | Choice |
|---|---|
| Language | Python 3.12 (code stays 3.9-compatible, ruff target `py39`) |
| API client | `arr-service` (`ArrClient`, `config.discover`), pinned to a git tag |
| Data store | JSON rollback records in `/config/history/` |
| Runtime | Docker, linux/amd64 and linux/arm64, supervisord |

## Layout

```
src/arr_localize/
  localize.py     classify files, plan actions for a title, copy a link, run a title
  history.py      rollback records, one for each pass that writes
  cli.py          run / loop / undo-tags
docker/           Entrypoint.sh, RunLoop.sh, supervisord.conf
tests/unit/       pytest with real temporary files and a fake client
docs/             every document except README.md
_resources/       dev references, never in git
```

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"   # install
.venv/bin/arr-localize run                                   # one dry-run pass, uses ./.env
.venv/bin/pytest tests/unit                                  # test
.venv/bin/ruff check . && .venv/bin/ruff format --check .    # lint
docker compose up -d                                         # run the container
```

Until `arr-service` has the tag `v0.1.0`, install it from a local clone first:
`.venv/bin/pip install -e ../arr-service`, then `.venv/bin/pip install --no-deps -e .`.

## Conventions

**Naming**: Python rules win. Modules, files and functions are `snake_case`, the package
is `arr_localize`. Directories outside the package, documentation filenames and container
names are PascalCase. Constants and environment variables are `UPPER_SNAKE_CASE`.

**Errors**: a pass never stops the loop. `run_title()` stops one title at its first
failed action and logs it. The next pass tries that title again. `cmd_loop` catches and
logs a failed pass.

**Project-specific rules** (these protect a real media library):
- **Dry-run by default.** `--execute` or `LOCALIZE_EXECUTE=true` is the only way to change
  anything. Keep it that way for any new command.
- **A rollback record comes before every write.** `one_pass()` writes `history/<stamp>.json`
  before the first action runs.
- **Actions are data.** The plan is a list of `Action` objects. The dry-run prints the
  same list that `--execute` runs.
- **Never change the link target.** The debrid file is the rollback for a copy.
- **Never commit `.env`.** It holds live API keys.

## How to work here

**Plan mode** for anything beyond a single-file edit: a refactor, a change to the copy
logic, anything touching Docker or CI. Show the plan and wait for a yes.

**A subagent** for work that parallelizes — a research spike, reading a long reference,
an independent audit. The main thread integrates the result. A subagent never runs a
command with `--execute`.

**Ask early.** An architecture question answered before the work costs a minute. The
same question answered after costs the work.

Standing rules for this repo: rebase, never merge. `_resources/` never enters git. Docs
live in `docs/`, and `README.md` is the only root doc. CI green before merge.

## The phase loop

Each phase of the build runs the same five steps.

1. `/resume-session` — restore the state the last phase left
2. Build. Name `tdd-workflow` only for a bug fix, where the test is the reproducer
3. `verification-loop` — the gate at the end of the phase
4. Review in parallel: `code-reviewer`, `security-reviewer` and `python-reviewer`
5. `/learn-eval`, then `/save-session`

Commit at the end of every phase. A local commit costs nothing and gives the review a
diff to read.

`blueprint` holds the phase plan between sessions. Each step in it carries a brief that a
fresh session can execute cold.

## Docker

Volumes and environment variables are in `docs/QUICK-REFERENCE.md`. Read that file
rather than repeating it here.

What is true of this project and not of every Binhex container:

- `/media` and the debrid mount must have the **same container paths as in Radarr and
  Sonarr**. ArrLocalize reads the file paths from their API and opens them as given.
- `PUID`/`PGID` must be the same pair as Radarr, because the copies get this owner.
- The container runs supervisord as root only to own `/config`. The loop runs as
  `PUID:PGID`.

First place to look when the container misbehaves: `/config/supervisord.log`.

## Gotchas

- Every title shows "path not found" → the command ran on a machine without the mounts,
  such as a workstation. That is expected there. On the server, it means the volume
  lines do not match Radarr.
- A Seerr request downloads through qBittorrent → the title has no `seerr` tag. Check
  the default tag on the server in Seerr (Settings → Services → edit the server → Test →
  Tags).
- Media with a tag uses only clients with that tag, and untagged media uses only untagged
  clients. Do not put a tag on the normal download client.

## Where the rules live

The Plum Solutions standards — naming, Binhex Docker layout, documentation rules, git
workflow — are in the `plum-standards` skill, not copied here. A copy in every repo is a
copy that goes stale.

This file holds only what is true of **this** project.
