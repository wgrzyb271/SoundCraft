"""Konfiguracja Orkiestratora. Wartości sporne są parametrami (nie hardkodami)."""
from __future__ import annotations

import os
import warnings
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

# Jedyny dozwolony dostawca LLM. Brak fallbacku na inne modele/lokalne LLM (decyzja użytkownika).
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
# Nazwy modeli DeepSeek się zmieniają (stare aliasy deepseek-chat/-reasoner wygasły w lipcu 2026),
# dlatego nazwa jest konfigurowalna przez DEEPSEEK_MODEL. Sprawdź aktualną na api-docs.deepseek.com.
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"

ClassifierMode = Literal["hybrid", "llm", "rules"]
_CLASSIFIER_MODES = ("hybrid", "llm", "rules")

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_ENV_VAR = "ORCH_CONFIG"
DEFAULT_CONFIG_NAMES = ("config.yaml", "config.yml")


class ConfigError(ValueError):
    """Błąd pliku konfiguracyjnego (zła składnia, nieznany klucz, zły typ)."""


def find_config_file(explicit: str | Path | None = None) -> Path | None:
    """Kolejność: argument `explicit` (np. --config) -> $ORCH_CONFIG -> ./config.yaml -> <repo>/config.yaml.

    Jawnie podana ścieżka, która nie istnieje, to błąd; brak pliku w miejscach domyślnych to nie błąd
    (wtedy działają zmienne środowiskowe i wartości domyślne).
    """
    chosen = explicit or os.environ.get(CONFIG_ENV_VAR)
    if chosen:
        path = Path(chosen).expanduser()
        if not path.is_file():
            raise ConfigError(f"nie znaleziono pliku konfiguracyjnego: {path}")
        return path
    for base in (Path.cwd(), REPO_ROOT):
        for name in DEFAULT_CONFIG_NAMES:
            if (base / name).is_file():
                return base / name
    return None


