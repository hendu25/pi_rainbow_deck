import hmac
import json
import os
import re
import socket
import sys
import threading
import time

if __package__:
    from .keystrokes import execute_action
    from .log_monitor import start_log_monitor
else:
    from keystrokes import execute_action
    from log_monitor import start_log_monitor

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
MAX_COMMAND_BYTES = 4096
COMMAND_TIMESTAMP_WINDOW = 30


def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"[ERROR] Missing config file: {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_command(data, token, used_nonces):
    try:
        message = json.loads(data.decode("utf-8"))
        payload = message["payload"]
        signature = message["signature"]
        if set(payload) != {"button_id", "timestamp", "nonce"}:
            return None
        button_id = payload["button_id"]
        timestamp = payload["timestamp"]
        nonce = payload["nonce"]
        if not isinstance(button_id, str):
            return None
        if isinstance(timestamp, bool) or not isinstance(timestamp, int):
            return None
        if not isinstance(nonce, str) or not re.fullmatch(r"[0-9a-f]{32}", nonce):
            return None
        if not isinstance(signature, str):
            return None

        now = int(time.time())
        if abs(now - timestamp) > COMMAND_TIMESTAMP_WINDOW:
            return None

        canonical_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        expected_signature = hmac.new(
            token.encode("utf-8"), canonical_payload.encode("utf-8"), "sha256"
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            return None

        for old_nonce, old_timestamp in list(used_nonces.items()):
            if now - old_timestamp > COMMAND_TIMESTAMP_WINDOW:
                del used_nonces[old_nonce]
        if nonce in used_nonces:
            return None
        used_nonces[nonce] = timestamp
        return button_id
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
        return None


def receive_command(conn):
    conn.settimeout(2.0)
    data = bytearray()
    while len(data) <= MAX_COMMAND_BYTES:
        chunk = conn.recv(min(1024, MAX_COMMAND_BYTES + 1 - len(data)))
        if not chunk:
            return None
        newline = chunk.find(b"\n")
        if newline >= 0:
            data.extend(chunk[:newline])
            return bytes(data)
        data.extend(chunk)
    raise ValueError("Command message exceeds maximum size")


def main():
    config = load_config()
    active_profile = config.get("active_profile", "SAFETY")
    networking = config.get("networking", {})
    claude_cfg = config.get("claude", {})

    host_actions = config.get("profiles", {}).get(active_profile, {})
    host_ip = networking.get("host_ip", "192.168.7.1")
    port = networking.get("command_port", 5000)
    pi_ip = networking.get("pi_ip", "192.168.7.2")
    telemetry_port = networking.get("telemetry_port", 5001)
    context_limit = claude_cfg.get("context_window_limit", 200000)
    command_token = os.environ.get("PI_RAINBOW_DECK_COMMAND_TOKEN", "")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", command_token):
        raise RuntimeError(
            "Set PI_RAINBOW_DECK_COMMAND_TOKEN to the same 64-character hex secret on the host and Pi."
        )

    print("=" * 60)
    print(f"Claude Host Bridge [{sys.platform.upper()}] | Profile: [{active_profile}]")
    print(f"Keybindings: {host_actions}")
    print(f"Listening on {host_ip}:{port}...")
    print("=" * 60)

    # Start background log monitor
    threading.Thread(
        target=start_log_monitor,
        args=(pi_ip, telemetry_port, context_limit),
        daemon=True,
    ).start()

    # Main Command Socket Listener
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host_ip, port))
        s.listen()
        used_nonces = {}

        while True:
            try:
                conn, _ = s.accept()
                with conn:
                    data = receive_command(conn)
                    if data:
                        btn_id = validate_command(data, command_token, used_nonces)
                        if btn_id is None:
                            print(
                                "[WARNING] Rejected unauthenticated or replayed command"
                            )
                        else:
                            action_id = host_actions.get(btn_id)
                            if action_id:
                                execute_action(action_id)
                            else:
                                print(f"[WARNING] Unmapped button ID: {btn_id}")
            except KeyboardInterrupt:
                print("\nStopping bridge server.")
                break
            except (OSError, ValueError) as e:
                print(f"[WARNING] Rejected command connection: {e}")
            except Exception as e:
                print(f"[ERROR]: {e}")


if __name__ == "__main__":
    main()
