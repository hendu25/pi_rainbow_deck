# 🌈 Claude Deck

A dedicated hardware macro pad and telemetry monitor for **Claude Code** sessions built with a **Raspberry Pi Zero** and a **Pimoroni Rainbow HAT**.

Claude Deck connects to your host machine (macOS or Windows) over **USB Gadget Mode** (Ethernet-over-USB) or Wi-Fi. It gives you physical touch buttons for rapid action approvals, audio feedback via the onboard piezo buzzer, and real-time session stats (token counts and context window fill gauges) parsed from live Claude Code logs.

## 🔐 Secure the command connection

The host bridge accepts commands that inject keystrokes into the active application. Before starting the bridge or Pi daemon, configure the same randomly generated 64-character hexadecimal secret in the `CLAUDE_DECK_COMMAND_TOKEN` environment variable on both machines. Do not commit or share this secret over an untrusted channel.

Generate the token on the host with:

```sh
python -c "import secrets; print(secrets.token_hex(32))"
```

Set it in the shell used to run the host bridge:

```powershell
$env:CLAUDE_DECK_COMMAND_TOKEN = "<generated-secret>"
```

On macOS or Linux, use `export CLAUDE_DECK_COMMAND_TOKEN="<generated-secret>"`.

For a Pi daemon managed by systemd, add `Environment=CLAUDE_DECK_COMMAND_TOKEN=<generated-secret>` to a systemd service override (for example, `sudo systemctl edit claude-deck.service`), then restart the service. Keep the override private and restrict access to it. The host bridge binds only to the address configured as `networking.host_ip` in `src/claude_deck_host/config.json`; ensure that address belongs to the host's USB or Wi-Fi interface.

Commands are authenticated, time-limited, and protected against replay. The bridge will not start without a valid secret, and the Pi will show an error if its secret is missing or invalid.

## 🧪 Development and tests

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run `uv sync --group dev --extra host` to create the development environment and install the host and test dependencies. Run the hardware-free security tests with `uv run pytest`; they use localhost sockets and stub Rainbow HAT, so they do not need a Raspberry Pi, physical HAT, or real keystroke injection.

The source packages use the standard `src/` layout. Run the host bridge with `uv run claude-deck-host`. On a Raspberry Pi checkout, install only the Pi runtime dependencies with `uv sync --no-dev --extra pi`, then run the daemon with `uv run claude-deck-pi`. The deployment script syncs `src/claude_deck_pi/` to the existing Pi target directory.

---

## 📁 Repository Structure

```text
claude-deck/
├── README.MD                 # Project documentation
├── deploy.sh                 # One-click deployment script (rsync to Pi Zero)
├── pyproject.toml            # Project metadata and dependency groups
├── uv.lock                   # Reproducible uv dependency lockfile
├── src/
│   ├── claude_deck_host/     # Host Machine Service (Mac / Windows)
│   │   ├── config.json       # Profile & network settings
│   │   ├── keystrokes.py     # Cross-platform OS key injection
│   │   ├── log_monitor.py    # Real-time ~/.claude/ log parser
│   │   └── bridge.py         # Main socket server & entry point
│   └── claude_deck_pi/       # Pi Zero Daemon Service
│       ├── config.json       # UI & network settings
│       ├── hat_hardware.py   # Hardware abstraction (Buzzer, LEDs, Display)
│       └── main.py           # Touch button event loop & telemetry subscriber
└── tests/                    # Hardware-free pytest suite