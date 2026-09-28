"""Lokalne demo pełnego grafu bez GPU i bez połączenia z WCSS."""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from .config import Settings
from .contracts import AgentReport, AgentTask
from .main import run_orchestrator
from .mcp_session import NullMcpSession
from .postprocessing import SoundCraftPostProcessor


class DemoStemAgent:
    """Symuluje model GPU, ale tworzy prawdziwe pliki WAV dla postprocessingu."""

    def __init__(self, name: str, fail: bool = False):
        self.name = name
        self.fail = fail

    async def run(self, task: AgentTask) -> AgentReport:
        if self.fail:
            return AgentReport(
                agent=self.name, status="FAILED", failure_type="OOM",
                details="Symulowany OOM — demonstracja eskalacji do następnego modelu.",
            )
        source = Path(task.user_dir) / "input" / "audio_folder" / "audio.wav"
        audio, sample_rate = sf.read(source, always_2d=True, dtype="float32")
        output = Path(task.user_dir) / "work" / self.name / "stems"
        output.mkdir(parents=True, exist_ok=True)
        if task.category == "B":
            sf.write(output / "target.wav", audio * 0.7, sample_rate)
            return AgentReport(
                agent=self.name, status="SUCCESS", job_id="demo-001",
                output_path=str(output), details="Demo SAM Audio utworzył target.wav.",
            )
        gains = {"vocals": 0.7, "drums": 0.15, "bass": 0.1, "other": 0.05}
        for stem, gain in gains.items():
            sf.write(output / f"{stem}.wav", audio * gain, sample_rate)
        return AgentReport(
            agent=self.name, status="SUCCESS", job_id="demo-001",
            output_path=str(output), details="Demo agent utworzył syntetyczne stemy.",
        )


def _make_demo_audio(path: Path) -> None:
    sample_rate = 44100
    duration_s = 2
    time = np.arange(sample_rate * duration_s, dtype=np.float32) / sample_rate
    signal = 0.25 * np.sin(2 * np.pi * 220 * time)
    stereo = np.column_stack((signal, signal))
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, stereo, sample_rate)


def _demo_effects(prompt: str, stem: str) -> dict:
    text = prompt.lower()
    if stem not in text and not (stem == "vocals" and "wokal" in text):
        return {}
    if any(word in text for word in ("głośniej", "glosniej", "wzmocnij", "louder")):
        return {"gain": {"gain_db": 3.0}}
    if any(word in text for word in ("ciszej", "ścisz", "scisz", "quieter")):
        return {"gain": {"gain_db": -3.0}}
    return {}


async def process_demo_request(request_dir: Path, prompt: str, fallback: bool = False) -> dict:
    """Przetwarza katalog backendu lokalnie i zapisuje odpowiedź jak worker WCSS."""
    input_path = request_dir / "input" / "audio_folder" / "audio.wav"

    async def deploy(_username: str, _audio: str, _prompt: str) -> str:
        return str(request_dir)

    agents = {
        "agent_bs_roformer": DemoStemAgent("agent_bs_roformer", fail=fallback),
        "agent_demucs": DemoStemAgent("agent_demucs"),
        "agent_sam_audio": DemoStemAgent("agent_sam_audio"),
    }
    settings = Settings(classifier_mode="rules", models_yaml_path=Path(__file__).parents[1] / "models.yaml")
    summary = await run_orchestrator(
        request_dir.name, str(input_path), prompt, agents=agents, settings=settings,
        mcp_factory=lambda: NullMcpSession(deploy=deploy), show=False,
        postprocess=SoundCraftPostProcessor(effects_decider=_demo_effects),
    )
    payload = summary.model_dump(mode="json")
    response_dir = request_dir / "output" / "agent_response"
    response_dir.mkdir(parents=True, exist_ok=True)
    response_path = response_dir / "response_demo.json"
    response_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


async def run_demo(prompt: str, output: Path, audio: Path | None, fallback: bool) -> dict:
    with tempfile.TemporaryDirectory(prefix="soundcraft-demo-") as temporary:
        request_dir = Path(temporary) / "demo-request"
        input_path = request_dir / "input" / "audio_folder" / "audio.wav"
        input_path.parent.mkdir(parents=True, exist_ok=True)
        if audio is None:
            _make_demo_audio(input_path)
        else:
            shutil.copy2(audio, input_path)

        payload = await process_demo_request(request_dir, prompt, fallback)
        if payload["execution_code"] == "PASSED" and payload.get("output_path"):
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(payload["output_path"], output)
            payload["output_path"] = str(output.resolve())
        return payload


def cli() -> None:
    parser = argparse.ArgumentParser(description="Lokalne demo SoundCraft bez GPU")
    parser.add_argument("--prompt", default="wyciągnij wokal")
    parser.add_argument("--audio", type=Path, default=None, help="opcjonalny wejściowy WAV")
    parser.add_argument("--output", type=Path, default=Path("soundcraft_demo_result.wav"))
    parser.add_argument("--fallback", action="store_true", help="symuluj OOM BS-RoFormer i przejście do Demucs")
    args = parser.parse_args()
    if args.audio is not None and not args.audio.is_file():
        parser.error(f"nie znaleziono pliku: {args.audio}")
    result = asyncio.run(run_demo(args.prompt, args.output, args.audio, args.fallback))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["execution_code"] == "PASSED" else 1)


if __name__ == "__main__":
    cli()
