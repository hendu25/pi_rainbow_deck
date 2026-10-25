# Changelog

Notable changes to Pi Rainbow Deck are documented here.

## [0.0.1] - Unreleased

Initial public release.

### Added

- Raspberry Pi Zero and Pimoroni Rainbow HAT button pad for Claude Code actions,
  with host-side keystroke injection and session telemetry display.
- Host bridge and Pi daemon with configurable SAFETY, CONTEXT, and AGENTS
  profiles.
- HMAC-authenticated, timestamped button commands with replay protection.
- Windows, macOS, and Linux host support. Linux key injection requires an X11
  desktop session.
- `uv`-managed Python project, CLI commands, and Pi deployment script.
- Hardware-free tests, Ruff linting and formatting, pre-commit hooks, and
  cross-platform GitHub Actions CI.
- Setup, security, and contribution documentation.
- GPL-3.0-or-later licensing.

### Validation note

Automated tests and package builds pass in CI. Physical Raspberry Pi Zero and
Rainbow HAT operation has not yet been confirmed as part of this release
preparation; verify it on the target hardware before publishing the release.
