# 🌈 Claude Deck

A dedicated hardware macro pad and telemetry monitor for **Claude Code** sessions built with a **Raspberry Pi Zero** and a **Pimoroni Rainbow HAT**.

Claude Deck connects to your host machine (macOS or Windows) over **USB Gadget Mode** (Ethernet-over-USB) or Wi-Fi. It gives you physical touch buttons for rapid action approvals, audio feedback via the onboard piezo buzzer, and real-time session stats (token counts and context window fill gauges) parsed from live Claude Code logs.

---

## 📁 Repository Structure

```text
claude-deck/
├── README.md               # Project documentation
├── deploy.sh               # One-click deployment script (rsync to Pi Zero)
├── claude-deck-host/       # Host Machine Service (Mac / Windows)
│   ├── config.json         # Profile & network settings
│   ├── keystrokes.py       # Cross-platform OS key injection
│   ├── log_monitor.py      # Real-time ~/.claude/ log parser
│   └── bridge.py           # Main socket server & entry point
└── claude-deck-pi/         # Pi Zero Daemon Service
    ├── config.json         # UI & network settings
    ├── hat_hardware.py     # Hardware abstraction (Buzzer, LEDs, Display)
    └── main.py             # Touch button event loop & telemetry subscriber