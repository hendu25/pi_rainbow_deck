# Contributing to Pi Rainbow Deck

Thanks for considering a contribution! Bug reports, documentation improvements,
tests, and code changes are all welcome.

## Before opening an issue

- Search existing issues and pull requests to avoid duplicates.
- Include your operating system, Python version, Pi model (if relevant), and
  Rainbow HAT details.
- Never include your `CLAUDE_DECK_COMMAND_TOKEN`, credentials, or private Claude
  Code transcripts in an issue.
- For a suspected security vulnerability, do not open a public issue. Follow the
  private reporting instructions in GitHub's Security tab if private
  vulnerability reporting is enabled; otherwise contact the repository
  maintainers privately.

## Development setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), clone
your fork, and install the development and host dependencies:

```sh
git clone https://github.com/<your-user>/pi_rainbow_deck.git
cd pi_rainbow_deck
uv sync --group dev --extra host
uv run pre-commit install
```

On Linux, PyAutoGUI needs an X11 session and its system packages. On Debian or
Ubuntu, install them with:

```sh
sudo apt update
sudo apt install python3-tk python3-dev scrot
```

Tests stub the Rainbow HAT and do not inject real keystrokes, so routine
development and CI do not require physical hardware.

## Branch and pull request workflow

1. Fork the repository on GitHub, then clone your fork:

   ```sh
   git clone https://github.com/<your-user>/pi_rainbow_deck.git
   cd pi_rainbow_deck
   ```

2. Create a short-lived branch in your fork based on the repository's default
   branch. Use a descriptive prefix, such as `fix/telemetry-reconnect`,
   `feat/context-profile`, or `docs/pi-setup`.

   ```sh
   git switch -c fix/telemetry-reconnect
   ```

3. Make focused changes and add or update tests and documentation where
   appropriate.
4. Run the project checks before pushing:

   ```sh
   uv run python scripts/check.py
   ```

   To include a package build:

   ```sh
   uv run python scripts/check.py --build
   ```

5. Push your branch to your fork and open a pull request against the repository's
   default branch:

   ```sh
   git push --set-upstream origin fix/telemetry-reconnect
   ```

   The GitHub Actions checks must pass before merge.
6. In the pull request description, explain the motivation, summarize behavior
   changes, link related issues, and note any manual testing that requires Pi
   hardware. Include screenshots or logs only after checking that they contain
   no secrets or private transcript data.

Keep pull requests narrowly scoped. Avoid committing generated build output,
virtual environments, credentials, or unrelated formatting changes.

## Project conventions

- Keep host and Pi runtime dependencies in their corresponding optional extras
  in `pyproject.toml`; keep development tools in the `dev` dependency group.
- Preserve hardware-free testability by stubbing Rainbow HAT and OS key
  injection in tests.
- Document configuration, security implications, and setup changes in the
  README.
- The project is licensed under GPL-3.0-or-later. By submitting a contribution,
  you agree that it may be distributed under that license.
