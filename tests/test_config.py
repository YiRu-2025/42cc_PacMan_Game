from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from pacman.config import (MIN_LEVELS, Config, LevelConfig, load_config,
                           read_raw_config, strip_comments, validated_int,
                           validated_levels, validated_str)

ROOT = Path(__file__).resolve().parent.parent


def cfg(tmp_path: Path, text: str) -> Config:
    f = tmp_path / "c.json"
    f.write_text(text, encoding="utf-8")
    return load_config(f)


# ---- strip_comments / read_raw_config ----
def test_strip_comments_drops_hash_slash_and_blank_lines() -> None:
    text = '# one\n\n// two\n  # three\n{"a": 1}\n'
    assert strip_comments(text) == '{"a": 1}'


def test_hash_inside_a_value_survives() -> None:
    assert '"a#b"' in strip_comments('{"k": "a#b"}')


def test_valid_file_with_comments(tmp_path: Path) -> None:
    f = tmp_path / "c.json"
    f.write_text('# comment\n{"lives": 3}\n')
    assert read_raw_config(f) == {"lives": 3}


@pytest.mark.parametrize("text", ['{"lives": }', "[1, 2]", "", "# only a comment",
                                  '"string"', "42"])
def test_unusable_content_returns_empty(tmp_path: Path, text: str) -> None:
    f = tmp_path / "c.json"
    f.write_text(text)
    assert read_raw_config(f) == {}


def test_missing_file_returns_empty(tmp_path: Path,
                                    capsys: pytest.CaptureFixture[str]) -> None:
    assert read_raw_config(tmp_path / "nope.json") == {}
    assert "[config]" in capsys.readouterr().err


def test_non_utf8_returns_empty(tmp_path: Path) -> None:
    f = tmp_path / "c.json"
    f.write_bytes(b"\xff\xfe{")
    assert read_raw_config(f) == {}


def test_directory_returns_empty(tmp_path: Path) -> None:
    assert read_raw_config(tmp_path) == {}


# ---- validated_int ----
def test_int_missing_is_silent(capsys: pytest.CaptureFixture[str]) -> None:
    assert validated_int({}, "k", 5, 1, 10) == 5
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize("value", [True, False, 3.0, "3", None, [3]])
def test_int_wrong_type_uses_default(value: object,
                                     capsys: pytest.CaptureFixture[str]) -> None:
    assert validated_int({"k": value}, "k", 5, 1, 10) == 5
    assert "'k'" in capsys.readouterr().err


@pytest.mark.parametrize("value, expected", [
    (1, 1), (10, 10), (0, 5), (11, 5), (-4, 5),
])
def test_int_range_is_inclusive(value: int, expected: int) -> None:
    assert validated_int({"k": value}, "k", 5, 1, 10) == expected


# ---- validated_str ----
def test_str_is_stripped() -> None:
    assert validated_str({"k": "  a.json "}, "k", "d") == "a.json"


@pytest.mark.parametrize("value", ["", "   ", 5, None])
def test_str_invalid_uses_default(value: object) -> None:
    assert validated_str({"k": value}, "k", "d") == "d"


def test_str_missing_uses_default() -> None:
    assert validated_str({}, "k", "d") == "d"


# ---- validated_levels ----
DEFAULT = tuple(LevelConfig(10 + i, 10) for i in range(MIN_LEVELS))


def test_levels_absent_uses_default() -> None:
    assert validated_levels({}, DEFAULT) == DEFAULT


@pytest.mark.parametrize("raw", [[], "x", 5, {"width": 5}])
def test_levels_not_a_nonempty_list(raw: object) -> None:
    assert validated_levels({"levels": raw}, DEFAULT) == DEFAULT


def test_levels_short_list_is_padded_from_the_default() -> None:
    out = validated_levels({"levels": [{"width": 7, "height": 8}]}, DEFAULT)
    assert len(out) == MIN_LEVELS
    assert out[0] == LevelConfig(7, 8) and out[1:] == DEFAULT[1:]


