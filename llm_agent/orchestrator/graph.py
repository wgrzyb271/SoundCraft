"""Graf LangGraph Orkiestratora — dokładnie wg diagramu stateDiagram-v2 z sekcji 3.2 dokumentu,
rozszerzony o Inicjalizacja i DeployPipeline (sekcja 7.1, kroki 1–2):

  Inicjalizacja -> DeployPipeline -> Klasyfikacja -> WyborAgenta -> Zlecenie -> OczekiwanieNaRaport
      -> Sukces | ObslugaBledu -> (WyborAgenta | Niepowodzenie)

LLM (DeepSeek) występuje tylko w węźle Klasyfikacja. Wybór agenta jest deterministyczny (ranking z
models.yaml), a kod grafu wymusza limity (sekcja 2.4: „LLM proponuje, kod pilnuje”).
"""
from __future__ import annotations

import asyncio
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Mapping

from pydantic import ValidationError
from langgraph.graph import END, START, StateGraph

from .agents import AgentRunner
from .classify import Classification, ClassificationError, classify_prompt
from .config import Settings
from .contracts import AgentReport, AgentTask, AttemptRecord
from .deploy import DeployError
from .llm import ChatClient
from .registry import RegistryError, candidates_for, list_available_models
from .state import OrchestratorState
from .summary import build_summary

_USERNAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}")
_DETAILS_MAX = 600


@dataclass
class Deps:
    settings: Settings
    agents: Mapping[str, AgentRunner]                       # klucz: nazwa agenta, np. "agent_bs_roformer"
    deploy: Callable[[str, str, str], Awaitable[str]]       # deploy_user_pipeline (MCP lub stub)
    llm: ChatClient | None = None                           # DeepSeek (jedyny LLM)
    list_models: Callable[[], dict[str, Any]] | None = None  # domyślnie: czyta models.yaml


def pick_next_model(ordered: list[str], models: dict[str, Any], agents: Mapping[str, Any],
                    history: list[dict[str, Any]], max_attempts_per_agent: int) -> str | None:
    """Pierwszy model z rankingu, który ma agenta i nie wyczerpał limitu prób (nie powtarza nieudanej próby)."""
    counts = Counter(h["model"] for h in history)
    for m in ordered:
        if models[m]["agent"] in agents and counts[m] < max_attempts_per_agent:
            return m
    return None


def _fail(node: str, code: str, msg: str, **extra: Any) -> dict[str, Any]:
    return {"error_code": code, "error_message": msg, "trace": [node], **extra}


