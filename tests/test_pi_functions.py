import builtins
import importlib
import json
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


def test_pi_load_config_reads_json_and_exits_if_missing(
    pi_modules, monkeypatch, tmp_path
):
    main, _, _ = pi_modules
    config_path = tmp_path / "config.json"
    expected = {"active_profile": "TEST"}
    config_path.write_text(json.dumps(expected), encoding="utf-8")
    monkeypatch.setattr(main, "CONFIG_PATH", str(config_path))
    assert main.load_config() == expected

    monkeypatch.setattr(main, "CONFIG_PATH", str(tmp_path / "missing.json"))
    with pytest.raises(SystemExit):
        main.load_config()


def test_pi_send_button_press_returns_false_when_connection_fails(
    pi_modules, monkeypatch
):
    main, _, _ = pi_modules

    def fail_socket(*args):
        raise OSError("connection refused")

    monkeypatch.setattr(main.socket, "socket", fail_socket)
    assert main.send_button_press("BTN_A") is False


def test_pi_local_test_mode_uses_virtual_hat_and_loopback(pi_modules, monkeypatch):
    main, _, _ = pi_modules

    monkeypatch.setenv("PI_RAINBOW_DECK_LOCAL_TEST", "1")
    importlib.reload(main)
    assert main.HOST_IP == "127.0.0.1"
    assert main.LOCAL_TEST_MODE

    monkeypatch.delenv("PI_RAINBOW_DECK_LOCAL_TEST")
    importlib.reload(main)
    assert main.HOST_IP == "192.168.7.1"
    assert not main.LOCAL_TEST_MODE


def test_virtual_hat_mode_does_not_import_hardware_driver(monkeypatch):
    monkeypatch.setenv("PI_RAINBOW_DECK_LOCAL_TEST", "1")
    monkeypatch.setenv("PI_RAINBOW_DECK_COMMAND_TOKEN", "a" * 64)
    monkeypatch.setitem(sys.modules, "rainbowhat", None)
    monkeypatch.delitem(sys.modules, "pi_rainbow_deck_pi.main", raising=False)
    monkeypatch.delitem(sys.modules, "pi_rainbow_deck_pi.hat_hardware", raising=False)

    main = importlib.import_module("pi_rainbow_deck_pi.main")

    assert main.LOCAL_TEST_MODE
    assert main.rh.__name__ == "pi_rainbow_deck_pi.virtual_hat"
    assert main.show_display.__module__ == "pi_rainbow_deck_pi.virtual_hat"


def test_virtual_hat_dispatches_selected_button(monkeypatch, capsys):
    from pi_rainbow_deck_pi import virtual_hat

    calls = []
    monkeypatch.setattr(
        virtual_hat.touch.A, "callback", lambda channel: calls.append(channel)
    )
    selections = iter(["a", "q"])
    monkeypatch.setattr(builtins, "input", lambda prompt: next(selections))
    quit_requests = []

    virtual_hat.run(lambda: quit_requests.append("quit") or True)

    assert calls == ["virtual"]
    assert quit_requests == ["quit"]
    output = capsys.readouterr().out
    assert "Press A, B, or C" in output
    assert "[VIRTUAL HAT] Host shutdown requested." in output


def test_pi_listen_for_telemetry_routes_context_and_token(pi_modules, monkeypatch):
    main, _, _ = pi_modules

    class Connection:
        def __init__(self, data):
            self.data = data

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def recv(self, size):
            return self.data

    class Listener:
        def __init__(self):
            self.connections = iter(
                [Connection(b"CTX:42.5"), Connection(b"TOK:10K "), Connection(b"OTHER")]
            )

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def setsockopt(self, *args):
            pass

        def bind(self, address):
            assert address == ("0.0.0.0", main.TELEMETRY_PORT)

        def listen(self):
            pass

        def accept(self):
            try:
                return next(self.connections), ("127.0.0.1", 1234)
            except StopIteration:
                raise KeyboardInterrupt

    monkeypatch.setattr(main.socket, "socket", lambda *args: Listener())
    gauge = Mock()
    display = Mock()
    monkeypatch.setattr(main, "set_context_gauge", gauge)
    monkeypatch.setattr(main, "show_display", display)

    with pytest.raises(KeyboardInterrupt):
        main.listen_for_telemetry()

    gauge.assert_called_once_with(42.5)
    display.assert_called_once_with("10K")


