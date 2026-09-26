from collections import namedtuple
from datetime import datetime, timezone

import pytest

from arr_localize import cli, localize

Usage = namedtuple("Usage", "total used free")
NOW = datetime(2026, 9, 25, tzinfo=timezone.utc)
PAST = "2026-01-01T00:00:00Z"
FUTURE = "2027-01-01T00:00:00Z"


class FakeClient:
    """Answers GETs from a dict and records every write."""

    def __init__(self, app, responses):
        self.name = app
        self.app = app
        self.responses = responses
        self.writes = []

    @property
    def media_path(self):
        return "series" if self.app == "sonarr" else "movie"

    @property
    def media_id_field(self):
        return "seriesIds" if self.app == "sonarr" else "movieIds"

    def get(self, path, params=None):
        key = path if not params else f"{path}?{next(iter(params.values()))}"
        return self.responses.get(key, [])

    def post(self, path, body):
        self.writes.append(("POST", path, body))

    def put(self, path, body):
        self.writes.append(("PUT", path, body))


@pytest.fixture
def media(tmp_path):
    debrid = tmp_path / "debrid"
    library = tmp_path / "media"
    debrid.mkdir()
    library.mkdir()
    return debrid, library


def make_link(debrid, library, name, data=b"video-bytes"):
    target = debrid / name
    target.write_bytes(data)
    link = library / name
    link.symlink_to(target)
    return link, target


def descriptions(titles):
    return [a.description.split()[0] for t in titles for a in t.actions]


# classify


def test_classify_regular_file(media):
    _, library = media
    f = library / "a.mkv"
    f.write_bytes(b"x")
    assert localize.classify(f) == localize.LOCAL


def test_classify_good_link(media):
    link, _ = make_link(*media, "a.mkv")
    assert localize.classify(link) == localize.SYMLINK


def test_classify_broken_link(media):
    link, target = make_link(*media, "a.mkv")
    target.unlink()
    assert localize.classify(link) == localize.BROKEN


def test_classify_missing_path(media):
    _, library = media
    assert localize.classify(library / "nope.mkv") == localize.MISSING


# copy_over_link


def test_copy_replaces_link_with_same_bytes(media):
    link, target = make_link(*media, "a.mkv", b"0123456789" * 1000)
    localize.copy_over_link(link)
    assert not link.is_symlink()
    assert link.read_bytes() == target.read_bytes()
    assert target.exists()
    assert not list(link.parent.glob("*" + localize.PARTIAL_SUFFIX))


def test_copy_fails_on_low_space_and_keeps_link(media):
    link, _ = make_link(*media, "a.mkv")
    with pytest.raises(localize.LocalizeError, match="not enough space"):
        localize.copy_over_link(link, disk_usage=lambda _: Usage(100, 100, 0))
    assert link.is_symlink()


def test_copy_error_midway_removes_partial_and_keeps_link(media, monkeypatch):
    link, _ = make_link(*media, "a.mkv")

    def boom(src, dst, length=0):
        dst.write(b"half")
        raise OSError("disk went away")

    monkeypatch.setattr(localize.shutil, "copyfileobj", boom)
    with pytest.raises(OSError):
        localize.copy_over_link(link)
    assert link.is_symlink()
    assert not list(link.parent.glob("*" + localize.PARTIAL_SUFFIX))


# plan: Radarr


def radarr(path, tags=(2, 1)):
    return FakeClient(
        "radarr",
        {
            "tag": [{"id": 1, "label": "1-plumsolutions"}, {"id": 2, "label": "seerr"}],
            "movie": [
                {
                    "id": 7,
                    "title": "Film",
                    "tags": list(tags),
                    "hasFile": True,
                    "movieFile": {"path": str(path)},
                },
                {"id": 8, "title": "Other", "tags": [], "hasFile": True, "movieFile": {"path": "/x"}},
            ],
        },
    )


def test_movie_link_gives_copy_rescan_untag(media):
    link, _ = make_link(*media, "a.mkv")
    titles, notes = localize.plan(radarr(link))
    assert descriptions(titles) == ["copy", "rescan", "untag"]
    assert notes == []


def test_movie_already_local_gives_only_untag(media):
    _, library = media
    f = library / "a.mkv"
    f.write_bytes(b"x")
    titles, _ = localize.plan(radarr(f))
    assert descriptions(titles) == ["untag"]


