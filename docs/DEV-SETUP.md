# Dev Setup — ArrLocalize

From a fresh clone to a running, tested copy. If a step here fails, the project is
wrong, not the reader.

Target: 10 minutes on a machine that already has Python 3.12 and Docker.

## Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.9 or newer (3.12 in the image) | `python3 --version` |
| Docker | 24 or newer | `docker --version` |
| git | any | `git --version` |

## 1. Clone

```bash
git clone https://github.com/AnotherMike-exe/ArrLocalize.git
cd ArrLocalize
git config pull.rebase true
```

`pull.rebase` keeps history linear, which the ruleset on `main` enforces anyway. Setting
it locally means a plain `git pull` never creates a merge commit that is then refused.

## 2. Install

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Create `_resources/` if you keep working notes. It is in `.gitignore` and never reaches
the repository:

```bash
mkdir -p _resources/{Examples,Research,Assets,Notes}
```

## 3. Configure

```bash
cp .env.example .env
```

Fill these before the first run:

| Variable | Needed for | Where to get it |
|---|---|---|
| `SONARR_URL`, `RADARR_URL` | every API call | the base URL of each instance |
| `SONARR_API_KEY`, `RADARR_API_KEY` | every API call | Settings → General → Security → API Key |

## 4. Run

```bash
.venv/bin/arr-localize run
```

Working when: the output ends with `nothing to do`, or it shows `plan` lines. On a
workstation, each tagged title shows "path not found", because the media paths exist only
on the server. That proves that the API side works.

Containerized instead, on the server:

```bash
docker compose up -d
docker exec ArrLocalize cat /config/supervisord.log
```

## 5. Test

```bash
.venv/bin/pytest tests/unit
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

`tests/integration` is empty. It needs a live Sonarr and Radarr and the debrid mount.

CI runs the same commands. A change that passes here passes there, and the reverse.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|

Add a row the first time somebody hits a problem. A troubleshooting table written in
advance guesses. One written from real failures does not.

## Where the rest is

| Question | Document |
|---|---|
| How it is built and why | `docs/ARCHITECTURE.md` |
| How Claude should work here | `docs/CLAUDE.md` |
| Commands, variables and paths at a glance | `docs/QUICK-REFERENCE.md` |
| What it does, for a user | `README.md` |
| Run the `:dev` image on Unraid | `docs/UnraidTesting.md` |