@pytest.mark.parametrize("success", [True, False])
def test_pi_handle_button_updates_feedback_and_cleans_up(
    pi_modules, monkeypatch, success
):
    main, _, _ = pi_modules
    events = []
    light = SimpleNamespace(
        on=lambda: events.append("on"),
        off=lambda: events.append("off"),
    )
    monkeypatch.setattr(
        main, "play_sound", lambda *args: events.append(("sound", args))
    )
    monkeypatch.setattr(
        main, "show_display", lambda value: events.append(("display", value))
    )
    monkeypatch.setattr(main, "send_button_press", lambda button: success)
    monkeypatch.setattr(
        main, "pulse_rainbow", lambda result: events.append(("pulse", result))
    )
    monkeypatch.setattr(
        main.time, "sleep", lambda delay: events.append(("sleep", delay))
    )
    main.UI_LABELS = {"display": "SAFE"}

    main.handle_button("BTN_A", "APPROVE", light)

    expected_display = "ERR " if not success else "SAFE"
    assert events[0] == ("sound", (1046, 0.03))
    assert events[1] == "on"
    assert ("pulse", success) in events
    assert ("display", expected_display) in events
    assert events[-2:] == ["off", ("display", "SAFE")]


@pytest.mark.parametrize(
    ("handler_name", "button_id", "label_key", "fallback", "light_name"),
    [
        ("handle_a", "BTN_A", "A_label", "Y   ", "red"),
        ("handle_b", "BTN_B", "B_label", "CMP ", "green"),
        ("handle_c", "BTN_C", "C_label", "STOP", "blue"),
    ],
)
def test_pi_touch_handlers_dispatch_button_action(
    pi_modules, monkeypatch, handler_name, button_id, label_key, fallback, light_name
):
    main, _, hat = pi_modules
    dispatched = []
    monkeypatch.setattr(main, "handle_button", lambda *args: dispatched.append(args))
    monkeypatch.setattr(main, "UI_LABELS", {label_key: "CUSTOM"})

    getattr(main, handler_name)("touch-event")

    assert dispatched == [(button_id, "CUSTOM", getattr(hat.lights, light_name))]

    monkeypatch.setattr(main, "UI_LABELS", {})
    getattr(main, handler_name)("touch-event")
    assert dispatched[-1] == (button_id, fallback, getattr(hat.lights, light_name))


def test_pi_cleanup_resets_hardware_then_exits(pi_modules, monkeypatch):
    main, _, _ = pi_modules
    reset = Mock()
    monkeypatch.setattr(main, "reset_hardware", reset)

    with pytest.raises(SystemExit) as result:
        main.cleanup(2, None)

    assert result.value.code == 0
    reset.assert_called_once_with()


def test_pi_main_requires_token_before_startup(pi_modules, monkeypatch):
    main, _, _ = pi_modules
    monkeypatch.setattr(main, "COMMAND_TOKEN", "")

    with pytest.raises(SystemExit) as result:
        main.main()

    assert result.value.code == 1


def test_pi_main_initializes_hardware_and_starts_telemetry(pi_modules, monkeypatch):
    main, _, hat = pi_modules
    monkeypatch.setattr(main, "COMMAND_TOKEN", "a" * 64)
    signal_calls = []
    monkeypatch.setattr(main.signal, "signal", lambda *args: signal_calls.append(args))
    thread = SimpleNamespace(start=Mock())
    monkeypatch.setattr(main.threading, "Thread", lambda **kwargs: thread)
    monkeypatch.setattr(
        main.signal,
        "pause",
        lambda: (_ for _ in ()).throw(SystemExit(0)),
        raising=False,
    )
    display = Mock()
    monkeypatch.setattr(main, "show_display", display)

    with pytest.raises(SystemExit):
        main.main()

    display.assert_called_once_with(main.UI_LABELS.get("display", "CLAU"))
    hat.lights.clear.assert_called_once_with()
    hat.rainbow.clear.assert_called_once_with()
    hat.rainbow.show.assert_called_once_with()
    assert len(signal_calls) == 2
    thread.start.assert_called_once_with()
    assert thread.start.call_args is not None
