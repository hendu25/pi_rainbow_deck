import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(
        description="Run Pi Rainbow Deck tests and quality checks."
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="also build the source distribution and wheel",
    )
    args = parser.parse_args()

    if shutil.which("uv") is None:
        print("Error: uv is required. Install it from https://docs.astral.sh/uv/")
        return 1

    commands = [
        ("Tests", ["uv", "run", "--group", "dev", "--extra", "host", "pytest", "-q"]),
        (
            "Ruff lint",
            ["uv", "run", "--group", "dev", "ruff", "check", "src", "tests", "scripts"],
        ),
        (
            "Ruff format",
            [
                "uv",
                "run",
                "--group",
                "dev",
                "ruff",
                "format",
                "--check",
                "src",
                "tests",
                "scripts",
            ],
        ),
        (
            "Pre-commit",
            ["uv", "run", "--group", "dev", "pre-commit", "run", "--all-files"],
        ),
    ]
    if args.build:
        commands.append(("Package build", ["uv", "build"]))

    for name, command in commands:
        print(f"\n==> {name}", flush=True)
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            print(f"\nFailed: {name} (exit code {result.returncode})", file=sys.stderr)
            return result.returncode

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
