# 🌈 Pi Rainbow Deck

[![CI](https://github.com/hendu25/pi_rainbow_deck/actions/workflows/ci.yml/badge.svg)](https://github.com/hendu25/pi_rainbow_deck/actions/workflows/ci.yml)

A dedicated hardware macro pad and telemetry monitor for **Claude Code** sessions built with a **Raspberry Pi Zero** and a **Pimoroni Rainbow HAT**.

Pi Rainbow Deck connects to your host machine (Windows, macOS, or Linux) over **USB Gadget Mode** (Ethernet-over-USB) or Wi-Fi. It gives you physical touch buttons for rapid action approvals, audio feedback via the onboard piezo buzzer, and real-time session stats (token counts and context window fill gauges) parsed from live Claude Code logs. This is an independent community project and is not affiliated with or endorsed by Anthropic.

## 🚀 Getting started

### 1. Install uv

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) on the host:

```powershell
winget install --id astral-sh.uv -e
```

```sh
# macOS
brew install uv

# Linux (official installer)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Install and run the host bridge

Clone the repository on your host, open a terminal in the checkout, and install the host dependencies:

```sh
git clone https://github.com/hendu25/pi_rainbow_deck.git pi-rainbow-deck
cd pi-rainbow-deck
uv sync --extra host
```

On Linux, PyAutoGUI needs an X11 desktop session for keystroke injection. On Debian/Ubuntu, install its system packages before syncing:

```sh
sudo apt update
sudo apt install python3-tk python3-dev scrot
```

The Linux host must have an active X11 session; Wayland-only sessions are not supported for key injection.

### 3. Configure the network and shared secret

Choose a host interface reachable from the Pi. Set `networking.host_ip` in `src/pi_rainbow_deck_host/config.json` to the host's address, and set `networking.host_ip` in `src/pi_rainbow_deck_pi/config.json` to that same address. The sample `192.168.7.1` is for USB Ethernet gadget networking; it must be assigned to the host's USB Ethernet adapter, or replaced with the appropriate host address for Wi-Fi. On Windows, use `ipconfig` to find the adapter address. Keep the configured command port reachable from the Pi.

Generate a secret on the host:

```sh
python -c "import secrets; print(secrets.token_hex(32))"
```

Use `.env.example` as a reference for the required variable name, and set the generated value in the OS environment on **both** the host and Pi before launching their programs. The application reads environment variables directly; it does not load `.env` files. Do not commit your real secret or share it over an untrusted channel.

```powershell
# Windows PowerShell
$env:PI_RAINBOW_DECK_COMMAND_TOKEN = "<generated-secret>"
```

```sh
# macOS / Linux
export PI_RAINBOW_DECK_COMMAND_TOKEN="<generated-secret>"
```

Start the host bridge in that same terminal:

```sh
uv run pi-rainbow-deck-host
```

On Windows, the host uses PyAutoGUI. macOS uses `osascript` and may prompt you to grant Accessibility permission to the terminal or Python. Linux uses PyAutoGUI with X11.

### 4. Install and run on the Raspberry Pi Zero

Use Raspberry Pi OS with Python 3.9 or later, enable the Rainbow HAT/I²C support as required by the OS, and clone the same repository on the Pi:

```sh
git clone https://github.com/hendu25/pi_rainbow_deck.git pi-rainbow-deck
cd pi-rainbow-deck
```

If uv is available for the Pi's OS and CPU architecture, install the Pi runtime and HAT dependency:

```sh
uv sync --no-dev --extra pi
export PI_RAINBOW_DECK_COMMAND_TOKEN="<same-generated-secret>"
uv run --no-sync pi-rainbow-deck-pi
```

Some original Raspberry Pi Zero (ARMv6) images may not have a compatible uv binary. In that case, use Python's virtual environment and pip:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install '.[pi]'
export PI_RAINBOW_DECK_COMMAND_TOKEN="<same-generated-secret>"
pi-rainbow-deck-pi
```

For a persistent systemd service, configure its `ExecStart` to use the installed environment's `pi-rainbow-deck-pi` command, and set `PI_RAINBOW_DECK_COMMAND_TOKEN` with a private systemd override (for example, `sudo systemctl edit claude-deck.service`). Restrict access to the override and restart the service after updating it. The optional `deploy.sh` script syncs the Pi package to its configured target and restarts that existing service. The target directory and service name retain their historical `claude-deck` identifiers for compatibility with existing Pi installs.

### 5. Run tests (optional)

On a development machine, install the host and test dependencies and run the hardware-free tests:

```sh
uv sync --group dev --extra host
uv run pytest
uv run pre-commit install
uv run pre-commit run --all-files
```

For one command that runs tests, Ruff, and pre-commit checks, use:

```sh
uv run python scripts/check.py
```

GitHub Actions runs these checks for pull requests targeting `main` or `master`.
The suite includes a hardware-free integration test that presses a virtual
button, sends its authenticated command over localhost, and verifies the host's
dry-run action mapping.

### Try the host and Pi apps without a Rainbow HAT

The Pi app includes a console-based virtual HAT for local integration testing.
It sends the same authenticated button commands as the physical HAT. The host
dry-run mode logs mapped actions instead of injecting keystrokes into the
currently focused application.

1. Open a terminal for the host app, set the same 64-character test token
   required by both apps, and enable local test mode:

   ```powershell
   $env:PI_RAINBOW_DECK_COMMAND_TOKEN = "<64-character-test-secret>"
   $env:PI_RAINBOW_DECK_LOCAL_TEST = "1"
   uv run --extra host pi-rainbow-deck-host
   ```

2. In a second terminal, set the same token and local test flag, then start
   the virtual HAT:

   ```powershell
   $env:PI_RAINBOW_DECK_COMMAND_TOKEN = "<64-character-test-secret>"
   $env:PI_RAINBOW_DECK_LOCAL_TEST = "1"
   uv run pi-rainbow-deck-pi
   ```

3. Enter `A`, `B`, or `C` in the Pi terminal. The virtual HAT displays feedback,
   and the host terminal logs the mapped action without pressing keys. Enter
   `Q` to send an authenticated shutdown request to the host and exit the
   virtual HAT. You can also stop the host locally with `Ctrl+C` in its terminal.

This local setup uses the configured ports, so stop any other app instances
using those ports first. The single `PI_RAINBOW_DECK_LOCAL_TEST` flag routes
both apps over loopback, enables the console HAT, and prevents real keystrokes.
When unset, both apps use the network addresses and physical HAT configured as
before.

Add `--build` to also build the source distribution and wheel:

```sh
uv run python scripts/check.py --build
```

The tests use localhost sockets and stub Rainbow HAT, so they require neither a Pi nor physical hardware or real keystroke injection. Pre-commit runs Ruff linting/formatting and standard YAML/TOML, whitespace, merge-conflict, and large-file checks.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the fork, branch, and pull request workflow.

## 🔐 Secure the command connection

The host bridge accepts authenticated commands that inject keystrokes into the active application. It requires a valid shared secret, verifies command signatures and timestamps, and rejects replayed commands. The bridge binds only to the address configured as `networking.host_ip` in `src/pi_rainbow_deck_host/config.json`.

## License

This project is licensed under the GNU General Public License, version 3 or (at your option) any later version. See [LICENSE](LICENSE) for the complete license text.

See [CHANGELOG.md](CHANGELOG.md) for release notes.

---

## 📁 Repository Structure

```text
pi-rainbow-deck/
├── README.MD                 # Project documentation
├── CHANGELOG.md              # Release history
├── CONTRIBUTING.md           # Contributor setup and pull request guide
├── deploy.sh                 # One-click deployment script (rsync to Pi Zero)
├── LICENSE                   # GPL-3.0-or-later
├── pyproject.toml            # Project metadata and dependency groups
├── uv.lock                   # Reproducible uv dependency lockfile
├── src/
│   ├── pi_rainbow_deck_host/ # Host Machine Service (Windows / macOS / Linux)
│   │   ├── config.json       # Profile & network settings
│   │   ├── keystrokes.py     # Cross-platform OS key injection
│   │   ├── log_monitor.py    # Real-time ~/.claude/ log parser
│   │   └── bridge.py         # Main socket server & entry point
│   └── pi_rainbow_deck_pi/   # Pi Zero Daemon Service
│       ├── config.json       # UI & network settings
│       ├── hat_hardware.py   # Hardware abstraction (Buzzer, LEDs, Display)
│       └── main.py           # Touch button event loop & telemetry subscriber
└── tests/                    # Hardware-free pytest suite
