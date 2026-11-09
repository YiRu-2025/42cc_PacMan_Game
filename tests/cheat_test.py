from pacman.cheat import CHEAT_ACTIONS, Cheat
from pacman.constants import CHEAT_BINDINGS


def test_every_binding_has_an_action() -> None:
    assert set(CHEAT_ACTIONS) == set(CHEAT_BINDINGS)


def test_skip_is_one_shot() -> None:
    c = Cheat()
    assert c.handle_key("1")
    assert c.consume_skip() is True
    assert c.consume_skip() is False


def test_toggle() -> None:
    c = Cheat()
    c.handle_key("2")
    assert c.invincible
    c.handle_key("2")
    assert not c.invincible
