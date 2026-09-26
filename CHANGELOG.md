# Changelog

All notable changes to this project are recorded here.

The format is [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-09-26

First release. Tested on Unraid with Radarr 6.4, Sonarr 4.0.20 and Decypharr.

### Added
- Find each Sonarr series and Radarr movie with the `seerr` tag, and copy each Decypharr
  debrid symlink to a local file in the same place
- Rescan the title after the copy, and remove the tag when the title is complete. A
  series is complete when every aired, monitored episode has a local file.
- Dry-run by default. Set `LOCALIZE_EXECUTE=true` to copy files and change tags.
- A rollback record in `/config/history/` before each pass that writes, and
  `arr-localize undo-tags` to add the tags back
- Binhex container with supervisord, for `linux/amd64` and `linux/arm64`
- `:dev` and `:dev-<sha>` images from the `dev` branch for testing

[Unreleased]: https://github.com/AnotherMike-exe/ArrLocalize/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/AnotherMike-exe/ArrLocalize/releases/tag/v0.1.0
