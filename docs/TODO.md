# TODO — ArrLocalize

Small work that has no issue yet. This file lives at `docs/TODO.md`.

Anything a user would ask for goes to GitHub instead:

- A feature somebody wants → a feature request issue
- A defect → a bug report issue
- A release worth planning → the roadmap

## Now

- [ ] Tag `arr-service` `v0.1.0`. Until then, `pip install -e ".[dev]"`, CI and the image build fail.
- [ ] Build the image and run it once with `LOCALIZE_EXECUTE=false` on the server.

## Next

- [ ] Set `LOCALIZE_EXECUTE=true` after the first dry-run log looks right.
- [ ] Test one TV request from start to end.
- [ ] Delete a `.localize.partial` file left by a container restart at the start of a pass.

## Someday

- [ ] Check the free space for the whole pass, not for each file.

## Scaffold gaps

```bash
grep -rn "\[[a-z]" README.md docs/*.md
```

- [ ] docker-compose.yml — the `/media` and debrid mount lines are examples. Copy them from the Radarr container.