def build_graph(deps: Deps):
    s = deps.settings
    list_models = deps.list_models or (lambda: list_available_models(s.models_yaml_path))

    # ------------------------------------------------------------------ węzły
    async def Inicjalizacja(state: OrchestratorState) -> dict[str, Any]:
        node = "Inicjalizacja"
        bad_input = []
        if not _USERNAME.fullmatch(state.get("username", "") or ""):
            bad_input.append("niepoprawny username")
        if not (state.get("prompt_text") or "").strip():
            bad_input.append("pusty prompt_text")
        if not (state.get("temp_audio_path") or "").strip():
            bad_input.append("brak temp_audio_path")
        if bad_input:
            return _fail(node, "INPUT_ERROR", "; ".join(bad_input))

        problems = s.validate()
        if s.classifier_mode != "rules" and deps.llm is None:
            problems.append("brak klienta DeepSeek (ustaw DEEPSEEK_API_KEY)")
        try:
            models = list_models()
        except RegistryError as e:
            return _fail(node, "INIT_ERROR", str(e))
        ranked = [m for m, i in models["models"].items() if i["in_ranking"]]
        missing = [m for m in ranked if models["models"][m]["agent"] not in deps.agents]
        warnings: list[str] = []
        if ranked and len(missing) == len(ranked):
            problems.append("brak zarejestrowanych agentów dla modeli z rankingu")
        elif missing:
            warnings.append(f"brak agenta dla modeli: {', '.join(missing)} (pomijane)")
        if problems:
            return _fail(node, "INIT_ERROR", "; ".join(problems))
        return {"models": models, "warnings": warnings, "history": [], "failures": 0,
                "error_code": None, "outcome": None, "trace": [node]}

    async def DeployPipeline(state: OrchestratorState) -> dict[str, Any]:
        node = "DeployPipeline"
        try:
            user_dir = await deps.deploy(state["username"], state["temp_audio_path"], state["prompt_text"])
        except DeployError as e:
            return _fail(node, "DEPLOY_ERROR", f"{e.code}: {e.message}")
        return {"user_dir": user_dir, "trace": [node]}

    async def Klasyfikacja(state: OrchestratorState) -> dict[str, Any]:
        node = "Klasyfikacja"
        try:
            cls = await classify_prompt(state["prompt_text"], s, deps.llm, state["models"])
        except ClassificationError as e:
            return _fail(node, "CLASSIFICATION_ERROR", str(e))
        if cls.category == "C":
            return _fail(node, "UNFEASIBLE", cls.reasoning, classification=cls.model_dump())
        return {"classification": cls.model_dump(), "trace": [node]}

    async def WyborAgenta(state: OrchestratorState) -> dict[str, Any]:
        node = "WyborAgenta"
        cls = Classification(**state["classification"])
        ordered = candidates_for(state["models"], cls.category, cls.stems)
        model = pick_next_model(ordered, state["models"]["models"], deps.agents,
                                state.get("history", []), s.max_attempts_per_agent)
        if model is None:
            if not ordered:
                msg = f"brak modeli zdolnych wykonać zadanie (kategoria {cls.category}, stemy: {cls.stems or '-'})"
            else:
                msg = f"wszyscy kandydaci z rankingu ({', '.join(ordered)}) zostali już wypróbowani lub nie mają agenta"
            return _fail(node, "NO_CANDIDATES", msg)
        return {"current_model": model, "current_agent": state["models"]["models"][model]["agent"],
                "trace": [node]}

    async def Zlecenie(state: OrchestratorState) -> dict[str, Any]:
        cls = Classification(**state["classification"])
        history = [AttemptRecord(**h) for h in state.get("history", [])]
        task = AgentTask(agent=state["current_agent"], model=state["current_model"],
                         user_dir=state["user_dir"], prompt_text=state["prompt_text"],
                         category=cls.category, stems=cls.stems,  # type: ignore[arg-type]
                         attempt_no=len(history) + 1, history=history)
        return {"task": task.model_dump(), "trace": ["Zlecenie"]}

    async def OczekiwanieNaRaport(state: OrchestratorState) -> dict[str, Any]:
        agent_name = state["current_agent"]
        task = AgentTask(**state["task"])
        agent = deps.agents[agent_name]
        try:
            raw = await asyncio.wait_for(agent.run(task), timeout=s.agent_timeout_s)
            report = raw if isinstance(raw, AgentReport) else AgentReport.model_validate(raw)
            if report.agent != agent_name:
                raise ValueError(f"raport od '{report.agent}', oczekiwano '{agent_name}'")
        except asyncio.TimeoutError:
            report = AgentReport(agent=agent_name, status="FAILED", failure_type="TIMEOUT",
                                 details=f"agent nie zwrócił raportu w {s.agent_timeout_s:.0f}s")
        except (ValidationError, ValueError) as e:
            report = AgentReport(agent=agent_name, status="FAILED", failure_type="RUNTIME_ERROR",
                                 details=f"niepoprawny raport agenta: {str(e)[:300]}")
        except Exception as e:  # noqa: BLE001 — awaria agenta = porażka próby, nie awaria orkiestratora
            report = AgentReport(agent=agent_name, status="FAILED", failure_type="RUNTIME_ERROR",
                                 details=f"wyjątek w agencie: {e!r}"[:_DETAILS_MAX])
        return {"report": report.model_dump(), "trace": ["OczekiwanieNaRaport"]}

    def _record(state: OrchestratorState) -> list[dict[str, Any]]:
        r = state["report"]
        rec = AttemptRecord(agent=r["agent"], model=state["current_model"], status=r["status"],
                            job_id=r.get("job_id"), failure_type=r.get("failure_type"),
                            details=(r.get("details") or "")[:_DETAILS_MAX],
                            attempted_params=r.get("attempted_params") or {})
        return [*state.get("history", []), rec.model_dump()]

    async def Sukces(state: OrchestratorState) -> dict[str, Any]:
        upd = {"history": _record(state), "outcome": "SUCCESS", "error_code": None, "trace": ["Sukces"]}
        return {**upd, "final": build_summary({**state, **upd}).model_dump()}

    async def ObslugaBledu(state: OrchestratorState) -> dict[str, Any]:
        r = state["report"]
        counts = s.count_unsupported_task or r.get("failure_type") != "UNSUPPORTED_TASK"
        failures = state.get("failures", 0) + (1 if counts else 0)
        upd: dict[str, Any] = {"history": _record(state), "failures": failures, "trace": ["ObslugaBledu"]}
        if failures >= s.max_failures:
            upd["error_code"] = "MAX_FAILURES"
            upd["error_message"] = f"liczba porażek {failures} >= N={s.max_failures}"
        return upd

    async def Niepowodzenie(state: OrchestratorState) -> dict[str, Any]:
        upd = {"outcome": "FAILED", "trace": ["Niepowodzenie"]}
        return {**upd, "final": build_summary({**state, **upd}).model_dump()}

    # ------------------------------------------------------------------ routing
    def after_ok(nxt: str):
        return lambda st: "Niepowodzenie" if st.get("error_code") else nxt

    def after_wait(st: OrchestratorState) -> str:
        return "Sukces" if st["report"]["status"] == "SUCCESS" else "ObslugaBledu"

    def after_error(st: OrchestratorState) -> str:
        return "Niepowodzenie" if st.get("error_code") == "MAX_FAILURES" else "WyborAgenta"

    g = StateGraph(OrchestratorState)
    for fn in (Inicjalizacja, DeployPipeline, Klasyfikacja, WyborAgenta, Zlecenie,
               OczekiwanieNaRaport, Sukces, ObslugaBledu, Niepowodzenie):
        g.add_node(fn.__name__, fn)
    g.add_edge(START, "Inicjalizacja")
    for src, nxt in (("Inicjalizacja", "DeployPipeline"), ("DeployPipeline", "Klasyfikacja"),
                     ("Klasyfikacja", "WyborAgenta"), ("WyborAgenta", "Zlecenie")):
        g.add_conditional_edges(src, after_ok(nxt), {nxt: nxt, "Niepowodzenie": "Niepowodzenie"})
    g.add_edge("Zlecenie", "OczekiwanieNaRaport")
    g.add_conditional_edges("OczekiwanieNaRaport", after_wait, {"Sukces": "Sukces", "ObslugaBledu": "ObslugaBledu"})
    g.add_conditional_edges("ObslugaBledu", after_error, {"WyborAgenta": "WyborAgenta", "Niepowodzenie": "Niepowodzenie"})
    g.add_edge("Sukces", END)
    g.add_edge("Niepowodzenie", END)
    return g.compile()
