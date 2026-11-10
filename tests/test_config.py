# from pathlib import Path
from pacman.config import read_raw_config


def test_valid_file_with_comments(tmp_path):
    f = tmp_path / "c.json"
    f.write_text('# comment\n{"lives": 3}\n')
    assert read_raw_config(f) == {"lives": 3}


def test_missing_file_returns_empty(tmp_path):
    assert read_raw_config(tmp_path / "nope.json") == {}


def test_broken_json_returns_empty(tmp_path):
    f = tmp_path / "c.json"
    f.write_text('{"lives": }')
    assert read_raw_config(f) == {}


def test_list_returns_empty(tmp_path):
    f = tmp_path / "c.json"
    f.write_text('[1, 2]')
    assert read_raw_config(f) == {}
