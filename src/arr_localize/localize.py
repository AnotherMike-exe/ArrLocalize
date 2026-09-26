"""Plan and run the localize pass for one Sonarr or Radarr instance.

A title is a movie or a series that carries the localize tag. For each title the
pass copies every debrid symlink to a real local file, rescans the title, and
removes the tag when the title is complete. The plan is a list of Action objects,
so the dry-run output and the executed pass use the same code path.
"""

import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

LOCAL = "local"
SYMLINK = "symlink"
BROKEN = "broken"
MISSING = "missing"

PARTIAL_SUFFIX = ".localize.partial"
SPACE_MARGIN = 0.05
COPY_CHUNK = 8 * 1024 * 1024


class LocalizeError(Exception):
    pass


class Action:
    def __init__(self, description, func):
        self.description = description
        self.func = func

    def run(self):
        self.func()

    def __repr__(self):
        return self.description


@dataclass
class Title:
    app: str
    id: int
    name: str
    tags: list
    links: list = field(default_factory=list)
    actions: list = field(default_factory=list)


def classify(path):
    """Return LOCAL, SYMLINK, BROKEN or MISSING for a media file path."""
    p = Path(path)
    if p.is_symlink():
        return SYMLINK if p.exists() else BROKEN
    if p.is_file():
        return LOCAL
    return MISSING


def copy_over_link(link, disk_usage=shutil.disk_usage):
    """Replace a symlink with a local copy of its target.

    The copy goes to a partial file in the same folder, and os.replace() then
    swaps it over the link in one step. If anything fails, the partial file is
    deleted and the link stays as it was. The link target is never changed.
    """
    link = Path(link)
    if not link.is_symlink():
        raise LocalizeError(f"{link} is not a symlink")
    source = link.resolve(strict=True)
    size = source.stat().st_size

    needed = int(size * (1 + SPACE_MARGIN))
    free = disk_usage(link.parent).free
    if free < needed:
        raise LocalizeError(f"not enough space for {link.name}: need {needed} bytes, {free} free")

    partial = link.with_name(link.name + PARTIAL_SUFFIX)
    try:
        with open(source, "rb") as src, open(partial, "wb") as dst:
            shutil.copyfileobj(src, dst, COPY_CHUNK)
            dst.flush()
            os.fsync(dst.fileno())
        copied = partial.stat().st_size
        if copied != size:
            raise LocalizeError(f"size mismatch for {link.name}: copied {copied} of {size} bytes")
        os.replace(partial, link)
    except BaseException:
        if partial.exists():
            partial.unlink()
        raise


def find_tag_id(client, label):
    for tag in client.get("tag") or []:
        if tag.get("label") == label:
            return tag["id"]
    return None


def _now():
    return datetime.now(timezone.utc)


def _aired(episode, now):
    stamp = episode.get("airDateUtc")
    if not stamp:
        return False
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")) <= now


def _file_actions(client, title, paths, notes):
    """Add copy actions for the symlinks in paths. Return True if every file is usable."""
    usable = True
    for path in paths:
        kind = classify(path)
        if kind == SYMLINK:
            title.links.append({"path": path, "target": os.readlink(path)})
            title.actions.append(Action(f"copy     {path}", lambda p=path: copy_over_link(p)))
        elif kind == BROKEN:
            notes.append(f"{client.name}: {title.name}: broken link, target is gone: {path}")
            usable = False
        elif kind == MISSING:
            notes.append(f"{client.name}: {title.name}: path not found, check the container mounts: {path}")
            usable = False
    return usable


def _finish(client, title, complete, tag_id):
    """Add the rescan and untag actions after the copies."""
    if title.links:
        body = (
            {"name": "RescanMovie", "movieId": title.id}
            if client.app == "radarr"
            else {"name": "RescanSeries", "seriesId": title.id}
        )
        title.actions.append(Action(f"rescan   {title.name}", lambda: client.post("command", body)))
    if complete:
        editor = {client.media_id_field: [title.id], "tags": [tag_id], "applyTags": "remove"}
        title.actions.append(
            Action(
                f"untag    {title.name}",
                lambda: client.put(f"{client.media_path}/editor", editor),
            )
        )


def _plan_movies(client, tag_id, notes):
    titles = []
    for movie in client.get("movie") or []:
        if tag_id not in movie.get("tags", []) or not movie.get("hasFile"):
            continue
        title = Title("radarr", movie["id"], movie["title"], list(movie["tags"]))
        path = (movie.get("movieFile") or {}).get("path")
        if not path:
            notes.append(f"{client.name}: {title.name}: Radarr gives no file path")
            continue
        usable = _file_actions(client, title, [path], notes)
        _finish(client, title, usable, tag_id)
        if title.actions:
            titles.append(title)
    return titles


def _plan_series(client, tag_id, notes, now):
    titles = []
    for series in client.get("series") or []:
        if tag_id not in series.get("tags", []):
            continue
        title = Title("sonarr", series["id"], series["title"], list(series["tags"]))
        files = client.get("episodefile", {"seriesId": series["id"]}) or []
        usable = _file_actions(client, title, [f["path"] for f in files if f.get("path")], notes)

        episodes = client.get("episode", {"seriesId": series["id"]}) or []
        waiting = [e for e in episodes if e.get("monitored") and _aired(e, now) and not e.get("hasFile")]
        _finish(client, title, usable and not waiting, tag_id)
        if title.actions:
            titles.append(title)
    return titles


def plan(client, tag_label="seerr", now=None):
    """Return (titles, notes). Each title holds its actions in run order."""
    notes = []
    tag_id = find_tag_id(client, tag_label)
    if tag_id is None:
        notes.append(f"{client.name}: no tag named {tag_label!r}, nothing to do")
        return [], notes
    if client.app == "radarr":
        return _plan_movies(client, tag_id, notes), notes
    return _plan_series(client, tag_id, notes, now or _now()), notes


def run_title(title, log):
    """Run a title's actions in order. Stop the title at the first error."""
    for action in title.actions:
        try:
            action.run()
        except Exception as exc:
            log(f"  FAILED {action.description}: {exc}")
            log(f"  skipped the rest of {title.name}, the next pass tries again")
            return False
        log(f"  done   {action.description}")
    return True