@dataclass(frozen=True)
class Settings:
    # --- licznik prób (sekcja 3.2 / 7.1 dokumentu) ---
    max_failures: int = 3  # N. TODO: do ustalenia, patrz sekcja 9 dokumentu architektury (#2: wartość N i sposób liczenia)
    max_attempts_per_agent: int = 1  # TODO: do ustalenia, patrz sekcja 9 dokumentu architektury (#2: czy ten sam model może dostać zadanie ponownie)
    count_unsupported_task: bool = True  # TODO: do ustalenia, patrz sekcja 9 dokumentu architektury (#1: czy UNSUPPORTED_TASK zwiększa licznik porażek)

    # --- czas ---
    # Bezpiecznik po stronie Orkiestratora. Właściwe T_wait (oczekiwanie na VRAM) żyje w agencie.
    agent_timeout_s: float = 3600.0  # TODO: do ustalenia, patrz sekcja 9 dokumentu architektury (#3: T_wait, budżet czasu)

    # --- klasyfikacja promptu ---
    classifier_mode: ClassifierMode = "hybrid"  # TODO: do ustalenia, patrz sekcja 9 dokumentu architektury (#5: kto klasyfikuje; co przy niepewności)
    llm_parse_retries: int = 1  # ponowienie tego SAMEGO modelu DeepSeek przy niepoprawnym JSON (to nie jest fallback)

    # --- DeepSeek (jedyny LLM) ---
    deepseek_api_key: str | None = field(default=None, repr=False)
    deepseek_base_url: str = DEEPSEEK_BASE_URL
    deepseek_model: str = DEFAULT_DEEPSEEK_MODEL
    deepseek_thinking: bool = False  # klasyfikacja jest prosta; tryb thinking wyłączony (szybciej/taniej)
    llm_timeout_s: float = 60.0

    # --- klucze i tokeny (repr=False: nigdy nie trafiają do logów ani tracebacków) ---
    # Hugging Face: potrzebny agentom modeli (np. gated SAM Audio); orkiestrator sam go nie używa,
    # tylko eksportuje jako HF_TOKEN / HUGGING_FACE_HUB_TOKEN (patrz export_env()).
    huggingface_token: str | None = field(default=None, repr=False)
    extra_env: dict[str, str] = field(default_factory=dict, repr=False)  # dowolne dodatkowe zmienne środowiskowe

    # --- tryb debug ---
    # False (produkcja): brak TUI; wynik oddaje FinalSummary (front / API). True: panel TUI (rich) + log debug.
    debug: bool = False

    # --- MCP (deploy_user_pipeline). Puste `mcp_command` => lokalny stub NullMcpSession ---
    # TODO: do ustalenia, patrz sekcja 9 dokumentu architektury (komenda serwera MCP na WCSS)
    mcp_command: str | None = None
    mcp_args: tuple[str, ...] = ()
    mcp_env: dict[str, str] | None = field(default=None, repr=False)

    # --- ścieżki ---
    models_yaml_path: Path = Path(__file__).resolve().parent.parent / "models.yaml"
    user_root: str = "/tmp/orkiestrator_users"  # tylko dla lokalnego stuba deploy; realny deploy = MCP deploy_user_pipeline

    # --- graf ---
    max_graph_steps: int = 80  # recursion_limit LangGraph (bezpiecznik przed zapętleniem)

    def with_(self, **kw) -> "Settings":
        return replace(self, **kw)

    def validate(self) -> list[str]:
        """Zwraca listę błędów konfiguracji (pusta = OK)."""
        errs: list[str] = []
        if self.max_failures < 1:
            errs.append("max_failures (N) musi być >= 1")
        if self.max_attempts_per_agent < 1:
            errs.append("max_attempts_per_agent musi być >= 1")
        if self.agent_timeout_s <= 0:
            errs.append("agent_timeout_s musi być > 0")
        if self.classifier_mode not in _CLASSIFIER_MODES:
            errs.append(f"classifier_mode musi być jednym z: {', '.join(_CLASSIFIER_MODES)} (jest: {self.classifier_mode!r})")
        if not self.deepseek_base_url.rstrip("/").startswith(DEEPSEEK_BASE_URL):
            errs.append(f"deepseek_base_url musi wskazywać na {DEEPSEEK_BASE_URL} (wyłącznie DeepSeek)")
        return errs

    # ------------------------------------------------------------------ ładowanie
    @classmethod
    def load(cls, config_path: str | Path | None = None) -> "Settings":
        """Wartości domyślne <- plik config.yaml <- zmienne środowiskowe (najwyższy priorytet)."""
        path = find_config_file(config_path)
        kw = _kwargs_from_file(path) if path else {}
        kw.update(_kwargs_from_env(os.environ))
        return cls(**kw)

    @classmethod
    def from_env(cls) -> "Settings":
        """Zachowane dla zgodności wstecznej: to samo co load() (czyta też config.yaml, jeśli istnieje)."""
        return cls.load()

    def export_env(self) -> None:
        """Eksportuje tokeny i `env:` z konfiguracji do os.environ (agenci działają w tym samym procesie).

        Nigdy nie nadpisuje zmiennej już ustawionej w środowisku — środowisko ma pierwszeństwo.
        """
        pairs: dict[str, str] = dict(self.extra_env)
        if self.huggingface_token:
            pairs.setdefault("HF_TOKEN", self.huggingface_token)
            pairs.setdefault("HUGGING_FACE_HUB_TOKEN", self.huggingface_token)
        for key, value in pairs.items():
            os.environ.setdefault(key, value)


# ---------------------------------------------------------------------- plik konfiguracyjny
_TOP_LEVEL_KEYS = {"debug", "api_keys", "env", "deepseek", "orchestrator", "paths", "mcp"}


def _section(data: dict[str, Any], name: str, allowed: set[str]) -> dict[str, Any]:
    sec = data.get(name) or {}
    if not isinstance(sec, dict):
        raise ConfigError(f"sekcja '{name}' musi być słownikiem")
    unknown = set(sec) - allowed
    if unknown:
        raise ConfigError(f"nieznane klucze w sekcji '{name}': {', '.join(sorted(map(str, unknown)))}")
    return sec


def _str_map(value: Any, where: str) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"'{where}' musi być słownikiem NAZWA: wartość")
    return {str(k): str(v) for k, v in value.items() if v is not None}


