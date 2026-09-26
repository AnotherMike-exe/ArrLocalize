# 0001: Use the arr-service API client

**Status**: accepted, 2026-09-25

## Context

ArrLocalize needs a Sonarr and Radarr v3 client and the `<NAME>_URL` / `<NAME>_API_KEY`
instance discovery. arr-service already has both, with tests in daily use, and it has no
dependencies. ArrLocalize is a separate repo, because it is a container that runs all the
time, and arr-service is a CLI that an operator runs by hand.

## Decision

ArrLocalize depends on `arr-service` at a pinned git tag, and uses only `ArrClient`,
`config.discover()` and `config.load_env()`.

## Consequences

- There is one copy of the API code.
- arr-service must have a tag before ArrLocalize can build. The first tag is `v0.1.0`.
- A change to those three names in arr-service is a breaking change for ArrLocalize.
- The build stage needs `git` to fetch the dependency.
