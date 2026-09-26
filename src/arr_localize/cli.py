"""arr-localize: copy debrid symlinks to local files, then remove the tag.

arr-localize run                     plan one pass and print it (dry-run)
arr-localize run --execute           plan one pass and run it
arr-localize loop --execute          run a pass every LOCALIZE_INTERVAL seconds
arr-localize undo-tags STAMP         add back the tags that a pass removed
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from arr_service import config
from arr_service.client import ArrClient

from . import history, localize


def log(message):
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} {message}", flush=True)


def env_flag(name):
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def build_clients(only=None):
    instances, problems = config.discover(config.load_env(Path.cwd() / ".env"))
    for problem in problems:
        log(f"config: {problem}")
    clients = [ArrClient(**i) for i in instances if not only or i["name"] in only]
    if not clients:
        raise SystemExit("error: no Sonarr or Radarr instance is configured, see docs/QUICK-REFERENCE.md")
    return clients


def one_pass(clients, tag_label, execute):
    """Plan every instance, write the rollback record, then run. Return 0 or 1."""
    plans = []
    for client in clients:
        titles, notes = localize.plan(client, tag_label)
        for note in notes:
            log(f"note: {note}")
        plans.append((client, titles))

    if not any(titles for _, titles in plans):
        log("nothing to do")
        return 0

    for client, titles in plans:
        for title in titles:
            log(f"{client.name}: {title.name}")
            for action in title.actions:
                log(f"  plan   {action.description}")

    if not execute:
        log("dry-run: nothing was changed. Use --execute to apply.")
        return 0

    records = {
        client.name: {
            "app": client.app,
            "tag_id": localize.find_tag_id(client, tag_label),
            "titles": [{"id": t.id, "name": t.name, "tags": t.tags, "links": t.links} for t in titles],
        }
        for client, titles in plans
        if titles
    }
    log(f"rollback record written to {history.write(records)}")

    failed = 0
    for client, titles in plans:
        for title in titles:
            log(f"{client.name}: {title.name}")
            if not localize.run_title(title, log):
                failed += 1
    return 1 if failed else 0


def cmd_run(args):
    return one_pass(build_clients(args.instance), args.tag, args.execute)


def cmd_loop(args):
    execute = args.execute or env_flag("LOCALIZE_EXECUTE")
    log(f"loop: tag={args.tag!r} interval={args.interval}s execute={execute}")
    while True:
        try:
            one_pass(build_clients(args.instance), args.tag, execute)
        except Exception as exc:
            log(f"pass failed: {exc}")
        time.sleep(args.interval)


def cmd_undo_tags(args):
    records = history.load(args.stamp)
    clients = {c.name: c for c in build_clients()}
    for name, record in records.items():
        client = clients.get(name)
        if client is None:
            log(f"{name}: not configured, skipped")
            continue
        ids = [t["id"] for t in record["titles"]]
        log(f"{name}: add tag {record['tag_id']} back to {len(ids)} title(s)")
        if args.execute:
            body = {client.media_id_field: ids, "tags": [record["tag_id"]], "applyTags": "add"}
            client.put(f"{client.media_path}/editor", body)
    if not args.execute:
        log("dry-run: nothing was changed. Use --execute to apply.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="arr-localize", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("--tag", default=os.environ.get("LOCALIZE_TAG", "seerr"))
        p.add_argument("--instance", action="append", help="limit to this instance name")
        p.add_argument("--execute", action="store_true")

    run = sub.add_parser("run", help="one pass (dry-run by default)")
    common(run)
    run.set_defaults(func=cmd_run)

    loop = sub.add_parser("loop", help="run a pass on an interval")
    common(loop)
    loop.add_argument("--interval", type=int, default=int(os.environ.get("LOCALIZE_INTERVAL", "900")))
    loop.set_defaults(func=cmd_loop)

    undo = sub.add_parser("undo-tags", help="add back the tags that a pass removed")
    undo.add_argument("stamp", help="history file stamp or path")
    undo.add_argument("--execute", action="store_true")
    undo.set_defaults(func=cmd_undo_tags)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
