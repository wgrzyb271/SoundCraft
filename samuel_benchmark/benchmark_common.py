"""
benchmark_common.py — wspólne narzędzia dla skryptów benchmarku separacji źródeł audio.

Używane przez: prepare_reference.py, run_spleeter_benchmark.py,
run_samaudio_benchmark.py, package_results.py.

Trzyma się protokołu benchmark-protocol-v1.0:
- STEMS i TARGET_SR zgodne z evaluator.py (musi się z nim zgadzać 1:1,
  bo evaluator czyta katalogi w tym samym formacie).
- Struktura katalogów: <dir>/<track>/<stem>.wav

pip install soundfile numpy pyyaml --break-system-packages
"""

from __future__ import annotations

import json
import re
import sys
import time
import warnings
from contextlib import contextmanager
from pathlib import Path

import numpy as np

try:
    import soundfile as sf
except ImportError:
    sys.exit("Brakuje pakietu 'soundfile'. Zainstaluj: pip install soundfile --break-system-packages")

# Musi być zgodne z evaluator.py — nie zmieniaj niezależnie od siebie.
STEMS = ["vocals", "drums", "bass", "other"]
TARGET_SR = 44100  # protokół pkt 3.0: MUSDB18, stereo, 44.1kHz


def sanitize_track_name(name: str) -> str:
    """MUSDB18 nazywa utwory jako 'Artist - Title', co bywa niewygodne jako
    nazwa katalogu (spacje, ukośniki, cudzysłowy). Zamieniamy na bezpieczny
    identyfikator, ale ZACHOWUJEMY mapowanie do oryginalnej nazwy osobno
    (patrz prepare_reference.py -> track_names.json), żeby nie zgubić
    informacji, który plik to który utwór.
    """
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return safe or "track"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_wav(path: Path, audio: np.ndarray, sr: int = TARGET_SR) -> None:
    """Zapisuje audio jako WAV float32. `audio` w kształcie (samples, channels)
    lub (samples,) dla mono."""
    ensure_dir(path.parent)
    sf.write(str(path), audio, sr, subtype="FLOAT")


def load_wav(path: Path) -> tuple[np.ndarray, int]:
    audio, sr = sf.read(str(path), always_2d=True, dtype="float32")
    return audio, sr


def list_track_dirs(root: Path) -> list[Path]:
    if not root.exists():
        sys.exit(f"Katalog nie istnieje: {root}")
    return sorted(p for p in root.iterdir() if p.is_dir())


@contextmanager
def timer():
    """Użycie:
        with timer() as t:
            ... inferencja ...
        czas_sek = t()
    """
    start = time.perf_counter()
    result = {"elapsed": None}

    def _get():
        return result["elapsed"]

    try:
        yield _get
    finally:
        result["elapsed"] = time.perf_counter() - start


def write_inference_times(times: dict[str, float], path: Path) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(times, indent=2, ensure_ascii=False), encoding="utf-8")


def load_yaml_config(path: Path) -> dict:
    try:
        import yaml
    except ImportError:
        sys.exit("Brakuje pakietu 'pyyaml'. Zainstaluj: pip install pyyaml --break-system-packages")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def warn_sr_mismatch(path: Path, sr: int) -> None:
    if sr != TARGET_SR:
        warnings.warn(
            f"{path}: sample rate {sr} != {TARGET_SR}. Zgodnie z protokołem (4.0) "
            "resampling musi być wykonany i udokumentowany w README modelu."
        )