def test_movie_broken_link_gives_note_and_no_actions(media):
    link, target = make_link(*media, "a.mkv")
    target.unlink()
    titles, notes = localize.plan(radarr(link))
    assert titles == []
    assert "broken link" in notes[0]


def test_missing_tag_gives_note():
    client = FakeClient("radarr", {"tag": []})
    titles, notes = localize.plan(client)
    assert titles == [] and "no tag named" in notes[0]


def test_movie_run_writes_rescan_and_untag_only_seerr(media):
    link, _ = make_link(*media, "a.mkv")
    client = radarr(link)
    titles, _ = localize.plan(client)
    assert localize.run_title(titles[0], lambda _: None)
    assert not link.is_symlink()
    assert client.writes == [
        ("POST", "command", {"name": "RescanMovie", "movieId": 7}),
        ("PUT", "movie/editor", {"movieIds": [7], "tags": [2], "applyTags": "remove"}),
    ]


def test_failed_copy_stops_the_title(media):
    link, _ = make_link(*media, "a.mkv")
    client = radarr(link)
    titles, _ = localize.plan(client)

    def fail():
        raise OSError("disk went away")

    titles[0].actions[0].func = fail
    assert not localize.run_title(titles[0], lambda _: None)
    assert client.writes == []


# plan: Sonarr


def sonarr(paths, episodes):
    return FakeClient(
        "sonarr",
        {
            "tag": [{"id": 3, "label": "seerr"}],
            "series": [{"id": 4, "title": "Show", "tags": [3]}],
            "episodefile?4": [{"path": str(p)} for p in paths],
            "episode?4": episodes,
        },
    )


def test_series_with_aired_episode_missing_keeps_tag(media):
    link, _ = make_link(*media, "e1.mkv")
    episodes = [
        {"monitored": True, "airDateUtc": PAST, "hasFile": True},
        {"monitored": True, "airDateUtc": PAST, "hasFile": False},
    ]
    titles, _ = localize.plan(sonarr([link], episodes), now=NOW)
    assert descriptions(titles) == ["copy", "rescan"]


def test_series_complete_ignores_future_and_unmonitored(media):
    link, _ = make_link(*media, "e1.mkv")
    episodes = [
        {"monitored": True, "airDateUtc": PAST, "hasFile": True},
        {"monitored": True, "airDateUtc": FUTURE, "hasFile": False},
        {"monitored": False, "airDateUtc": PAST, "hasFile": False},
        {"monitored": True, "airDateUtc": None, "hasFile": False},
    ]
    client = sonarr([link], episodes)
    titles, _ = localize.plan(client, now=NOW)
    assert descriptions(titles) == ["copy", "rescan", "untag"]
    localize.run_title(titles[0], lambda _: None)
    assert client.writes[-1] == (
        "PUT",
        "series/editor",
        {"seriesIds": [4], "tags": [3], "applyTags": "remove"},
    )


# one_pass


def test_dry_run_changes_nothing(media, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALIZE_HISTORY_DIR", str(tmp_path / "history"))
    link, _ = make_link(*media, "a.mkv")
    client = radarr(link)
    assert cli.one_pass([client], "seerr", execute=False) == 0
    assert link.is_symlink()
    assert client.writes == []
    assert not (tmp_path / "history").exists()


def test_execute_writes_history_before_changes(media, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALIZE_HISTORY_DIR", str(tmp_path / "history"))
    link, target = make_link(*media, "a.mkv")
    client = radarr(link)
    assert cli.one_pass([client], "seerr", execute=True) == 0
    record = cli.history.load(next((tmp_path / "history").glob("*.json")).name)
    title = record["radarr"]["titles"][0]
    assert record["radarr"]["tag_id"] == 2
    assert title["tags"] == [2, 1]
    assert title["links"] == [{"path": str(link), "target": str(target)}]
    assert not link.is_symlink()


def test_loop_without_execute_never_runs_actions(monkeypatch):
    monkeypatch.delenv("LOCALIZE_EXECUTE", raising=False)
    seen = []
    monkeypatch.setattr(cli, "build_clients", lambda only=None: [])
    monkeypatch.setattr(cli, "one_pass", lambda clients, tag, execute: seen.append(execute))
    monkeypatch.setattr(cli.time, "sleep", lambda _: (_ for _ in ()).throw(KeyboardInterrupt))
    with pytest.raises(KeyboardInterrupt):
        cli.main(["loop", "--interval", "1"])
    assert seen == [False]
