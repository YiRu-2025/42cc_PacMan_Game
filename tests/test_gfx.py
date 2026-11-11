from pathlib import Path

import pygame
import pytest

import pacman.gfx.gfx as gfx_mod
from pacman.constants import MAX_FRAME_DT
from pacman.gfx import Gfx, GfxError
from pacman.gfx.gfx import _resample, _transform


def surface(width: int, height: int, pixels: dict[tuple[int, int], tuple[int, int, int]]
            ) -> pygame.Surface:
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    for (x, y), c in pixels.items():
        s.set_at((x, y), (*c, 255))
    return s


RED, GREEN, BLUE = (255, 0, 0), (0, 255, 0), (0, 0, 255)


def px(s: pygame.Surface, x: int, y: int) -> tuple[int, int, int]:
    r, g, b, _ = s.get_at((x, y))
    return r, g, b


# ---- pure pixel code (needs no window) ----
def test_transform_without_changes_returns_the_same_surface() -> None:
    s = surface(2, 1, {(0, 0): RED, (1, 0): GREEN})
    assert _transform(s, 0, False) is s and _transform(s, 4, False) is s


def test_quarter_turn_is_clockwise_and_swaps_the_size() -> None:
    s = surface(2, 1, {(0, 0): RED, (1, 0): GREEN})
    out = _transform(s, 1, False)
    assert out.get_size() == (1, 2)
    assert px(out, 0, 0) == RED and px(out, 0, 1) == GREEN


def test_half_turn_reverses_both_axes() -> None:
    s = surface(2, 1, {(0, 0): RED, (1, 0): GREEN})
    out = _transform(s, 2, False)
    assert px(out, 0, 0) == GREEN and px(out, 1, 0) == RED


def test_flip_mirrors_horizontally() -> None:
    s = surface(2, 1, {(0, 0): RED, (1, 0): GREEN})
    out = _transform(s, 0, True)
    assert px(out, 0, 0) == GREEN and px(out, 1, 0) == RED


def test_four_quarter_turns_restore_the_image() -> None:
    pixels = {(0, 0): RED, (1, 0): GREEN, (2, 0): BLUE,
              (0, 1): BLUE, (1, 1): RED, (2, 1): GREEN}
    s = surface(3, 2, pixels)
    out = s
    for _ in range(4):
        out = _transform(out, 1, False)
    assert out.get_size() == (3, 2)
    assert all(px(out, x, y) == c for (x, y), c in pixels.items())


def test_resample_upscales_with_nearest_neighbour() -> None:
    s = surface(2, 1, {(0, 0): RED, (1, 0): GREEN})
    out = _resample(s, 4, 2)
    assert out.get_size() == (4, 2)
    assert [px(out, x, 0) for x in range(4)] == [RED, RED, GREEN, GREEN]


def test_resample_downscales_and_stretches_one_axis() -> None:
    s = surface(4, 1, {(0, 0): RED, (1, 0): RED, (2, 0): GREEN, (3, 0): GREEN})
    out = _resample(s, 2, 3)
    assert out.get_size() == (2, 3) and px(out, 0, 2) == RED and px(out, 1, 1) == GREEN


# ---- the window (dummy video driver) ----
@pytest.fixture
def gfx() -> Gfx:
    try:
        g = Gfx(120, 80, "test")
    except GfxError:
        pytest.skip("no SDL video driver available")
    yield g
    g.close()


def test_screen_size_and_resize(gfx: Gfx) -> None:
    assert gfx.screen_size() == (120, 80)
    gfx.resize(200, 100)
    assert gfx.screen_size() == (200, 100)


def test_fill_rect_ignores_empty_sizes(gfx: Gfx) -> None:
    gfx.fill_rect((1, 2, 3), 0, 0, 0, 5)
    gfx.fill_rect((1, 2, 3), 0, 0, 5, -1)
    assert gfx._fills == {}
    gfx.fill_rect((1, 2, 3), 0, 0, 5, 5)
    gfx.fill_rect((1, 2, 3), 9, 9, 5, 5)
    assert len(gfx._fills) == 1                      # same surface, reused


def test_text_measure_and_draw(gfx: Gfx) -> None:
    w, h = gfx.text_size("hello", 30)
    assert w > 0 and h > 0 and gfx.text_size("hello!", 30)[0] > w
    gfx.draw_text("", 0, 0, 30, (0, 0, 0))          # nothing, no error
    gfx.draw_text("hi", 0, 0, 30, (0, 0, 0))


def test_missing_sprite_reports_false_once(gfx: Gfx) -> None:
    assert gfx.draw_sprite("no/such.png", 0, 0, 10) is False
    assert gfx.has_sprite("no/such.png", 10) is False
    assert gfx.draw_sprite("x.png", 0, 0, 0) is False        # zero size


def test_sprite_loads_scales_and_caches(gfx: Gfx, tmp_path: Path,
                                        monkeypatch: pytest.MonkeyPatch) -> None:
    pygame.image.save(surface(2, 2, {(0, 0): RED}), str(tmp_path / "s.png"))
    monkeypatch.setattr(gfx_mod, "ASSETS_DIR", str(tmp_path))
    assert gfx.draw_sprite("s.png", 0, 0, 8) is True
    assert gfx.draw_sprite("s.png", 0, 0, 8, turns=1, flip_x=True) is True
    assert len(gfx._sprites) == 2


def test_corrupt_sprite_is_treated_as_absent(gfx: Gfx, tmp_path: Path,
                                             monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "bad.png").write_bytes(b"not a png")
    monkeypatch.setattr(gfx_mod, "ASSETS_DIR", str(tmp_path))
    assert gfx.draw_sprite("bad.png", 0, 0, 8) is False


def test_no_events_when_idle(gfx: Gfx) -> None:
    assert gfx.poll_events() == []


def test_present_caps_the_frame_time(gfx: Gfx) -> None:
    assert 0.0 <= gfx.present() <= MAX_FRAME_DT


def test_close_is_idempotent() -> None:
    try:
        g = Gfx(50, 50)
    except GfxError:
        pytest.skip("no SDL video driver available")
    g.close()
    g.close()