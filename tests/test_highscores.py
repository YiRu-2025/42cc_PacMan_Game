import json
from pathlib import Path

import pytest

from pacman.constants import HIGHSCORE_LIMIT, NAME_MAX_LENGTH
from pacman.highscores import (
    Entry,
    Highscores,
    _valid_score,
    is_name_complete,
    sanitize_name,
)

Capture = pytest.CaptureFixture[str]


@pytest.fixture
def table(tmp_path: Path) -> Highscores:
    return Highscores(tmp_path / "scores.json")


def write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


# --------------------------------------------------------------- names
@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Alice", "Alice"),
        ("  Bob  ", "Bob"),
        ("a    b", "a b"),
        ("Zoé", "Zo"),
        ("名前abc", "abc"),
        ("a_b-c!", "abc"),
        ("", "PLAYER"),
        ("   ", "PLAYER"),
        ("!!!", "PLAYER"),
        ("abcdefghijklmnop", "abcdefghij"),
        ("abcdefghi j", "abcdefghi"),
        ("R2D2 42", "R2D2 42"),
    ],
)
def test_sanitize_name(raw: str, expected: str) -> None:
    assert sanitize_name(raw) == expected


def test_sanitized_names_always_fit() -> None:
    for raw in ("x" * 100, "é" * 50, " a " * 30):
        assert 0 < len(sanitize_name(raw)) <= NAME_MAX_LENGTH


@pytest.mark.parametrize(
    "raw, ok",
    [
        ("Alice", True),
        ("a b", True),
        ("", False),
        (" a", False),
        ("a ", False),
        ("é", False),
        ("x" * 10, True),
        ("x" * 11, False),
    ],
)
def test_is_name_complete(raw: str, ok: bool) -> None:
    assert is_name_complete(raw) is ok


@pytest.mark.parametrize(
    "value, expected",
    [
        (5, 5),
        (0, 0),
        (-1, None),
        (True, None),
        (False, None),
        (3.0, None),
        ("7", None),
        (None, None),
    ],
)
def test_valid_score(value: object, expected: int | None) -> None:
    assert _valid_score(value) == expected


def test_entry_is_immutable() -> None:
    with pytest.raises(Exception):
        Entry("a", 1).score = 2  # type: ignore[misc]


# ----------------------------------------------------------- the table
def test_empty_table(table: Highscores) -> None:
    assert table.entries == () and table.best() == 0
    assert table.qualifies(0) and not table.qualifies(-1)


def test_entries_is_a_tuple_copy(table: Highscores) -> None:
    table.add("a", 1)
    assert isinstance(table.entries, tuple)


def test_add_orders_best_first_and_returns_rank(table: Highscores) -> None:
    assert table.add("a", 100) == 1
    assert table.add("b", 300) == 1
    assert table.add("c", 200) == 2
    assert [e.name for e in table.entries] == ["b", "c", "a"]
    assert table.best() == 300


def test_ties_keep_arrival_order(table: Highscores) -> None:
    table.add("first", 100)
    assert table.add("second", 100) == 2
    assert [e.name for e in table.entries] == ["first", "second"]


def test_table_is_trimmed_to_ten(table: Highscores) -> None:
    for i in range(15):
        table.add(f"p{i}", (i + 1) * 10)
    assert len(table.entries) == HIGHSCORE_LIMIT
    assert table.best() == 150 and table.entries[-1].score == 60


def test_full_table_rejects_equal_and_lower(table: Highscores) -> None:
    for i in range(10):
        table.add("p", 100 + i)
    assert not table.qualifies(100)
    assert not table.qualifies(50)
    assert table.add("late", 100) == 0
    assert table.qualifies(101)


def test_full_table_accepts_better_and_drops_last(table: Highscores) -> None:
    for i in range(10):
        table.add("p", 100 + i)
    assert table.add("new", 500) == 1
    assert len(table.entries) == 10
    assert all(e.score != 100 for e in table.entries)


def test_negative_scores_are_clamped(table: Highscores) -> None:
    assert table.add("neg", -50) == 1
    assert table.entries[0].score == 0


def test_add_sanitizes_the_name(table: Highscores) -> None:
    table.add("  é!  ", 5)
    assert table.entries[0].name == "PLAYER"


def test_rank_of(table: Highscores) -> None:
    for s in (300, 200, 100):
        table.add("p", s)
    assert table.rank_of(400) == 1
    assert table.rank_of(250) == 2
    assert table.rank_of(200) == 3  # a tie goes below
    assert table.rank_of(-5) == 0


# ------------------------------------------------------------- loading
def test_missing_file_gives_empty_table(table: Highscores, capsys: Capture) -> None:
    table.load()
    assert table.entries == () and capsys.readouterr().err == ""


def test_empty_file_gives_empty_table(table: Highscores) -> None:
    table.path.write_text("   \n")
    table.load()
    assert table.entries == ()


def test_empty_list_gives_empty_table(table: Highscores) -> None:
    write(table.path, [])
    table.load()
    assert table.entries == ()


def test_invalid_json_is_reported(table: Highscores, capsys: Capture) -> None:
    table.path.write_text("{oops")
    table.load()
    assert table.entries == ()
    assert "not valid JSON" in capsys.readouterr().err


def test_non_utf8_file(table: Highscores, capsys: Capture) -> None:
    table.path.write_bytes(b"\xff\xfe\x00")
    table.load()
    assert table.entries == () and "cannot read" in capsys.readouterr().err


def test_unreadable_path(tmp_path: Path, capsys: Capture) -> None:
    t = Highscores(tmp_path)  # a directory, not a file
    t.load()
    assert t.entries == () and "cannot read" in capsys.readouterr().err


def test_json_that_is_not_a_list(table: Highscores, capsys: Capture) -> None:
    write(table.path, {"name": "a", "score": 1})
    table.load()
    assert table.entries == () and "JSON array" in capsys.readouterr().err


def test_bad_rows_are_dropped_good_ones_kept(
    table: Highscores, capsys: Capture
) -> None:
    write(
        table.path,
        [
            {"name": "ok", "score": 50},
            "string",
            7,
            None,
            {"name": "no score"},
            {"score": 5},
            {"name": 5, "score": 5},
            {"name": "bool", "score": True},
            {"name": "neg", "score": -3},
            {"name": "float", "score": 1.5},
        ],
    )
    table.load()
    assert [e.name for e in table.entries] == ["ok"]
    assert "ignored 9 unusable entries" in capsys.readouterr().err


def test_single_bad_row_message_is_singular(
    table: Highscores, capsys: Capture
) -> None:
    write(table.path, [{"name": "a", "score": 1}, 5])
    table.load()
    assert "1 unusable entry" in capsys.readouterr().err


def test_load_sorts_sanitizes_and_trims(table: Highscores) -> None:
    rows = [{"name": f"p{i}", "score": i} for i in range(15)]
    rows.append({"name": "é!x", "score": 99})
    write(table.path, rows)
    table.load()
    assert len(table.entries) == 10
    assert table.entries[0] == Entry("x", 99)
    scores = [e.score for e in table.entries]
    assert scores == sorted(scores, reverse=True)


def test_load_replaces_previous_contents(table: Highscores) -> None:
    table.add("old", 1)
    table.load()  # the file does not exist
    assert table.entries == ()


# -------------------------------------------------------------- saving
def test_save_and_reload_round_trip(table: Highscores) -> None:
    table.add("a", 10)
    table.add("b", 20)
    assert table.save() is True
    other = Highscores(table.path)
    other.load()
    assert other.entries == table.entries


def