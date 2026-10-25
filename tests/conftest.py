import importlib
import sys
import types

import pytest


@pytest.fixture
def fake_rainbowhat(monkeypatch):
    def recorder():
        from unittest.mock import Mock

        return Mock()

    class TouchButton:
        def press(self):
            return lambda callback: callback

    hat = types.ModuleType("rainbowhat")
    hat.buzzer = types.SimpleNamespace(note=recorder())
    hat.display = types.SimpleNamespace(
        clear=recorder(), print_str=recorder(), show=recorder()
    )
    hat.lights = types.SimpleNamespace(
        red=types.SimpleNamespace(on=recorder(), off=recorder()),
        green=types.SimpleNamespace(on=recorder(), off=recorder()),
        blue=types.SimpleNamespace(on=recorder(), off=recorder()),
        clear=recorder(),
    )
    hat.rainbow = types.SimpleNamespace(
        clear=recorder(),
        set_pixel=recorder(),
        set_all=recorder(),
        show=recorder(),
    )
    hat.touch = types.SimpleNamespace(A=TouchButton(), B=TouchButton(), C=TouchButton())
    monkeypatch.setitem(sys.modules, "rainbowhat", hat)
    monkeypatch.delitem(sys.modules, "claude_deck_pi.main", raising=False)
    monkeypatch.delitem(sys.modules, "claude_deck_pi.hat_hardware", raising=False)
    return hat


@pytest.fixture
def pi_modules(monkeypatch, fake_rainbowhat):
    monkeypatch.setenv("CLAUDE_DECK_COMMAND_TOKEN", "a" * 64)
    hardware = importlib.import_module("claude_deck_pi.hat_hardware")
    main = importlib.import_module("claude_deck_pi.main")
    return main, hardware, fake_rainbowhat