def _kwargs_from_file(path: Path) -> dict[str, Any]:
    import yaml  # leniwy import: rdzeń nie wymaga PyYAML, gdy nie ma pliku

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"{path}: niepoprawny YAML: {e}") from e
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: plik musi zawierać słownik na najwyższym poziomie")
    unknown = set(data) - _TOP_LEVEL_KEYS
    if unknown:
        raise ConfigError(f"{path}: nieznane klucze: {', '.join(sorted(map(str, unknown)))}")

    kw: dict[str, Any] = {}
    keys = _section(data, "api_keys", {"deepseek", "huggingface"})
    if keys.get("deepseek"):
        kw["deepseek_api_key"] = str(keys["deepseek"])
    if keys.get("huggingface"):
        kw["huggingface_token"] = str(keys["huggingface"])
    if (kw.get("deepseek_api_key") or kw.get("huggingface_token") or data.get("env")) \
            and os.name == "posix" and path.stat().st_mode & 0o077:
        warnings.warn(f"{path} zawiera klucze API, a jest czytelny dla innych użytkowników — "
                      f"ustaw `chmod 600 {path}` (WCSS to maszyna współdzielona)", stacklevel=3)

    ds = _section(data, "deepseek", {"model", "thinking", "timeout_s"})
    if "model" in ds:
        kw["deepseek_model"] = str(ds["model"])
    if "thinking" in ds:
        kw["deepseek_thinking"] = bool(ds["thinking"])
    if "timeout_s" in ds:
        kw["llm_timeout_s"] = float(ds["timeout_s"])

    orch = _section(data, "orchestrator",
                    {"classifier", "max_failures", "max_attempts_per_agent", "agent_timeout_s", "count_unsupported_task"})
    if "classifier" in orch:
        kw["classifier_mode"] = orch["classifier"]
    if "max_failures" in orch:
        kw["max_failures"] = int(orch["max_failures"])
    if "max_attempts_per_agent" in orch:
        kw["max_attempts_per_agent"] = int(orch["max_attempts_per_agent"])
    if "agent_timeout_s" in orch:
        kw["agent_timeout_s"] = float(orch["agent_timeout_s"])
    if "count_unsupported_task" in orch:
        kw["count_unsupported_task"] = bool(orch["count_unsupported_task"])

    paths = _section(data, "paths", {"models_yaml", "user_root"})
    if paths.get("models_yaml"):
        p = Path(str(paths["models_yaml"])).expanduser()
        kw["models_yaml_path"] = p if p.is_absolute() else (path.parent / p).resolve()
    if paths.get("user_root"):
        kw["user_root"] = str(paths["user_root"])

    mcp = _section(data, "mcp", {"command", "args", "env"})
    if mcp.get("command"):
        kw["mcp_command"] = str(mcp["command"])
    if mcp.get("args"):
        if not isinstance(mcp["args"], list):
            raise ConfigError("'mcp.args' musi być listą")
        kw["mcp_args"] = tuple(str(a) for a in mcp["args"])
    if mcp.get("env"):
        kw["mcp_env"] = _str_map(mcp["env"], "mcp.env")

    if "debug" in data:
        kw["debug"] = bool(data["debug"])
    if data.get("env"):
        kw["extra_env"] = _str_map(data["env"], "env")
    return kw


def _kwargs_from_env(env: Any) -> dict[str, Any]:
    """Zmienne środowiskowe nadpisują plik. Zwraca tylko te klucze, które faktycznie są ustawione."""
    kw: dict[str, Any] = {}
    if "ORCH_MAX_FAILURES" in env:
        kw["max_failures"] = int(env["ORCH_MAX_FAILURES"])
    if "ORCH_MAX_ATTEMPTS_PER_AGENT" in env:
        kw["max_attempts_per_agent"] = int(env["ORCH_MAX_ATTEMPTS_PER_AGENT"])
    if "ORCH_AGENT_TIMEOUT_S" in env:
        kw["agent_timeout_s"] = float(env["ORCH_AGENT_TIMEOUT_S"])
    if "ORCH_CLASSIFIER" in env:
        kw["classifier_mode"] = env["ORCH_CLASSIFIER"]
    if "ORCH_MODELS_YAML" in env:
        kw["models_yaml_path"] = Path(env["ORCH_MODELS_YAML"])
    if "ORCH_DEBUG" in env:
        kw["debug"] = env["ORCH_DEBUG"].strip().lower() in ("1", "true", "yes", "on")
    if "DEEPSEEK_MODEL" in env:
        kw["deepseek_model"] = env["DEEPSEEK_MODEL"]
    if env.get("DEEPSEEK_API_KEY"):
        kw["deepseek_api_key"] = env["DEEPSEEK_API_KEY"]
    hf = env.get("HF_TOKEN") or env.get("HUGGING_FACE_HUB_TOKEN")
    if hf:
        kw["huggingface_token"] = hf
    return kw
