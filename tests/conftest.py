import importlib
import sys
import types

import pytest

if sys.platform.startswith("linux"):
    pyautogui = types.ModuleType("pyautogui")
    pyautogui.typewrite = lambda *args, **kwargs: None
    pyautogui.press = lambda *args, **kwargs: None
    pyautogui.hotkey = lambda *args, **kwargs: None
    sys.modules.setdefault("pyautogui", pyautogui)


@pytest.fixture(autouse=True)
def isolate_application_environment(monkeypatch):
    monkeypatch.delenv("PI_RAINBOW_DECK_COMMAND_TOKEN", raising=False)
    monkeypatch.delenv("PI_RAINBOW_DECK_LOCAL_TEST", raising=False)


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
    monkeypatch.delitem(sys.modules, "pi_rainbow_deck_pi.main", raising=False)
    monkeypatch.delitem(sys.modules, "pi_rainbow_deck_pi.hat_hardware", raising=False)
    return hat


@pytest.fixture
def pi_modules(monkeypatch, fake_rainbowhat):
    monkeypatch.setenv("PI_RAINBOW_DECK_COMMAND_TOKEN", "a" * 64)
    hardware = importlib.import_module("pi_rainbow_deck_pi.hat_hardware")
    main = importlib.import_module("pi_rainbow_deck_pi.main")
    return main, hardware, fake_rainbowhat
