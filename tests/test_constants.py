import sys
from pathlib import Path

import pytest

import pacman.constants as C
from pacman.constants import Direction, WALL_ORDER


# ---- directions ----
def test_direction_vectors() -> None:
    assert [(d.dx, d.dy) for d in WALL_ORDER] == [(0, -1), (1, 0), (0, 1), (-1, 0)]


@pytest.mark.parametrize("d", list(Direction))
def test_opposite_is_an_involution(d: Direction) -> None:
    assert d.opposite().opposite() is d and d.opposite() is not d
    assert (d.dx + d.opposite().dx, d.dy + d.opposite().dy) == (0, 0)


# ---- cell size ----
def test_small_maze_uses_the_target_size() -> None:
    assert C.cell_size_for(10, 10) == C.TARGET_CELL_SIZE


def test_huge_maze_is_floored_at_the_minimum() -> None:
    assert C.cell_size_for(500, 500) == C.MIN_CELL_SIZE


@pytest.mark.parametrize("w, h", [(0, 5), (5, 0), (-1, -1)])
def test_degenerate_sizes_do_not_crash(w: int, h: int) -> None:
    assert C.cell_size_for(w, h) == C.TARGET_CELL_SIZE


def test_cell_size_never_grows_with_the_maze() -> None:
    sizes = [C.cell_size_for(n, n) for n in range(5, 120, 5)]
    assert sizes == sorted(sizes, reverse=True)
    assert all(C.MIN_CELL_SIZE <= s <= C.TARGET_CELL_SIZE for s in sizes)


def test_typical_maze_fits_the_window() -> None:
    s = C.cell_size_for(24, 15)
    assert 24 * s <= C.MAX_WINDOW_WIDTH
    assert 15 * s + C.HUD_HEIGHT <= C.MAX_WINDOW_HEIGHT


# ---- names ----
def test_name_charset_is_ascii_alnum_and_space() -> None:
    assert " " in C.NAME_CHARSET and "a" in C.NAME_CHARSET and "9" in C.NAME_CHARSET
    assert "é" not in C.NAME_CHARSET and "_" not in C.NAME_CHARSET
    assert len(C.NAME_CHARSET) == 26 * 2 + 10 + 1


# ---- sprite paths ----
def test_wall_sprite_name_is_news_order() -> None:
    assert C.wall_sprite(frozenset({Direction.NORTH, Direction.EAST})) == "walls/wall_1100.png"
    assert C.wall_sprite(frozenset()) == "walls/wall_0000.png"
    assert C.wall_sprite(frozenset(WALL_ORDER)) == "walls/wall_1111.png"


def test_all_sixteen_wall_names_are_distinct() -> None:
    names = set()
    for mask in range(16):
        walls = frozenset(d for i, d in enumerate(WALL_ORDER) if mask >> i & 1)
        names.add(C.wall_sprite(walls))
    assert len(names) == 16


def test_sprite_builders() -> None:
    assert C.wall_edge_sprite(Direction.WEST) == "walls/edge_w.png"
    assert C.player_sprite(Direction.EAST, 1) == "player/player_e_1.png"
    assert C.player_sprite(Direction.EAST, 4) == "player/player_e_1.png"   # wraps
    assert C.player_base_sprite(3) == "player/player_0.png"
    assert C.ghost_sprite(2, 1, "frightened") == "ghosts/ghost_2_frightened_1.png"
    assert C.ghost_body_sprite(2) == "ghosts/body_0.png"
    assert C.ghost_hat_sprite(3) == "ghosts/hat_3.png"
    assert C.ghost_state_sprite("dead", 1) == "ghosts/dead_1.png"
    assert C.digit_sprite("A") == "ui/glyph_a.png"


def test_every_direction_has_a_player_transform() -> None:
    assert set(C.PLAYER_TRANSFORM) == set(Direction)


def test_every_layer_has_a_fallback_colour() -> None:
    assert set(C.FALLBACK_COLORS) == set(C.Layer)
    for rgb in C.FALLBACK_COLORS.values():
        assert len(rgb) == 3 and all(0 <= v <= 255 for v in rgb)


def test_cheat_bindings_are_digits_with_descriptions() -> None:
    assert set(C.CHEAT_BINDINGS) == set("12345")
    assert all(C.CHEAT_BINDINGS.values())


# ---- resource and data paths ----
def test_assets_dir_exists_and_is_absolute() -> None:
    assert Path(C.ASSETS_DIR).is_absolute() and Path(C.ASSETS_DIR).is_dir()


def test_resource_path_from_source() -> None:
    assert C.resource_path("assets") == C.ASSETS_DIR


def test_resource_path_uses_meipass_when_frozen(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert C.resource_path("assets") == str(tmp_path / "assets")


def test_data_dir_from_source_is_the_working_directory(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.chdir(tmp_path)
    assert not C.is_frozen()
    assert C.data_dir() == Path.cwd()
    assert C.data_path("h.json") == Path.cwd() / "h.json"


def test_data_dir_frozen_is_beside_the_executable(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "pac-man"))
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "temp"), raising=False)
    assert C.data_dir() == tmp_path.resolve()
    assert C.data_path("h.json") == tmp_path.resolve() / "h.json"


def test_data_dir_frozen_falls_back_when_not_writable(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "pac-man"))
    monkeypatch.setattr(C.os, "access", lambda *a, **k: False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    assert C.data_dir() == tmp_path / "home" / ".pac-man"


def test_absolute_data_path_is_kept(tmp_path: Path) -> None:
    assert C.data_path(str(tmp_path / "x.json")) == tmp_path / "x.json"