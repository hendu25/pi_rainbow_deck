import json
import socket
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from claude_deck_host import bridge, keystrokes, log_monitor


ROOT = Path(__file__).resolve().parents[1]
TOKEN = "a" * 64


def _signed_command(button_id="BTN_A", timestamp=None, nonce="1" * 32):
    import hashlib
    import hmac

    payload = {
        "button_id": button_id,
        "timestamp": int(time.time()) if timestamp is None else timestamp,
        "nonce": nonce,
    }
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    signature = hmac.new(TOKEN.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    return json.dumps(
        {"payload": payload, "signature": signature}, separators=(",", ":")
    ).encode()


def test_bridge_load_config_reads_json_and_exits_if_missing(monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    expected = {"active_profile": "TEST"}
    config_path.write_text(json.dumps(expected), encoding="utf-8")
    monkeypatch.setattr(bridge, "CONFIG_PATH", str(config_path))
    assert bridge.load_config() == expected

    monkeypatch.setattr(bridge, "CONFIG_PATH", str(tmp_path / "missing.json"))
    with pytest.raises(SystemExit):
        bridge.load_config()


def test_bridge_validate_command_accepts_valid_and_prunes_expired_nonce():
    old_nonce = "f" * 32
    nonces = {old_nonce: int(time.time()) - bridge.COMMAND_TIMESTAMP_WINDOW - 1}
    assert bridge.validate_command(_signed_command(), TOKEN, nonces) == "BTN_A"
    assert old_nonce not in nonces
    assert nonces["1" * 32] > 0


@pytest.mark.parametrize(
    "packet",
    [
        b"\xff",
        b"[]",
        b'{"payload": {}, "signature": "x"}',
        b'{"payload": {"button_id": 3, "timestamp": 1, "nonce": "'
        + b"0" * 32
        + b'"}, "signature": "x"}',
        b'{"payload": {"button_id": "BTN_A", "timestamp": true, "nonce": "'
        + b"0" * 32
        + b'"}, "signature": "x"}',
        b'{"payload": {"button_id": "BTN_A", "timestamp": 1, "nonce": "bad"}, "signature": "x"}',
    ],
)
def test_bridge_validate_command_rejects_invalid_fields(packet):
    assert bridge.validate_command(packet, TOKEN, {}) is None


def test_bridge_receive_command_sets_timeout_and_rejects_oversized_data():
    class Connection:
        def __init__(self, chunks):
            self.chunks = iter(chunks)
            self.timeout = None

        def settimeout(self, timeout):
            self.timeout = timeout

        def recv(self, size):
            return next(self.chunks)

    conn = Connection([b""])
    assert bridge.receive_command(conn) is None
    assert conn.timeout == 2.0

    conn = Connection([b"x" * (bridge.MAX_COMMAND_BYTES + 1)])
    with pytest.raises(ValueError, match="exceeds maximum size"):
        bridge.receive_command(conn)


def test_bridge_main_dispatches_valid_command_and_ignores_unmapped(monkeypatch):
    valid = _signed_command(nonce="2" * 32)
    unmapped = _signed_command("BTN_UNKNOWN", nonce="3" * 32)
    invalid = b"not-json"

    class Connection:
        def __init__(self, data):
            self.data = data

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def settimeout(self, timeout):
            pass

        def recv(self, size):
            data, self.data = self.data, b""
            return data + (b"\n" if data else b"")

    class Listener:
        def __init__(self):
            self.connections = iter(
                [Connection(valid), Connection(invalid), Connection(unmapped)]
            )
            self.bind_address = None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def setsockopt(self, *args):
            pass

        def bind(self, address):
            self.bind_address = address

        def listen(self):
            pass

        def accept(self):
            try:
                return next(self.connections), ("127.0.0.1", 1234)
            except StopIteration:
                raise KeyboardInterrupt

    listener = Listener()
    monkeypatch.setattr(bridge, "load_config", lambda: {
        "active_profile": "SAFETY",
        "networking": {"host_ip": "127.0.0.1", "command_port": 0},
        "claude": {"context_window_limit": 100},
        "profiles": {"SAFETY": {"BTN_A": "APPROVE"}},
    })
    monkeypatch.setenv("CLAUDE_DECK_COMMAND_TOKEN", TOKEN)
    monkeypatch.setattr(bridge.socket, "socket", lambda *args: listener)
    thread = SimpleNamespace(start=Mock())
    monkeypatch.setattr(bridge.threading, "Thread", lambda **kwargs: thread)
    action = Mock()
    monkeypatch.setattr(bridge, "execute_action", action)

    bridge.main()

    assert listener.bind_address == ("127.0.0.1", 0)
    action.assert_called_once_with("APPROVE")
    thread.start.assert_called_once()


def test_bridge_main_rejects_missing_token_before_starting(monkeypatch):
    monkeypatch.setattr(bridge, "load_config", lambda: {})
    monkeypatch.delenv("CLAUDE_DECK_COMMAND_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="CLAUDE_DECK_COMMAND_TOKEN"):
        bridge.main()


@pytest.mark.parametrize(
    ("action_id", "expected"),
    [
        ("APPROVE", ['keystroke "y"', "key code 36"]),
        ("COMPACT", ['keystroke "/compact"', "key code 36"]),
        ("DIFF", ['keystroke "/diff"', "key code 36"]),
        ("COST", ['keystroke "/cost"', "key code 36"]),
        ("TASKS", ['keystroke "/tasks"', "key code 36"]),
        ("REWIND", ["key code 53", "key code 53"]),
        ("ABORT", ["key down control", 'keystroke "c"', "key up control"]),
    ],
)
def test_execute_action_runs_macos_keystrokes(monkeypatch, action_id, expected):
    calls = []
    monkeypatch.setattr(keystrokes, "IS_MAC", True)
    monkeypatch.setattr(keystrokes, "IS_WIN", False)
    monkeypatch.setattr(keystrokes.subprocess, "run", lambda command: calls.append(command[-1]))
    monkeypatch.setattr(keystrokes.time, "sleep", lambda delay: None)

    keystrokes.execute_action(action_id)

    assert [call.rsplit("to ", 1)[-1] for call in calls] == expected


def test_execute_action_runs_windows_keystrokes_and_ignores_unknown(monkeypatch):
    calls = []
    pyautogui = SimpleNamespace(
        typewrite=lambda text: calls.append(("typewrite", text)),
        press=lambda key: calls.append(("press", key)),
        hotkey=lambda *keys: calls.append(("hotkey", *keys)),
    )
    monkeypatch.setattr(keystrokes, "IS_MAC", False)
    monkeypatch.setattr(keystrokes, "IS_WIN", True)
    monkeypatch.setattr(keystrokes, "pyautogui", pyautogui, raising=False)

    keystrokes.execute_action("APPROVE")
    assert calls == [("typewrite", "y"), ("press", "enter")]
    calls.clear()
    keystrokes.execute_action("REWIND")
    assert calls == [("press", "esc"), ("press", "esc")]
    calls.clear()
    keystrokes.execute_action("ABORT")
    assert calls == [("hotkey", "ctrl", "c")]
    calls.clear()
    keystrokes.execute_action("UNKNOWN")
    assert calls == []


def test_execute_action_uses_pyautogui_on_linux(monkeypatch):
    calls = []
    pyautogui = SimpleNamespace(
        typewrite=lambda text: calls.append(("typewrite", text)),
        press=lambda key: calls.append(("press", key)),
        hotkey=lambda *keys: calls.append(("hotkey", *keys)),
    )
    monkeypatch.setattr(keystrokes, "IS_MAC", False)
    monkeypatch.setattr(keystrokes, "IS_WIN", False)
    monkeypatch.setattr(keystrokes, "IS_LINUX", True)
    monkeypatch.setattr(keystrokes, "pyautogui", pyautogui, raising=False)

    keystrokes.execute_action("DIFF")

    assert calls == [("typewrite", "/diff"), ("press", "enter")]


def test_get_latest_claude_log_finds_newest_and_handles_missing_dir(monkeypatch):
    logs = ["older.jsonl", "newer.jsonl"]
    monkeypatch.setattr(log_monitor.os.path, "expanduser", lambda path: "claude")
    monkeypatch.setattr(log_monitor.os.path, "exists", lambda path: True)
    monkeypatch.setattr(log_monitor.glob, "glob", lambda *args, **kwargs: logs)
    monkeypatch.setattr(
        log_monitor.os.path, "getmtime", lambda path: {"older.jsonl": 1, "newer.jsonl": 2}[path]
    )
    assert log_monitor.get_latest_claude_log() == "newer.jsonl"
    monkeypatch.setattr(log_monitor.os.path, "exists", lambda path: False)
    assert log_monitor.get_latest_claude_log() is None


def test_send_telemetry_sends_message_and_swallows_unreachable_pi(monkeypatch):
    sent = []

    class FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def settimeout(self, timeout):
            assert timeout == 1.0

        def connect(self, address):
            assert address == ("127.0.0.1", 5001)

        def sendall(self, data):
            sent.append(data)

    monkeypatch.setattr(log_monitor.socket, "socket", lambda *args: FakeSocket())
    log_monitor.send_telemetry("CTX:10.0", "127.0.0.1", 5001)
    assert sent == [b"CTX:10.0"]

    monkeypatch.setattr(
        log_monitor.socket, "socket", lambda *args: (_ for _ in ()).throw(OSError())
    )
    log_monitor.send_telemetry("CTX:10.0", "127.0.0.1", 5001)


def test_start_log_monitor_processes_usage_and_sends_changed_telemetry(monkeypatch):
    records = [
        '{"usage":{"input_tokens":100}}',
        '{"usage":{"input_tokens":100}}',
        '{"message":{"usage":{"input_tokens":1000,"output_tokens":1000}}}',
        '{"not":"usage"}',
        "invalid-json",
    ]

    class FakeLog:
        def seek(self, offset, whence):
            pass

        def readlines(self):
            return records

        def close(self):
            pass

    reads = 0

    def latest_log():
        nonlocal reads
        reads += 1
        if reads > 1:
            raise KeyboardInterrupt
        return "session.jsonl"

    sent = []
    monkeypatch.setattr(log_monitor, "get_latest_claude_log", latest_log)
    monkeypatch.setattr(log_monitor, "open", lambda *args, **kwargs: FakeLog(), raising=False)
    monkeypatch.setattr(log_monitor, "send_telemetry", lambda *args: sent.append(args))
    monkeypatch.setattr(log_monitor.time, "sleep", lambda delay: None)

    with pytest.raises(KeyboardInterrupt):
        log_monitor.start_log_monitor("pi", 5001, 2000)

    assert sent == [
        ("CTX:5.0", "pi", 5001),
        ("TOK:100 ", "pi", 5001),
        ("CTX:100.0", "pi", 5001),
        ("TOK:2K  ", "pi", 5001),
    ]
