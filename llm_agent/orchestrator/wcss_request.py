"""Uruchomienie całego pipeline'u dla katalogu żądania znajdującego się już na WCSS."""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import Settings
from .deploy import DeployError
from .main import run_orchestrator
from .mcp_session import NullMcpSession
from .wcss_agents import build_wcss_agents


def _load_request(request_dir: Path) -> tuple[str, Path]:
    audio_path = request_dir / "input" / "audio_folder" / "audio.wav"
    metadata_files = sorted((request_dir / "input" / "prompt_folder").glob("*.json"))
    if not audio_path.is_file():
        raise FileNotFoundError(f"brak audio: {audio_path}")
    if not metadata_files:
        raise FileNotFoundError(f"brak metadanych promptu w {request_dir / 'input' / 'prompt_folder'}")
    data: Any = json.loads(metadata_files[-1].read_text(encoding="utf-8"))
    prompt = data.get("prompt") if isinstance(data, dict) else None
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("metadane nie zawierają niepustego pola 'prompt'")
    return prompt, audio_path


def _request_session(request_dir: Path) -> NullMcpSession:
    async def deploy(_username: str, temp_audio_path: str, _prompt: str) -> str:
        if Path(temp_audio_path).resolve() != (request_dir / "input" / "audio_folder" / "audio.wav").resolve():
            raise DeployError("BAD_PATH", "audio nie należy do wskazanego katalogu żądania")
        return str(request_dir)

    return NullMcpSession(deploy=deploy)


async def process_request(request_dir: str | Path, settings: Settings | None = None) -> dict[str, Any]:
    root = Path(request_dir).resolve()
    prompt, audio_path = _load_request(root)
    summary = await run_orchestrator(
        username=root.name,
        temp_audio_path=str(audio_path),
        prompt_text=prompt,
        agents=build_wcss_agents(),
        settings=settings,
        mcp_factory=lambda: _request_session(root),
        show=False,
    )
    payload = summary.model_dump(mode="json")
    response_dir = root / "output" / "agent_response"
    response_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    target = response_dir / f"response_{stamp}.json"
    temporary = response_dir / f".{target.name}.tmp"
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(target)
    return payload


def cli() -> None:
    parser = argparse.ArgumentParser(description="SoundCraft: przetwórz jeden katalog żądania WCSS")
    parser.add_argument("request_dir")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    settings = Settings.load(args.config)
    result = asyncio.run(process_request(args.request_dir, settings))
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["execution_code"] == "PASSED" else 1)


if __name__ == "__main__":
    cli()
