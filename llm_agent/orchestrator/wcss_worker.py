"""Worker obserwujący katalog backendu WCSS i uruchamiający orkiestrator."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .config import Settings
from .callback import notify_backend
from .wcss_request import process_request


def _ready(request_dir: Path) -> bool:
    return (
        (request_dir / "input" / "audio_folder" / "audio.wav").is_file()
        and any((request_dir / "input" / "prompt_folder").glob("*.json"))
        and not any((request_dir / "output" / "agent_response").glob("response_*.json"))
    )


def _claim(request_dir: Path) -> int | None:
    lock = request_dir / ".soundcraft-processing.lock"
    try:
        return os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return None


def _write_unhandled_failure(request_dir: Path, exc: Exception) -> dict[str, object]:
    output = request_dir / "output" / "agent_response"
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    payload = {
        "execution_code": "FAILED",
        "status": "FAILED",
        "error_code": "WORKER_ERROR",
        "error_message": f"Worker WCSS: {exc}"[:600],
        "output_path": None,
    }
    target = output / f"response_{stamp}.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


async def run_worker(root: Path, settings: Settings, once: bool, poll_s: float) -> None:
    root.mkdir(parents=True, exist_ok=True)
    while True:
        for request_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            if not _ready(request_dir):
                continue
            descriptor = _claim(request_dir)
            if descriptor is None:
                continue
            lock = request_dir / ".soundcraft-processing.lock"
            try:
                os.write(descriptor, f"pid={os.getpid()}\n".encode())
                os.close(descriptor)
                payload = await process_request(request_dir, settings)
            except Exception as exc:  # noqa: BLE001
                payload = _write_unhandled_failure(request_dir, exc)
            try:
                await notify_backend(request_dir.name, payload, settings)
            except Exception as exc:  # callback nigdy nie może zatrzymać workera
                print(f"Callback requestu {request_dir.name} nie powiódł się: {exc}", flush=True)
            finally:
                lock.unlink(missing_ok=True)
        if once:
            return
        await asyncio.sleep(poll_s)


def cli() -> None:
    parser = argparse.ArgumentParser(description="SoundCraft WCSS request worker")
    parser.add_argument("--root", default=None, help="nadpisuje paths.request_root z config.yaml")
    parser.add_argument("--config", default=None)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll", type=float, default=3.0)
    args = parser.parse_args()
    settings = Settings.load(args.config)
    errors = settings.validate()
    if errors:
        parser.error("; ".join(errors))
    root = args.root or settings.request_root
    if not root:
        parser.error("podaj --root albo ustaw paths.request_root w config.yaml")
    asyncio.run(run_worker(Path(root), settings, args.once, args.poll))


if __name__ == "__main__":
    cli()
