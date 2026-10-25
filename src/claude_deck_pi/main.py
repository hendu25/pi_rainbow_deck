#!/usr/bin/env python3
import os
import sys
import time
import socket
import signal
import json
import threading
import hashlib
import hmac
import re
import secrets
import rainbowhat as rh

if __package__:
    from .hat_hardware import (
        play_sound,
        show_display,
        set_context_gauge,
        pulse_rainbow,
        reset_hardware
    )
else:
    from hat_hardware import (
        play_sound,
        show_display,
        set_context_gauge,
        pulse_rainbow,
        reset_hardware
    )

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"[ERROR] Missing config file: {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

config = load_config()
active_profile = config.get("active_profile", "SAFETY")
networking = config.get("networking", {})

HOST_IP = networking.get("host_ip", "192.168.7.1")
PORT = networking.get("command_port", 5000)
TELEMETRY_PORT = networking.get("telemetry_port", 5001)
COMMAND_TOKEN = os.environ.get("CLAUDE_DECK_COMMAND_TOKEN", "")

PI_UI = config.get("profiles", {}).get(active_profile, {}).get("display", "SAFE")
UI_LABELS = config.get("profiles", {}).get(active_profile, {})

def send_button_press(button_id: str) -> bool:
    try:
        payload = {
            "button_id": button_id,
            "timestamp": int(time.time()),
            "nonce": secrets.token_hex(16)
        }
        canonical_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        signature = hmac.new(
            COMMAND_TOKEN.encode("utf-8"),
            canonical_payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        message = json.dumps(
            {"payload": payload, "signature": signature},
            separators=(",", ":")
        ).encode("utf-8")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect((HOST_IP, PORT))
            s.sendall(message + b"\n")
            return True
    except Exception:
        return False

def listen_for_telemetry():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', TELEMETRY_PORT))
        s.listen()
        while True:
            try:
                conn, _ = s.accept()
                with conn:
                    data = conn.recv(1024).decode('utf-8').strip()
                    if data.startswith("CTX:"):
                        set_context_gauge(float(data.split(":")[1]))
                    elif data.startswith("TOK:"):
                        show_display(data.split(":")[1])
            except Exception:
                pass

def handle_button(btn_id: str, label: str, light):
    play_sound(1046, 0.03)
    light.on()
    show_display(label)
    success = send_button_press(btn_id)
    pulse_rainbow(success)
    if not success:
        show_display("ERR ")
    time.sleep(0.2)
    light.off()
    show_display(UI_LABELS.get("display", "CLAU"))

@rh.touch.A.press()
def handle_a(ch):
    handle_button("BTN_A", UI_LABELS.get("A_label", "Y   "), rh.lights.red)

@rh.touch.B.press()
def handle_b(ch):
    handle_button("BTN_B", UI_LABELS.get("B_label", "CMP "), rh.lights.green)

@rh.touch.C.press()
def handle_c(ch):
    handle_button("BTN_C", UI_LABELS.get("C_label", "STOP"), rh.lights.blue)

def cleanup(signum, frame):
    reset_hardware()
    sys.exit(0)

def main():
    if not re.fullmatch(r"[0-9a-fA-F]{64}", COMMAND_TOKEN):
        print(
            "[ERROR] Set CLAUDE_DECK_COMMAND_TOKEN to the same 64-character hex secret "
            "on the host and Pi."
        )
        sys.exit(1)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print("=" * 50)
    print(f"Pi Zero Deck | Active Profile: [{active_profile}]")
    print("=" * 50)

    show_display(UI_LABELS.get("display", "CLAU"))
    rh.lights.clear()
    rh.rainbow.clear()
    rh.rainbow.show()

    threading.Thread(target=listen_for_telemetry, daemon=True).start()
    signal.pause()

if __name__ == "__main__":
    main()