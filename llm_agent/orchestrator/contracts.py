"""Kontrakt raportu agent -> orkiestrator (sekcja 2.2 dokumentu) oraz zlecenie orkiestrator -> agent."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

# TODO: do ustalenia, patrz sekcja 9 dokumentu architektury (#1: ostateczna lista typów błędów)
FailureType = Literal["NO_RESOURCES", "OOM", "RUNTIME_ERROR", "TIMEOUT", "UNSUPPORTED_TASK"]


class AttemptRecord(BaseModel):
    """Jedna próba (agent + wynik). Historia prób jest przekazywana kolejnym agentom."""

    agent: str
    model: str
    status: Literal["SUCCESS", "FAILED"]
    job_id: str | None = None
    failure_type: FailureType | None = None
    details: str = ""
    attempted_params: dict[str, Any] = Field(default_factory=dict)


class AgentTask(BaseModel):
    """Zlecenie dla agenta modelu (sekcja 7.1: user_dir, prompt_text, historia prób)."""

    agent: str
    model: str
    user_dir: str
    prompt_text: str
    category: Literal["A", "B"]
    stems: list[str] = Field(default_factory=list)
    attempt_no: int = 1
    history: list[AttemptRecord] = Field(default_factory=list)


class AgentReport(BaseModel):
    """Raport agenta -> orkiestrator (JSON z kontraktu)."""

    agent: str
    status: Literal["SUCCESS", "FAILED"]
    job_id: str | None = None
    output_path: str | None = None
    failure_type: FailureType | None = None
    details: str = ""
    attempted_params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _consistency(self) -> "AgentReport":
        if self.status == "SUCCESS" and not self.output_path:
            raise ValueError("SUCCESS wymaga output_path")
        if self.status == "FAILED" and self.failure_type is None:
            raise ValueError("FAILED wymaga failure_type")
        return self
