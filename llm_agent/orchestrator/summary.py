"""Podsumowanie końcowe (dla TUI) budowane ze stanu grafu."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .contracts import AttemptRecord

ERROR_TITLES = {
    "INIT_ERROR": "Inicjalizacja nie powiodła się",
    "INPUT_ERROR": "Niepoprawne dane wejściowe",
    "DEPLOY_ERROR": "Nie udało się przenieść plików na zasoby WCSS",
    "CLASSIFICATION_ERROR": "Klasyfikacja promptu nie powiodła się",
    "UNFEASIBLE": "Zadanie niewykonalne żadnym z dostępnych modeli",
    "NO_CANDIDATES": "Brak kolejnych kandydatów do wykonania zadania",
    "MAX_FAILURES": "Osiągnięto limit nieudanych prób",
    "INTERNAL_ERROR": "Wewnętrzny błąd Orkiestratora",
}


class FinalSummary(BaseModel):
    status: Literal["SUCCESS", "FAILED"]
    category: str | None = None
    stems: list[str] = Field(default_factory=list)
    model: str | None = None
    agent: str | None = None
    rationale: str = ""
    job_id: str | None = None
    output_path: str | None = None
    user_dir: str | None = None
    attempts: list[AttemptRecord] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    warnings: list[str] = Field(default_factory=list)


def _rationale(state: dict[str, Any], attempts: list[AttemptRecord]) -> str:
    cls = state.get("classification") or {}
    parts = []
    if cls:
        stems = f" ({', '.join(cls.get('stems', []))})" if cls.get("stems") else ""
        parts.append(f"Kategoria {cls.get('category')}{stems}: {cls.get('reasoning', '').strip()}")
    failed = [a for a in attempts if a.status == "FAILED"]
    if failed:
        esc = "; ".join(f"{a.model}: {a.failure_type}" for a in failed)
        parts.append(f"Eskalacja po niepowodzeniach ({esc}).")
    return " ".join(p for p in parts if p)


def build_summary(state: dict[str, Any]) -> FinalSummary:
    attempts = [AttemptRecord(**a) for a in state.get("history", [])]
    cls = state.get("classification") or {}
    ok = state.get("outcome") == "SUCCESS"
    report = state.get("report") or {}
    last = attempts[-1] if attempts else None
    code = state.get("error_code")
    msg = state.get("error_message")
    if not ok and code:
        msg = f"{ERROR_TITLES.get(code, code)}" + (f": {msg}" if msg else "")
    return FinalSummary(
        status="SUCCESS" if ok else "FAILED",
        category=cls.get("category"),
        stems=cls.get("stems", []),
        model=last.model if (ok and last) else None,
        agent=last.agent if (ok and last) else None,
        rationale=_rationale(state, attempts),
        job_id=report.get("job_id") if ok else None,
        output_path=report.get("output_path") if ok else None,
        user_dir=state.get("user_dir"),
        attempts=attempts,
        error_code=None if ok else code,
        error_message=None if ok else msg,
        warnings=list(state.get("warnings", [])),
    )
