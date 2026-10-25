import os
import sys
import json
import socket
import threading

from keystrokes import execute_action
from log_monitor import start_log_monitor

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"[ERROR] Missing config file: {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    config = load_config()
    active_profile = config.get("active_profile", "SAFETY")
    networking = config.get("networking", {})
    claude_cfg = config.get("claude", {})

    host_actions = config.get("profiles", {}).get(active_profile, {})
    port = networking.get("command_port", 5000)
    pi_ip = networking.get("pi_ip", "192.168.7.2")
    telemetry_port = networking.get("telemetry_port", 5001)
    context_limit = claude_cfg.get("context_window_limit", 200000)

    print("=" * 60)
    print(f"Claude Host Bridge [{sys.platform.upper()}] | Profile: [{active_profile}]")
    print(f"Keybindings: {host_actions}")
    print(f"Listening on port {port}...")
    print("=" * 60)

    # Start background log monitor
    threading.Thread(
        target=start_log_monitor,
        args=(pi_ip, telemetry_port, context_limit),
        daemon=True
    ).start()

    # Main Command Socket Listener
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', port))
        s.listen()

        while True:
            try:
                conn, _ = s.accept()
                with conn:
                    data = conn.recv(1024)
                    if data:
                        btn_id = data.decode('utf-8').strip()
                        action_id = host_actions.get(btn_id)
                        if action_id:
                            execute_action(action_id)
                        else:
                            print(f"[WARNING] Unmapped button ID: {btn_id}")
            except KeyboardInterrupt:
                print("\nStopping bridge server.")
                break
            except Exception as e:
                print(f"[ERROR]: {e}")

if __name__ == "__main__":
    main()