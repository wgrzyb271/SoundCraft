"""Połączenie mixAgent i deterministycznego PostProcessing w jeden etap grafu."""
from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .contracts import AgentReport, AgentTask, PostProcessingReport

StemProcessor = Callable[..., dict[str, Any]]
Stitcher = Callable[..., dict[str, Any]]

_EFFECT_REQUEST = re.compile(
    r"\b(głośn\w*|glosn\w*|cisz\w*|wzmocn\w*|ścisz\w*|scisz\w*|gain|eq|equaliz\w*|"
    r"korekcj\w*|kompres\w*|compress\w*|limit\w*|bas\s+więcej|more\s+bass)\b",
    re.IGNORECASE,
)


def _default_stem_processor(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from mixAgent.server import process_stem

    return process_stem(*args, **kwargs)


def _default_stitcher(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from PostProcessing.stitch_stems import stitch_stems

    return stitch_stems(*args, **kwargs)


def _find_stems(output_path: str) -> dict[str, Path]:
    root = Path(output_path)
    if not root.is_dir():
        raise FileNotFoundError(f"agent nie zwrócił katalogu stemów: {root}")
    candidates = (root, root / "audio")
    stems: dict[str, Path] = {}
    for name in ("vocals", "drums", "bass", "other", "target"):
        for directory in candidates:
            path = directory / f"{name}.wav"
            if path.is_file() and path.stat().st_size > 0:
                stems[name] = path
                break
    return stems


def _selected_stems(task: AgentTask) -> list[str]:
    if task.category == "B":
        return ["target"]
    selected: list[str] = []
    for stem in task.stems:
        expanded = ("drums", "bass", "other") if stem == "instrumental" else (stem,)
        for name in expanded:
            if name not in selected:
                selected.append(name)
    return selected


class SoundCraftPostProcessor:
    """Uruchamia mixAgent per stem, a następnie zawsze składa finalny WAV."""

    def __init__(
        self,
        stem_processor: StemProcessor = _default_stem_processor,
        stitcher: Stitcher = _default_stitcher,
        effects_decider: Callable[[str, str], dict[str, Any]] | None = None,
    ):
        self._stem_processor = stem_processor
        self._stitcher = stitcher
        self._effects_decider = effects_decider

    async def __call__(self, task: AgentTask, report: AgentReport) -> PostProcessingReport:
        result = await asyncio.to_thread(self._run, task, report)
        if result.status == "SUCCESS":
            temporary = Path(str(result.artifacts.pop("temporary_output")))
            final = Path(result.output_path or "")
            # Publikacja odbywa się dopiero po powrocie z wątku. Jeśli wait_for
            # anuluje etap, spóźniony wątek może zostawić plik roboczy, ale nie
            # opublikuje changed_audio_*.wav dla odpowiedzi FAILED.
            temporary.replace(final)
        return result

    def _run(self, task: AgentTask, report: AgentReport) -> PostProcessingReport:
        try:
            available = _find_stems(report.output_path or "")
            selected = _selected_stems(task)
            if not selected:
                raise ValueError("post-processing wymaga co najmniej jednego stema")
            missing = [name for name in selected if name not in available]
            if missing:
                raise FileNotFoundError(f"brak stemów wymaganych przez prompt: {', '.join(missing)}")

            user_dir = Path(task.user_dir)
            work_dir = user_dir / "work" / "postprocessing"
            output_dir = user_dir / "output" / "audio_folder"
            work_dir.mkdir(parents=True, exist_ok=True)
            output_dir.mkdir(parents=True, exist_ok=True)

            processed: dict[str, str] = {}
            effects: dict[str, Any] = {}
            needs_effects = bool(_EFFECT_REQUEST.search(task.prompt_text))
            for stem in selected:
                mixed_path = work_dir / f"mixed_{stem}.wav"
                kwargs: dict[str, Any] = {}
                if self._effects_decider is not None:
                    kwargs["effects_decider"] = self._effects_decider
                elif not needs_effects:
                    # Czysta separacja nie wymaga drugiego wywołania LLM; mixAgent nadal
                    # wykonuje bezpieczny limiter i zapisuje ujednolicony WAV.
                    kwargs["chosen_effects"] = {}
                result = self._stem_processor(
                    str(available[stem]), task.prompt_text, str(mixed_path), stem, **kwargs
                )
                if not mixed_path.is_file() or mixed_path.stat().st_size == 0:
                    raise RuntimeError(f"mixAgent nie utworzył pliku dla stema {stem}")
                processed[stem] = str(mixed_path)
                effects[stem] = result.get("effects_used", {})

            final_path = output_dir / f"changed_audio_{task.attempt_no:03d}.wav"
            temporary_path = work_dir / f"final_{task.attempt_no:03d}.wav"
            stitched = self._stitcher(processed, str(temporary_path))
            if stitched.get("status") != "SUCCESS":
                raise RuntimeError(stitched.get("details") or stitched.get("error") or "stitch_stems FAILED")
            if not temporary_path.is_file() or temporary_path.stat().st_size == 0:
                raise RuntimeError("PostProcessing nie utworzył finalnego pliku WAV")
            return PostProcessingReport(
                status="SUCCESS",
                output_path=str(final_path),
                details=f"mixAgent i PostProcessing zakończone; stemy: {', '.join(selected)}",
                artifacts={
                    "source_stems": {k: str(available[k]) for k in selected},
                    "effects": effects,
                    "temporary_output": str(temporary_path),
                },
            )
        except Exception as exc:  # noqa: BLE001 — kontrakt etapu zwraca ustrukturyzowany błąd
            return PostProcessingReport(
                status="FAILED", failure_type="RUNTIME_ERROR", details=str(exc)[:600]
            )
