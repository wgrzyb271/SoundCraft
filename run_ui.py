#!/usr/bin/env python3
"""Start SoundCraft backend and frontend together."""
from __future__ import annotations

import argparse
import errno
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _require(command: str) -> None:
    if shutil.which(command) is None:
        raise SystemExit(f"Missing command: {command}")


def _signal_process(process: subprocess.Popen, sig: signal.Signals) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, sig)
        elif sig == signal.SIGTERM:
            process.terminate()
        else:
            process.kill()
    except ProcessLookupError:
        pass


def _stop(processes: list[subprocess.Popen]) -> None:
    for process in processes:
        _signal_process(process, signal.SIGTERM)
    deadline = time.monotonic() + 5
    for process in processes:
        if process.poll() is None:
            try:
                process.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                _signal_process(process, signal.SIGKILL)


def _require_free_port(host: str, port: int, option: str) -> None:
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SystemExit(f"Invalid host {host!r}: {exc}") from exc

    family, socktype, proto, _, address = addresses[0]
    with socket.socket(family, socktype, proto) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(address)
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE:
                raise SystemExit(
                    f"Cannot bind to {host}:{port}: {exc.strerror or exc}."
                ) from exc
            raise SystemExit(
                f"Port {host}:{port} is already in use. Stop the previous SoundCraft "
                f"process or select another port with {option}."
            ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Start SoundCraft frontend and backend")
    parser.add_argument("--demo", action="store_true", help="local pipeline without WCSS or GPU")
    parser.add_argument("--config", type=Path, default=ROOT / "llm_agent" / "config.local.yaml")
    parser.add_argument("--backend-host", default="127.0.0.1")
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--frontend-host", default="127.0.0.1")
    parser.add_argument("--frontend-port", type=int, default=5173)
    args = parser.parse_args()

    _require("npm")
    if not args.demo and not args.config.is_file():
        parser.error(f"configuration does not exist: {args.config}")
    _require_free_port(args.backend_host, args.backend_port, "--backend-port")
    _require_free_port(args.frontend_host, args.frontend_port, "--frontend-port")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["VITE_API_URL"] = f"http://{args.backend_host}:{args.backend_port}"
    env["SOUNDCRAFT_FRONTEND_ORIGINS"] = ",".join((
        f"http://localhost:{args.frontend_port}",
        f"http://127.0.0.1:{args.frontend_port}",
    ))
    if args.demo:
        env["SOUNDCRAFT_DEMO"] = "1"
        env.pop("SOUNDCRAFT_CONFIG", None)
    else:
        env["SOUNDCRAFT_CONFIG"] = str(args.config.resolve())

    backend = [
        sys.executable, "-m", "uvicorn", "app.main:app",
        "--host", args.backend_host, "--port", str(args.backend_port),
    ]
    frontend = [
        "npm", "run", "dev", "--", "--host", args.frontend_host,
        "--port", str(args.frontend_port), "--strictPort",
    ]
    processes: list[subprocess.Popen] = []

    def shutdown(_signum=None, _frame=None):
        _stop(processes)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    try:
        process_options = {"env": env, "start_new_session": os.name == "posix"}
        processes.append(subprocess.Popen(backend, cwd=ROOT / "SoundCraft_backend", **process_options))
        processes.append(subprocess.Popen(frontend, cwd=ROOT / "SoundCraft_frontend", **process_options))
        mode = "DEMO (local, no GPU)" if args.demo else f"WCSS ({args.config})"
        print(f"SoundCraft mode: {mode}", flush=True)
        print(f"UI: http://{args.frontend_host}:{args.frontend_port}", flush=True)
        print(f"API: http://{args.backend_host}:{args.backend_port}", flush=True)
        print("Press Ctrl+C to stop both processes.", flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        failed = next((process.returncode for process in processes if process.poll() is not None), 1)
        raise SystemExit(failed or 0)
    finally:
        _stop(processes)


if __name__ == "__main__":
    main()
