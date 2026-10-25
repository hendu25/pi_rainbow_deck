import glob
import json
import os
import socket
import time


def get_latest_claude_log():
    """Finds the most recently modified Claude Code transcript log file."""
    claude_dir = os.path.expanduser("~/.claude")
    if not os.path.exists(claude_dir):
        return None
    log_files = glob.glob(os.path.join(claude_dir, "**", "*.jsonl"), recursive=True)
    return max(log_files, key=os.path.getmtime) if log_files else None


def send_telemetry(message: str, pi_ip: str, port: int):
    """Pushes a telemetry string to the Pi Zero."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            s.connect((pi_ip, port))
            s.sendall(message.encode("utf-8"))
    except Exception:
        pass  # Fails silently if Pi is unreachable


def start_log_monitor(pi_ip: str, telemetry_port: int, context_limit: int):
    """Tails active Claude Code JSONL logs and streams usage updates to Pi."""
    current_file, file_handle, last_tokens = None, None, -1
    print("[LOG MONITOR] Watching ~/.claude/ for live session stats...")

    while True:
        try:
            latest = get_latest_claude_log()
            if latest and latest != current_file:
                if file_handle:
                    file_handle.close()
                current_file = latest
                file_handle = open(current_file, "r", encoding="utf-8")
                file_handle.seek(0, os.SEEK_END)
                last_tokens = -1

            if file_handle:
                for line in file_handle.readlines():
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        usage = entry.get("usage") or entry.get("message", {}).get(
                            "usage"
                        )
                        if usage:
                            total = sum(
                                [
                                    usage.get("input_tokens", 0),
                                    usage.get("cache_read_input_tokens", 0),
                                    usage.get("cache_creation_input_tokens", 0),
                                    usage.get("output_tokens", 0),
                                ]
                            )
                            if total != last_tokens and total > 0:
                                last_tokens = total
                                ctx_pct = (total / context_limit) * 100.0
                                send_telemetry(
                                    f"CTX:{ctx_pct:.1f}", pi_ip, telemetry_port
                                )

                                tok_str = (
                                    f"{int(total / 1000)}K"
                                    if total >= 1000
                                    else str(total)
                                )
                                send_telemetry(
                                    f"TOK:{tok_str:<4}", pi_ip, telemetry_port
                                )
                    except json.JSONDecodeError:
                        continue
            time.sleep(1.0)
        except Exception:
            time.sleep(2.0)
