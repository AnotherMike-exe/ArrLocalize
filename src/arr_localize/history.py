"""Rollback records. One JSON file for each pass that writes anything.

The record holds each title's tags and each original link, written before the
first change. `undo-tags` reads it to add the removed tag back. The copies need no
undo, because the debrid file that each link pointed at is never changed.
"""

import json
import os
from datetime import datetime
from pathlib import Path


def history_dir():
    return Path(os.environ.get("LOCALIZE_HISTORY_DIR", "history"))


def write(records):
    """Write {instance: {"tag_id": int, "titles": [...]}} and return the path."""
    target = history_dir()
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(records, indent=2))
    return path


def load(stamp):
    path = Path(stamp)
    if not path.exists():
        path = history_dir() / (stamp if stamp.endswith(".json") else f"{stamp}.json")
    return json.loads(path.read_text())
