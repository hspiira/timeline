#!/usr/bin/env python3
"""Run the API and the web client together.

One Ctrl-C stops both. If either exits on its own, the other is stopped too, so
you never end up with half a stack running and a port still held.

Works before and after the monorepo move: the web client is looked for under
apps/web first, then at the sibling timeline-ui checkout.

    uv run python -m scripts.dev          # or: make dev
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent
WEB_CANDIDATES = (
    API_DIR / "apps" / "web",          # after the monorepo move
    API_DIR.parent / "timeline-ui",    # separate checkouts, today
)

# Ports are overridable so a second stack can run beside one already up.
API_PORT = os.environ.get("API_PORT", "8000")
WEB_PORT = os.environ.get("WEB_PORT")

API_CMD = ["uv", "run", "uvicorn", "app.main:app", "--reload", "--port", API_PORT]
# The package's dev script already fixes a port, so appending another would pass
# --port twice. Override by calling vite directly instead.
WEB_CMD = (
    ["pnpm", "exec", "vite", "dev", "--port", WEB_PORT] if WEB_PORT else ["pnpm", "dev"]
)

COLOURS = {"api": "\033[36m", "web": "\033[35m"}
RESET = "\033[0m"

Process = subprocess.Popen[str]


def find_web_dir() -> Path | None:
    """Return the web client directory, or None if neither location has one."""
    return next((c for c in WEB_CANDIDATES if (c / "package.json").is_file()), None)


def stream(name: str, process: Process) -> None:
    """Print one process's output, each line tagged with its source."""
    colour = COLOURS.get(name, "")
    assert process.stdout is not None
    for line in process.stdout:
        sys.stdout.write(f"{colour}{name:>3}{RESET} │ {line}")
        sys.stdout.flush()


def start(name: str, cmd: list[str], cwd: Path) -> Process:
    """Launch one process in its own session so its whole tree can be signalled."""
    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        # Own process group: uvicorn --reload and vite both spawn children, and
        # killing just the parent leaves those holding the port.
        start_new_session=True,
    )
    threading.Thread(target=stream, args=(name, process), daemon=True).start()
    return process


def signal_group(process: Process, sig: int) -> None:
    """Send a signal to a process's whole group, ignoring one already gone."""
    try:
        os.killpg(os.getpgid(process.pid), sig)
    except (ProcessLookupError, PermissionError):
        pass


def stop(processes: dict[str, Process]) -> None:
    """Ask both to stop, then force whatever is still alive."""
    running = [p for p in processes.values() if p.poll() is None]
    for process in running:
        signal_group(process, signal.SIGTERM)
    for process in running:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            signal_group(process, signal.SIGKILL)


def wait_for_first_exit(processes: dict[str, Process]) -> tuple[str, int]:
    """Block until one process exits; return its name and exit code."""
    while True:
        for name, process in processes.items():
            code = process.poll()
            if code is not None:
                return name, code
        time.sleep(0.2)


def main() -> int:
    """Start both, then stop both as soon as either one ends."""
    web_dir = find_web_dir()
    if web_dir is None:
        looked = "\n  ".join(str(c) for c in WEB_CANDIDATES)
        print(f"No web client found. Looked for a package.json in:\n  {looked}")
        return 1

    print(f"api │ {API_DIR}  :{API_PORT}")
    print(f"web │ {web_dir}  :{WEB_PORT or 'default'}")
    print("Ctrl-C stops both.\n")

    processes: dict[str, Process] = {}

    def on_signal(signum: int, _frame: object) -> None:
        """Turn a termination signal into the same unwinding a Ctrl-C gets.

        Handling only KeyboardInterrupt is not enough. A SIGTERM, or a SIGINT that
        the shell set to SIG_IGN because this was started as a background job,
        would otherwise leave uvicorn and vite holding their ports.
        """
        raise KeyboardInterrupt(signum)

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    try:
        processes["api"] = start("api", API_CMD, API_DIR)
        processes["web"] = start("web", WEB_CMD, web_dir)
        name, code = wait_for_first_exit(processes)
        print(f"\n{name} exited with code {code}; stopping the other.")
        return code
    except FileNotFoundError as exc:
        print(f"\nCould not start: {exc.filename} is not installed or not on PATH.")
        return 1
    except KeyboardInterrupt:
        print("\nStopping.")
        return 0
    finally:
        stop(processes)


if __name__ == "__main__":
    raise SystemExit(main())
