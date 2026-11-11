from pacman.cheat import CHEAT_ACTIONS, Cheat, CheatMode
from pacman.constants import CHEAT_BINDINGS


def test_every_binding_has_an_action() -> None:
    assert set(CHEAT_ACTIONS) == set(CHEAT_BINDINGS)


def test_every_mode_is_bound_to_a_key() -> None:
    assert set(CHEAT_ACTIONS.values()) == set(CheatMode)


def test_starts_enabled_with_everything_off() -> None:
    c = Cheat()
    assert c.enabled
    assert not (c.invincible or c.freeze or c.speed)
    assert c.consume_skip() is False and c.consume_lives() == 0
    assert c.active_labels() == []


def test_skip_is_one_shot() -> None:
    c = Cheat()
    assert c.handle_key("1")
    assert c.consume_skip() is True
    assert c.consume_skip() is False


def test_repeated_skip_requests_collapse_into_one() -> None:
    c = Cheat()
    c.handle_key("1")
    c.handle_key("1")
    assert c.consume_skip() is True and c.consume_skip() is False


def test_toggles_flip_back() -> None:
    c = Cheat()
    for key, attr in (("2", "invincible"), ("3", "freeze"), ("5", "speed")):
        assert c.handle_key(key)
        assert getattr(c, attr)
        assert c.handle_key(key)
        assert not getattr(c, attr)


def test_lives_accumulate_then_reset() -> None:
    c = Cheat()
    c.handle_key("4")
    c.handle_key("4")
    assert c.consume_lives() == 2
    assert c.consume_lives() == 0


def test_toggles_are_independent() -> None:
    c = Cheat()
    c.handle_key("2")
    c.handle_key("3")
    assert c.invincible and c.freeze and not c.speed


def test_unknown_key_is_not_consumed() -> None:
    c = Cheat()
    for ch in ("x", "", "0", "6", "12"):
        assert c.handle_key(ch) is False
    assert not (c.invincible or c.freeze or c.speed)


def test_disabled_cheats_do_nothing() -> None:
    c = Cheat(enabled=False)
    assert c.handle_key("1") is False
    assert c.handle_key("2") is False
    assert c.invincible is False
    assert c.consume_skip() is False and c.active_labels() == []


def test_disabling_clears_everything() -> None:
    c = Cheat()
    for key in "12345":
        c.handle_key(key)
    c.set_enabled(False)
    assert not (c.invincible or c.freeze or c.speed)
    assert c.consume_skip() is False and c.consume_lives() == 0


def test_toggle_enabled_round_trip() -> None:
    c = Cheat()
    c.toggle_enabled()
    assert not c.enabled
    c.toggle_enabled()
    assert c.enabled


def test_active_labels_in_fixed_order() -> None:
    c = Cheat()
    c.handle_key("5")
    c.handle_key("3")
    c.handle_key("2")
    assert c.active_labels() == ["INVINCIBLE", "FREEZE", "SPEED"]


def test_one_shot_requests_are_not_labels() -> None:
    c = Cheat()
    c.handle_key("1")
    c.handle_key("4")
    assert