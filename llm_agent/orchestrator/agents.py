"""Interfejs agenta modelu + agent-dummy do testów/demo/placeholderów (bez realnego SLURM).

Realnych agentów (podgrafy LangGraph per model: agent_bs_roformer, agent_demucs, agent_spleeter,
agent_open_unmix, agent_sam_audio) buduje osobna osoba — orkiestrator wymaga od nich tylko, żeby
spełniały protokół `AgentRunner` (metoda async `run(task) -> AgentReport`). Do czasu ich powstania
`DummyAgent` służy jako placeholder: drukuje na konsolę, że "uruchamia" danego agenta, i zwraca
zaskryptowany wynik, żeby cały graf dało się odpalić end-to-end już teraz.
"""
from __future__ import annotations

import asyncio
from typing import Any, Protocol

from .contracts import AgentReport, AgentTask


class AgentRunner(Protocol):
    name: str

    async def run(self, task: AgentTask) -> AgentReport | dict[str, Any]: ...


class DummyAgent:
    """Agent-placeholder: przy `run()` drukuje "Uruchamiam agenta <nazwa>..." i zwraca zaskryptowany wynik.

    script: lista elementów — AgentReport | dict | Exception. Ostatni element powtarza się w nieskończoność.
    delay_s: sztuczne opóźnienie (test timeoutu).
    verbose: czy drukować na konsolę przy każdym wywołaniu (domyślnie tak; testy mogą wyłączyć, jeśli output przeszkadza).
    """

    def __init__(self, name: str, script: list[Any] | None = None, delay_s: float = 0.0, verbose: bool = True):
        self.name = name
        self.script = script if script is not None else [self.success()]
        self.delay_s = delay_s
        self.verbose = verbose
        self.calls: list[AgentTask] = []

    def success(self, job_id: str = "1000") -> AgentReport:
        return AgentReport(agent=self.name, status="SUCCESS", job_id=job_id,
                           output_path=f"/tmp/dummy/{self.name}/wynik.wav", details="dummy OK")

    def failure(self, failure_type: str = "RUNTIME_ERROR", job_id: str | None = None,
                params: dict[str, Any] | None = None) -> AgentReport:
        return AgentReport(agent=self.name, status="FAILED", job_id=job_id, failure_type=failure_type,
                           details=f"dummy {failure_type}", attempted_params=params or {})

    async def run(self, task: AgentTask) -> AgentReport | dict[str, Any]:
        attempt = len(self.calls) + 1
        if self.verbose:
            stems = f" ({', '.join(task.stems)})" if task.stems else ""
            print(f"[DUMMY] Uruchamiam agenta {self.name} — model={task.model}{stems}, "
                  f"próba {attempt}, user_dir={task.user_dir}")
        self.calls.append(task)
        if self.delay_s:
            await asyncio.sleep(self.delay_s)
        idx = min(len(self.calls) - 1, len(self.script) - 1)
        item = self.script[idx]
        if isinstance(item, Exception):
            if self.verbose:
                print(f"[DUMMY] agent {self.name}: wyjątek {item!r}")
            raise item
        if self.verbose:
            status = item.get("status") if isinstance(item, dict) else getattr(item, "status", "?")
            print(f"[DUMMY] agent {self.name}: zwracam status={status}")
        return item
