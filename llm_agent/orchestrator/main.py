"""Punkt wejścia: run_orchestrator(username, temp_audio_path, prompt_text) + CLI (--demo z agentami-dummy)."""
from __future__ import annotations

import argparse
import asyncio
import logging
from typing import TYPE_CHECKING, Any, Callable, Mapping

from .agents import AgentRunner, DummyAgent
from .config import ConfigError, Settings
from .graph import Deps, build_graph
from .llm import ChatClient, DeepSeekClient, LLMError
from .mcp_session import McpSession, NullMcpSession, StdioMcpSession
from .registry import list_available_models
from .summary import FinalSummary, build_summary

if TYPE_CHECKING:  # rich jest potrzebny tylko w trybie debug (TUI) — import leniwy
    from rich.console import Console

log = logging.getLogger("orchestrator")


def _default_mcp_factory(settings: Settings) -> Callable[[], McpSession]:
    """Realny MCP, gdy w config.yaml podano `mcp.command`; w przeciwnym razie lokalny stub."""
    if settings.mcp_command:
        return lambda: StdioMcpSession(settings.mcp_command, list(settings.mcp_args), settings.mcp_env)
    return lambda: NullMcpSession(user_root=settings.user_root)


async def run_orchestrator(
    username: str,
    temp_audio_path: str,
    prompt_text: str,
    *,
    agents: Mapping[str, AgentRunner],
    settings: Settings | None = None,
    llm: ChatClient | None = None,
    mcp_factory: Callable[[], McpSession] | None = None,
    console: "Console | None" = None,
    show: bool | None = None,
) -> FinalSummary:
    """Uruchamia graf end-to-end. Połączenia MCP są zamykane przez `async with` (bez procesów zombie).

    Zwraca `FinalSummary` — to jest kontrakt dla frontendu. TUI (rich) pojawia się TYLKO w trybie debug:
    `show=None` (domyślnie) => decyduje `settings.debug`; jawne `show=True/False` ma pierwszeństwo.
    """
    settings = settings or Settings.load()
    show = settings.debug if show is None else show
    if settings.debug:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s %(levelname)s %(message)s")
        log.debug("start: user=%s audio=%s classifier=%s N=%s", username, temp_audio_path,
                  settings.classifier_mode, settings.max_failures)
    settings.export_env()  # HF_TOKEN itd. z config.yaml dla agentów w tym procesie (env ma pierwszeństwo)
    if llm is None and settings.classifier_mode != "rules" and settings.deepseek_api_key:
        llm = DeepSeekClient(settings)  # jedyny dozwolony LLM
    factory = mcp_factory or _default_mcp_factory(settings)

    async with factory() as mcp:
        deps = Deps(settings=settings, agents=agents, deploy=mcp.deploy_user_pipeline, llm=llm)
        graph = build_graph(deps)
        try:
            state = await graph.ainvoke(
                {"username": username, "temp_audio_path": temp_audio_path, "prompt_text": prompt_text, "trace": []},
                config={"recursion_limit": settings.max_graph_steps},
            )
            summary = FinalSummary(**state["final"]) if state.get("final") else build_summary(
                {**state, "outcome": "FAILED", "error_code": state.get("error_code") or "INTERNAL_ERROR"})
        except Exception as e:  # noqa: BLE001 — TUI zawsze dostaje czytelny komunikat
            summary = build_summary({"outcome": "FAILED", "error_code": "INTERNAL_ERROR", "error_message": repr(e)})
    log.debug("koniec: status=%s error_code=%s", summary.status, summary.error_code)
    if show:
        from .tui import render_final  # TUI tylko w debug — bez rich w ścieżce produkcyjnej

        render_final(summary, console)
    return summary


def _demo_agents(settings: Settings) -> dict[str, AgentRunner]:
    models = list_available_models(settings.models_yaml_path)["models"]
    return {info["agent"]: DummyAgent(info["agent"], verbose=settings.debug) for info in models.values()}  # bez debug: czysty stdout


def cli() -> None:
    ap = argparse.ArgumentParser(description="Orkiestrator audio (LangGraph supervisor, DeepSeek)")
    ap.add_argument("--username", required=True)
    ap.add_argument("--audio", required=True, help="ścieżka do .wav (np. w /tmp)")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--config", default=None, help="ścieżka do config.yaml (domyślnie: $ORCH_CONFIG, ./config.yaml)")
    ap.add_argument("--classifier", choices=["hybrid", "llm", "rules"], default=None)
    ap.add_argument("--debug", action="store_true", help="tryb debug: panel TUI + log DEBUG (nadpisuje config.yaml)")
    ap.add_argument("--demo", action="store_true", help="agenci-dummy zamiast realnych agentów (bez SLURM)")
    a = ap.parse_args()
    try:
        settings = Settings.load(a.config)
    except ConfigError as e:
        raise SystemExit(f"Błąd konfiguracji: {e}")
    if a.classifier:
        settings = settings.with_(classifier_mode=a.classifier)
    if a.debug:
        settings = settings.with_(debug=True)
    if not a.demo:
        raise SystemExit("Realni agenci modeli nie są jeszcze podpięci — użyj --demo albo wywołaj run_orchestrator(agents=...).")
    try:
        summary = asyncio.run(run_orchestrator(a.username, a.audio, a.prompt, agents=_demo_agents(settings), settings=settings))
    except LLMError as e:
        raise SystemExit(f"Błąd DeepSeek: {e}")
    if not settings.debug:  # bez TUI: stdout = jedna linia JSON (FinalSummary), do odczytu przez front/skrypt
        print(summary.model_dump_json())
    raise SystemExit(0 if summary.status == "SUCCESS" else 1)


if __name__ == "__main__":
    cli()
