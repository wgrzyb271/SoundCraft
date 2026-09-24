"""Rejestr modeli: czytanie models.yaml i narzędzie `list_available_models`.

Orkiestrator NIE liczy fitness i NIE zmienia kolejności rankingu (sekcja 4.1, zasada 6) — tylko czyta.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

STEMS = ("vocals", "drums", "bass", "other", "instrumental")
# Twardy zakaz (sekcja 4/7.1): SAM Audio nigdy w kategorii A, niezależnie od danych w yaml.
FORBIDDEN_FOR_STEMS = frozenset({"sam_audio"})


class RegistryError(RuntimeError):
    pass


def load_models_yaml(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        raise RegistryError(f"Nie można wczytać {p}: {e}") from e
    if not isinstance(raw, dict):
        raise RegistryError(f"{p}: oczekiwano mapowania na najwyższym poziomie")

    models = raw.get("models")
    ranking = raw.get("ranking")
    if not isinstance(models, dict) or not models:
        raise RegistryError(f"{p}: brak sekcji 'models'")
    if not isinstance(ranking, dict) or not isinstance(ranking.get("stems"), dict):
        raise RegistryError(f"{p}: brak sekcji 'ranking.stems'")
    for mid, info in models.items():
        if not isinstance(info, dict) or not info.get("agent") or not isinstance(info.get("tasks"), list):
            raise RegistryError(f"{p}: model '{mid}' wymaga pól 'agent' i 'tasks' (lista)")

    ranked = {m for lst in ranking["stems"].values() for m in lst} | set(ranking.get("open_tasks", []))
    unknown = ranked - set(models)
    if unknown:
        raise RegistryError(f"{p}: ranking wskazuje nieznane modele: {sorted(unknown)}")
    overlap = ranked & set(ranking.get("no_results_yet", []))
    if overlap:
        raise RegistryError(f"{p}: modele jednocześnie w rankingu i w no_results_yet: {sorted(overlap)}")
    return raw


def candidates_for(snapshot: dict[str, Any], category: str, stems: list[str]) -> list[str]:
    """Uporządkowana (malejąco wg rankingu) lista modeli zdolnych wykonać zadanie.

    A: kolejność wg rankingu głównego stemu (pierwszy z `stems`), filtr: model musi obsługiwać
       WSZYSTKIE żądane stemy. TODO: do ustalenia, patrz sekcja 9 dokumentu architektury
       (ranking dla promptu z kilkoma stemami naraz nie jest zdefiniowany).
    B: ranking `open_tasks`.
    """
    models = snapshot["models"]
    if category == "B":
        ordered = list(snapshot["ranking"]["open_tasks"])
        return [m for m in ordered if "open" in models[m]["tasks"]]
    if category == "A":
        if not stems:
            return []
        primary = stems[0]
        rank_key = snapshot.get("stem_aliases", {}).get(primary, primary)
        ordered = list(snapshot["ranking"]["stems"].get(rank_key, []))
        return [
            m
            for m in ordered
            if m not in FORBIDDEN_FOR_STEMS and all(f"stem:{s}" in models[m]["tasks"] for s in stems)
        ]
    return []  # C: nie ma kandydatów


def list_available_models(path: str | Path, task: str | None = None) -> dict[str, Any]:
    """Narzędzie Orkiestratora: VRAM, typy zadań i ranking per stem z models.yaml.

    `task`: None | "open" | "stem:<nazwa>" — gdy podane, dodaje klucz `candidates`.
    """
    raw = load_models_yaml(path)
    ranking = raw["ranking"]
    ranked_ids = {m for lst in ranking["stems"].values() for m in lst} | set(ranking.get("open_tasks", []))
    snap: dict[str, Any] = {
        "data_snapshot": ranking.get("data_snapshot"),
        "models": {
            mid: {
                "agent": info["agent"],
                "vram_gb": info.get("vram_gb"),
                "tasks": list(info["tasks"]),
                "in_ranking": mid in ranked_ids,
            }
            for mid, info in raw["models"].items()
        },
        "ranking": {
            "stems": {k: list(v) for k, v in ranking["stems"].items()},
            "open_tasks": list(ranking.get("open_tasks", [])),
        },
        "stem_aliases": dict(raw.get("stem_aliases", {})),
        "no_results_yet": list(ranking.get("no_results_yet", [])),
    }
    if task is not None:
        if task == "open":
            snap["candidates"] = candidates_for(snap, "B", [])
        elif task.startswith("stem:") and task[5:] in STEMS:
            snap["candidates"] = candidates_for(snap, "A", [task[5:]])
        else:
            raise ValueError(f"Nieznane task='{task}' (dozwolone: 'open', 'stem:<{'|'.join(STEMS)}>')")
    return snap
