# TODO — ArrLocalize

Small work that has no issue yet. This file lives at `docs/TODO.md`.

Anything a user would ask for goes to GitHub instead:

- A feature somebody wants → a feature request issue
- A defect → a bug report issue
- A release worth planning → the roadmap

## Now

- [x] Tag `arr-service` `v0.1.0`
- [x] Run the image on Unraid, dry-run and then execute (Wicked: For Good, 85 GB, 22 min)

## Next


- [ ] Test one TV request from start to end.
- [ ] Delete a `.localize.partial` file left by a container restart at the start of a pass.

## Someday

- [ ] Check the free space for the whole pass, not for each file.

## Scaffold gaps

```bash
grep -rn "\[[a-z]" README.md docs/*.md
```

- [x] docker-compose.yml — mounts match PlumServer