def test_levels_bad_entries_are_skipped() -> None:
    out = validated_levels({"levels": [5, "x", {"width": 7, "height": 8}]}, DEFAULT)
    assert out[0] == LevelConfig(7, 8) and len(out) == MIN_LEVELS


def test_levels_all_bad_falls_back_to_default() -> None:
    assert validated_levels({"levels": [1, 2]}, DEFAULT) == DEFAULT


def test_levels_missing_or_bad_sizes_use_the_base_size() -> None:
    out = validated_levels({"levels": [{"width": 7}, {"width": 3, "height": "x"}]},
                           DEFAULT)
    assert out[0] == LevelConfig(7, LevelConfig().height)
    assert out[1] == LevelConfig(LevelConfig().width, LevelConfig().height)


def test_levels_longer_than_ten_are_kept() -> None:
    raw = [{"width": 10, "height": 10}] * 12
    assert len(validated_levels({"levels": raw}, DEFAULT)) == 12


# ---- load_config ----
def test_missing_file_gives_every_default(tmp_path: Path) -> None:
    assert load_config(tmp_path / "nope.json") == Config()


def test_defaults_are_sane() -> None:
    c = Config()
    assert len(c.levels) >= MIN_LEVELS and c.lives >= 1 and c.seed >= 1
    assert all(5 <= lv.width and 5 <= lv.height for lv in c.levels)


def test_config_is_frozen() -> None:
    with pytest.raises(FrozenInstanceError):
        Config().lives = 9  # type: ignore[misc]


def test_a_full_valid_file(tmp_path: Path) -> None:
    c = cfg(tmp_path, """# comment
{"highscore_filename": "s.json", "lives": 5, "seed": 9, "level_max_time": 30,
 "points_per_pacgum": 1, "points_per_super_pacgum": 2, "points_per_ghost": 3,
 "pacgum": 7, "levels": [{"width": 11, "height": 9}]}""")
    assert (c.highscore_filename, c.lives, c.seed, c.level_max_time) == ("s.json", 5, 9, 30)
    assert (c.points_per_pacgum, c.points_per_super_pacgum, c.points_per_ghost) == (1, 2, 3)
    assert c.pacgum == 7 and c.levels[0] == LevelConfig(11, 9)
    assert len(c.levels) == MIN_LEVELS


@pytest.mark.parametrize("text, key, default", [
    ('{"lives": -5}', "lives", 3),
    ('{"lives": 100}', "lives", 3),
    ('{"lives": "abc"}', "lives", 3),
    ('{"lives": true}', "lives", 3),
    ('{"seed": 0}', "seed", 42),
    ('{"level_max_time": 0}', "level_max_time", 90),
    ('{"points_per_ghost": 10001}', "points_per_ghost", 200),
    ('{"highscore_filename": ""}', "highscore_filename", "highscore.json"),
])
def test_bad_values_fall_back_one_key_at_a_time(tmp_path: Path, text: str,
                                                key: str, default: object) -> None:
    assert getattr(cfg(tmp_path, text), key) == default


def test_one_bad_key_does_not_spoil_the_others(tmp_path: Path) -> None:
    c = cfg(tmp_path, '{"lives": "x", "seed": 7}')
    assert c.lives == 3 and c.seed == 7


def test_unknown_keys_are_ignored_with_a_note(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    c = cfg(tmp_path, '{"lifes": 9}')
    assert c.lives == 3 and "unknown key 'lifes'" in capsys.readouterr().err


def test_garbage_never_raises(tmp_path: Path) -> None:
    for text in ["", "{", "[[[", "null", '{"levels": {"a": 1}}', "\x00\x01"]:
        assert isinstance(cfg(tmp_path, text), Config)


def test_shipped_config_loads_cleanly(capsys: pytest.CaptureFixture[str]) -> None:
    c = load_config(ROOT / "config.json")
    assert (c.lives, c.seed, c.level_max_time) == (3, 42, 90)
    assert c.levels[0] == LevelConfig(20, 15) and c.levels[1] == LevelConfig(25, 18)
    assert len(c.levels) == MIN_LEVELS
    err = capsys.readouterr().err
    assert "invalid" not in err and "unknown" not in err