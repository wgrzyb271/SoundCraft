"""Stan grafu Orkiestratora. Historia prób i licznik N leżą tu, a nie w pamięci LLM (sekcja 2.5)."""
from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict


class OrchestratorState(TypedDict, total=False):
    # wejście
    username: str
    temp_audio_path: str
    prompt_text: str
    # pośrednie
    user_dir: str
    models: dict[str, Any]          # wynik list_available_models()
    warnings: list[str]
    classification: dict[str, Any]
    current_model: str | None
    current_agent: str | None
    task: dict[str, Any]            # AgentTask.model_dump()
    report: dict[str, Any]          # AgentReport.model_dump()
    history: list[dict[str, Any]]   # AttemptRecord.model_dump() — wszystkie dotychczasowe próby
    failures: int                   # licznik porażek (porównywany z N)
    # wynik
    outcome: Literal["SUCCESS", "FAILED"] | None
    error_code: str | None
    error_message: str | None
    final: dict[str, Any]           # FinalSummary.model_dump()
    trace: Annotated[list[str], operator.add]   # odwiedzone węzły (debug/testy)
