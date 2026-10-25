import errno
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
QUIT_COMMAND_ID = "QUIT"


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


def handle_command(data, command_token, used_nonces, host_actions, dry_run=False):
    button_id = validate_command(data, command_token, used_nonces)
    if button_id is None:
        print("[WARNING] Rejected unauthenticated or replayed command")
        return False

    if button_id == QUIT_COMMAND_ID:
        print("[INFO] Authenticated host shutdown requested")
        return True

    action_id = host_actions.get(button_id)
    if not action_id:
        print(f"[WARNING] Unmapped button ID: {button_id}")
        return False

    if dry_run:
        print(f"[DRY RUN] Would execute action: {action_id}")
    else:
        execute_action(action_id)
    return False


def main():
    config = load_config()
    active_profile = config.get("active_profile", "SAFETY")
    networking = config.get("networking", {})
    claude_cfg = config.get("claude", {})
    local_test_mode = os.environ.get("PI_RAINBOW_DECK_LOCAL_TEST") == "1"

    host_actions = config.get("profiles", {}).get(active_profile, {})
    host_ip = (
        "127.0.0.1" if local_test_mode else networking.get("host_ip", "192.168.7.1")
    )
    port = networking.get("command_port", 5000)
    pi_ip = "127.0.0.1" if local_test_mode else networking.get("pi_ip", "192.168.7.2")
    telemetry_port = networking.get("telemetry_port", 5001)
    context_limit = claude_cfg.get("context_window_limit", 200000)
    command_token = os.environ.get("PI_RAINBOW_DECK_COMMAND_TOKEN", "")
    dry_run = local_test_mode
    if not re.fullmatch(r"[0-9a-fA-F]{64}", command_token):
        raise RuntimeError(
            "Set PI_RAINBOW_DECK_COMMAND_TOKEN to the same 64-character hex secret on the host and Pi."
        )

    print("=" * 60)
    print(f"Claude Host Bridge [{sys.platform.upper()}] | Profile: [{active_profile}]")
    if dry_run:
        print(
            "Dry-run enabled: mapped actions will be logged without injecting keystrokes."
        )
    print(f"Keybindings: {host_actions}")
    print("=" * 60)

    # Main Command Socket Listener
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host_ip, port))
            s.listen()
        except OSError as exc:
            if (
                getattr(exc, "winerror", None) == 10049
                or exc.errno == errno.EADDRNOTAVAIL
            ):
                print(
                    f"[ERROR] Host IP {host_ip} is not assigned to this computer. "
                    "Connect/configure the network adapter for the Pi, or set "
                    "networking.host_ip in src/pi_rainbow_deck_host/config.json "
                    "to this computer's reachable IPv4 address (check `ipconfig`)."
                )
            else:
                print(
                    f"[ERROR] Could not listen on {host_ip}:{port}: {exc}. "
                    "Check the configured host IP and port."
                )
            raise SystemExit(1) from None

        print(f"Listening on {host_ip}:{port}...")

        # Start background log monitor only after the command listener is ready.
        threading.Thread(
            target=start_log_monitor,
            args=(pi_ip, telemetry_port, context_limit),
            daemon=True,
        ).start()

        used_nonces = {}

        while True:
            try:
                conn, _ = s.accept()
                with conn:
                    data = receive_command(conn)
                if data and handle_command(
                    data, command_token, used_nonces, host_actions, dry_run
                ):
                    print("\nStopping bridge server.")
                    break
            except KeyboardInterrupt:
                print("\nStopping bridge server.")
                break
            except (OSError, ValueError) as e:
                print(f"[WARNING] Rejected command connection: {e}")
            except Exception as e:
                print(f"[ERROR]: {e}")


if __name__ == "__main__":
    main()
