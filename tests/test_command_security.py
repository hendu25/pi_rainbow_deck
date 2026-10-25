import hashlib
import hmac
import json
import os
import socket
import sys
import threading
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "a" * 64


def _import_pi_main(monkeypatch):
    class TouchButton:
        def press(self):
            return lambda callback: callback

    rainbowhat = types.ModuleType("rainbowhat")
    rainbowhat.touch = types.SimpleNamespace(
        A=TouchButton(), B=TouchButton(), C=TouchButton()
    )
    rainbowhat.lights = types.SimpleNamespace(
        red=object(), green=object(), blue=object()
    )
    rainbowhat.rainbow = object()
    monkeypatch.setitem(sys.modules, "rainbowhat", rainbowhat)

    hardware = types.ModuleType("hat_hardware")
    hardware.play_sound = lambda *args: None
    hardware.show_display = lambda *args: None
    hardware.set_context_gauge = lambda *args: None
    hardware.pulse_rainbow = lambda *args: None
    hardware.reset_hardware = lambda *args: None
    monkeypatch.setitem(sys.modules, "pi_rainbow_deck_pi.hat_hardware", hardware)

    previous_token = os.environ.get("CLAUDE_DECK_COMMAND_TOKEN")
    os.environ["CLAUDE_DECK_COMMAND_TOKEN"] = TOKEN
    try:
        from pi_rainbow_deck_pi import main

        return main
    finally:
        if previous_token is None:
            os.environ.pop("CLAUDE_DECK_COMMAND_TOKEN", None)
        else:
            os.environ["CLAUDE_DECK_COMMAND_TOKEN"] = previous_token


def signed_command(button_id="BTN_A", timestamp=None, token=TOKEN, **extra_fields):
    payload = {
        "button_id": button_id,
        "timestamp": int(time.time()) if timestamp is None else timestamp,
        "nonce": "0123456789abcdef0123456789abcdef",
    }
    payload.update(extra_fields)
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    signature = hmac.new(
        token.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return json.dumps(
        {"payload": payload, "signature": signature},
        separators=(",", ":"),
    ).encode("utf-8")


def test_pi_command_authenticates_and_dispatches_over_localhost(monkeypatch):
    from pi_rainbow_deck_host import bridge

    pi_main = _import_pi_main(monkeypatch)
    config = json.loads(
        (ROOT / "src" / "pi_rainbow_deck_host" / "config.json").read_text()
    )
    actions = config["profiles"]["SAFETY"]
    used_nonces = {}

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        pi_main.HOST_IP, pi_main.PORT = listener.getsockname()

        received = []
        server_error = []

        def receive_and_validate():
            try:
                conn, _ = listener.accept()
                with conn:
                    data = bridge.receive_command(conn)
                button_id = bridge.validate_command(data, TOKEN, used_nonces)
                received.append(actions.get(button_id))
            except Exception as error:
                server_error.append(error)

        server = threading.Thread(target=receive_and_validate)
        server.start()
        assert pi_main.send_button_press("BTN_A") is True
        server.join(timeout=3)

    assert not server.is_alive(), "local command receiver did not finish"
    assert not server_error
    assert received == ["APPROVE"]


def test_host_rejects_replayed_command():
    from pi_rainbow_deck_host import bridge

    packet = signed_command()
    used_nonces = {}

    assert bridge.validate_command(packet, TOKEN, used_nonces) == "BTN_A"
    assert bridge.validate_command(packet, TOKEN, used_nonces) is None


def test_host_rejects_invalid_signature():
    from pi_rainbow_deck_host import bridge

    packet = json.loads(signed_command())
    packet["signature"] = "0" * 64

    assert (
        bridge.validate_command(json.dumps(packet).encode("utf-8"), TOKEN, {}) is None
    )


def test_host_rejects_expired_command():
    from pi_rainbow_deck_host import bridge

    packet = signed_command(timestamp=int(time.time()) - 60)

    assert bridge.validate_command(packet, TOKEN, {}) is None


def test_host_rejects_malformed_command():
    from pi_rainbow_deck_host import bridge

    assert bridge.validate_command(b"not-json", TOKEN, {}) is None
    assert (
        bridge.validate_command(
            signed_command(extra_fields={"unexpected": 1}), TOKEN, {}
        )
        is None
    )


def test_receive_command_reads_newline_terminated_message():
    from pi_rainbow_deck_host import bridge

    sender, receiver = socket.socketpair()
    try:
        sender.sendall(b'{"command":"ok"}\n')
        sender.shutdown(socket.SHUT_WR)

        assert bridge.receive_command(receiver) == b'{"command":"ok"}'
    finally:
        sender.close()
        receiver.close()
