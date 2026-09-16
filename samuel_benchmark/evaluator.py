#!/usr/bin/env python3
"""
evaluator.py — skrypt ewaluacyjny benchmarku SAM-Audio-small
(zgodnie z benchmark-protocol-v1.0)

Liczy SDR, SI-SDR, PQ, CE, CU, inference_time_sec dla outputu
`run_samaudio_benchmark.py` względem referencji MUSDB18.

-----------------------------------------------------------------------------
OCZEKIWANA STRUKTURA KATALOGÓW
-----------------------------------------------------------------------------

outputs-dir/                     (output modelu — to co dev sam wygenerował)
├── track_001/
│   ├── vocals.wav                (opcjonalnie — tylko jeśli model wspiera dany stem)
│   ├── drums.wav
│   ├── bass.wav
│   └── other.wav
├── track_002/
│   └── ...
└── ...

reference-dir/                   (ground truth z MUSDB18 — ten sam dla wszystkich)
├── track_001/
│   ├── vocals.wav
│   ├── drums.wav
│   ├── bass.wav
│   └── other.wav
└── ...

inference-times.json             (opcjonalny plik z czasami inferencji per utwór)
{
  "track_001": 12.34,
  "track_002": 9.87
}

-----------------------------------------------------------------------------
UŻYCIE
-----------------------------------------------------------------------------

python evaluator.py \
    --model-name SamAudio \
    --outputs-dir ./samaudio_outputs \
    --reference-dir ./musdb18_test_wav \
    --inference-times ./samaudio_inference_times.json \
    --output samaudio_results.csv

Wszystkie powyższe flagi mają teraz sensowne domyślne wartości dla tego
projektu (patrz KONFIGURACJA niżej) — samo `python evaluator.py` też
zadziała, jeśli struktura katalogów jest standardowa.

Jeżeli model nie obsługuje danego źródła (np. Open-Unmix nie robi "guitar",
Spleeter w wersji 4-stem nie robi "piano" itd.), po prostu nie twórz pliku
danego stemu w outputs-dir/track_XXX/ — skrypt oznaczy go jako "not_supported"
i pominie w metrykach liczbowych, zgodnie z protokołem (pkt 5.0).

-----------------------------------------------------------------------------
ZALEŻNOŚCI
-----------------------------------------------------------------------------

pip install soundfile numpy museval audiobox_aesthetics pyyaml --break-system-packages

museval i audiobox_aesthetics są opcjonalne w tym sensie, że skrypt się nie
wywali gdy ich brakuje — po prostu odpowiednie kolumny (SDR / PQ,CE,CU)
zostaną wypełnione jako puste, z ostrzeżeniem w stderr. SI-SDR liczone jest
zawsze (implementacja własna, bez zależności).

-----------------------------------------------------------------------------
KONFIGURACJA PRZEZ PLIK YAML (opcjonalnie)
-----------------------------------------------------------------------------

Zamiast wypisywać wszystkie flagi w linii komend, możesz trzymać je w pliku
config.yaml (już przygotowany dla tego projektu, patrz plik obok):

    model_name: "SamAudio"
    outputs_dir: "./samaudio_outputs"
    reference_dir: "./musdb18_test_wav"
    inference_times: "./samaudio_inference_times.json"
    output: "samaudio_results.csv"
    summary_output: "samaudio_summary.csv"

i uruchomić po prostu:

    python evaluator.py --config config.yaml

albo, jeśli plik nazywa się dokładnie "config.yaml" i leży w katalogu, z
którego odpalasz skrypt — wystarczy:

    python evaluator.py

Każda flaga podana ręcznie w CLI ma pierwszeństwo przed wartością z configu
(np. `python evaluator.py --config config.yaml --model-name SamAudio-v2`
nadpisze tylko model_name, reszta zostanie wzięta z pliku).
"""

import argparse
import csv
import json
import os
import statistics
import sys
import warnings
from pathlib import Path

import numpy as np

# Wyciszenie nieszkodliwych warningów z zależności (torch/audiobox_aesthetics),
# które zaśmiecają output i nie dotyczą niczego w tym skrypcie.
warnings.filterwarnings("ignore", category=FutureWarning, module="torch.*")
warnings.filterwarnings("ignore", category=UserWarning, module="torch.*")
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")

try:
    import soundfile as sf
except ImportError:
    sys.exit("Brakuje pakietu 'soundfile'. Zainstaluj: pip install soundfile --break-system-packages")

# --- opcjonalne zależności ---------------------------------------------------

try:
    import museval  # oficjalna implementacja BSS-eval używana dla MUSDB18
    HAS_MUSEVAL = True
except ImportError:
    HAS_MUSEVAL = False

try:
    import torch
    from audiobox_aesthetics.infer import initialize_predictor
    HAS_AESTHETICS = True
except ImportError:
    HAS_AESTHETICS = False


try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

STEMS = ["vocals", "drums", "bass", "other"]
TARGET_SR = 44100  # zgodnie z protokołem: 44.1kHz, stereo


# =============================================================================
# I/O
# =============================================================================

def load_audio(path: Path) -> np.ndarray:
    """Wczytuje plik audio jako float32, kształt (samples, channels)."""
    audio, sr = sf.read(str(path), always_2d=True, dtype="float32")
    if sr != TARGET_SR:
        warnings.warn(
            f"{path}: sample rate {sr} != {TARGET_SR}. "
            "Zgodnie z protokołem (4.0) resampling powinien być wykonany "
            "i udokumentowany PRZED ewaluacją, nie w evaluatorze."
        )
    return audio


def find_tracks(reference_dir: Path) -> list[str]:
    """Lista utworów test setu na podstawie referencji (ground truth)."""
    return sorted(p.name for p in reference_dir.iterdir() if p.is_dir())


def align_length(ref: np.ndarray, est: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Przycina oba sygnały do wspólnej, minimalnej długości (drobne różnice
    długości bywają nieuniknione po separacji, np. padding modelu)."""
    n = min(len(ref), len(est))
    return ref[:n], est[:n]


# =============================================================================
# METRYKI: SDR / SI-SDR
# =============================================================================

def compute_si_sdr(reference: np.ndarray, estimate: np.ndarray, eps: float = 1e-8) -> float:
    """Scale-Invariant SDR, uśrednione po kanałach.
    Standardowa definicja (Le Roux et al., 2018).
    """
    ref = reference.mean(axis=1) if reference.ndim > 1 else reference
    est = estimate.mean(axis=1) if estimate.ndim > 1 else estimate
    ref, est = align_length(ref, est)

    ref = ref - ref.mean()
    est = est - est.mean()

    dot = np.dot(est, ref)
    s_target = (dot / (np.dot(ref, ref) + eps)) * ref
    e_noise = est - s_target

    ratio = (np.sum(s_target ** 2) + eps) / (np.sum(e_noise ** 2) + eps)
    return 10 * np.log10(ratio + eps)


def compute_sdr_museval(reference: np.ndarray, estimate: np.ndarray) -> float | None:
    """Klasyczny BSS-eval SDR przez museval (standard używany do MUSDB18).
    Zwraca None jeśli museval nie jest zainstalowany.
    """
    if not HAS_MUSEVAL:
        return None

    ref, est = align_length(reference, estimate)
    # museval oczekuje kształtu (nsrc, nsamples, nchan) -> tu 1 źródło
    ref_ = ref[np.newaxis, ...]
    est_ = est[np.newaxis, ...]
    sdr, _, _, _ = museval.evaluate(ref_, est_, win=ref_.shape[1], hop=ref_.shape[1])
    # museval zwraca wartość per-frame; bierzemy medianę zgodnie z konwencją SiSEC/MUSDB18
    return float(np.nanmedian(sdr))


# =============================================================================
# METRYKI: AudioBox-Aesthetics (PQ, CE, CU)
# =============================================================================

_aesthetics_predictor = None


def get_aesthetics_predictor():
    global _aesthetics_predictor
    if _aesthetics_predictor is None and HAS_AESTHETICS:
        _aesthetics_predictor = initialize_predictor()
    return _aesthetics_predictor


def compute_aesthetics(path: Path) -> dict:
    """Zwraca dict z kluczami PQ, CE, CU.
    Jeśli audiobox_aesthetics nie jest zainstalowany, zwraca puste wartości.

    Uwaga: audio wczytujemy sami przez soundfile i podajemy predictorowi
    gotowy tensor (klucz "path" + "sample_rate" zamiast ścieżki do pliku).
    Omija to torchaudio.load()/torchcodec, który na wielu maszynach (zwłaszcza
    macOS) wymaga systemowego FFmpeg w konkretnej, zgodnej wersji i potrafi
    się wysypać przy dlopen mimo poprawnej instalacji pip.
    """
    predictor = get_aesthetics_predictor()
    if predictor is None:
        return {"PQ": "", "CE": "", "CU": ""}

    audio, sr = sf.read(str(path), always_2d=True, dtype="float32")  # (samples, channels)
    wav = torch.from_numpy(audio.T)  # -> (channels, samples), format oczekiwany przez torchaudio-style API

    result = predictor.forward([{"path": wav, "sample_rate": sr}])[0]
    # rzeczywiste klucze zwracane przez bibliotekę: CE, CU, PC, PQ (skrótowe)
    return {
        "PQ": result.get("PQ", ""),
        "CE": result.get("CE", ""),
        "CU": result.get("CU", ""),
    }


# =============================================================================
# GŁÓWNA PĘTLA EWALUACJI
# =============================================================================

def evaluate_track_stem(
    model_name: str,
    track: str,
    stem: str,
    ref_path: Path,
    est_path: Path,
    inference_time: float | str,
) -> dict:
    if not est_path.exists():
        # model nie obsługuje tego źródła — zgodnie z protokołem (5.0) zaznaczamy i pomijamy
        return {
            "model": model_name,
            "track": track,
            "stem": stem,
            "SDR": "not_supported",
            "SI-SDR": "not_supported",
            "PQ": "not_supported",
            "CE": "not_supported",
            "CU": "not_supported",
            "inference_time_sec": inference_time,
        }

    reference = load_audio(ref_path)
    estimate = load_audio(est_path)

    si_sdr = compute_si_sdr(reference, estimate)
    sdr = compute_sdr_museval(reference, estimate)
    aesthetics = compute_aesthetics(est_path)

    return {
        "model": model_name,
        "track": track,
        "stem": stem,
        "SDR": f"{sdr:.4f}" if sdr is not None else "",
        "SI-SDR": f"{si_sdr:.4f}",
        "PQ": aesthetics["PQ"],
        "CE": aesthetics["CE"],
        "CU": aesthetics["CU"],
        "inference_time_sec": inference_time,
    }


def summarize(rows: list[dict]) -> list[dict]:
    """Agreguje mean/median/std per model+stem dla kolumn numerycznych."""
    numeric_cols = ["SDR", "SI-SDR", "PQ", "CE", "CU"]
    by_stem: dict[str, list[dict]] = {}
    for row in rows:
        by_stem.setdefault(row["stem"], []).append(row)

    summary = []
    for stem, stem_rows in by_stem.items():
        agg = {"stem": stem, "n_tracks": len(stem_rows)}
        for col in numeric_cols:
            values = []
            for r in stem_rows:
                v = r[col]
                if v in ("", "not_supported"):
                    continue
                try:
                    values.append(float(v))
                except (TypeError, ValueError):
                    continue
            if values:
                agg[f"{col}_mean"] = round(statistics.mean(values), 4)
                agg[f"{col}_median"] = round(statistics.median(values), 4)
                agg[f"{col}_std"] = round(statistics.stdev(values), 4) if len(values) > 1 else 0.0
            else:
                agg[f"{col}_mean"] = agg[f"{col}_median"] = agg[f"{col}_std"] = ""
        summary.append(agg)
    return summary


def load_config(config_path: Path) -> dict:
    if not HAS_YAML:
        sys.exit("Podano --config, ale brakuje pakietu 'pyyaml'. Zainstaluj: pip install pyyaml --break-system-packages")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main():
    parser = argparse.ArgumentParser(description="Wspólny evaluator benchmarku separacji źródeł audio.")
    parser.add_argument("--config", type=Path, default=None,
                         help="Opcjonalny plik YAML z parametrami (model_name, outputs_dir, reference_dir, "
                              "inference_times, output, summary_output). Flagi CLI nadpisują wartości z configu.")
    parser.add_argument("--model-name", default="SamAudio", help="Nazwa modelu (domyślnie: SamAudio)")
    parser.add_argument("--outputs-dir", type=Path, default=Path("./samaudio_outputs"),
                         help="Katalog z outputem modelu (domyślnie: ./samaudio_outputs)")
    parser.add_argument("--reference-dir", type=Path, default=Path("./musdb18_test_wav"),
                         help="Katalog z ground truth MUSDB18 (domyślnie: ./musdb18_test_wav)")
    parser.add_argument("--inference-times", type=Path, default=Path("./samaudio_inference_times.json"),
                         help="JSON {track: sekundy} (domyślnie: ./samaudio_inference_times.json)")
    parser.add_argument("--output", type=Path, default=Path("samaudio_results.csv"),
                         help="Ścieżka wyjściowego CSV (domyślnie: samaudio_results.csv)")
    parser.add_argument("--summary-output", type=Path, default=Path("samaudio_summary.csv"),
                         help="Ścieżka zagregowanych statystyk mean/median/std (domyślnie: samaudio_summary.csv)")
    args = parser.parse_args()

    # Plik --config (jeśli podany) może nadpisać powyższe domyślne wartości —
    # ale tylko dla flag, których NIE podano ręcznie w CLI (sys.argv).
    # Domyślne wartości powyżej już są ustawione pod SAM-Audio, więc
    # --config jest opcjonalny, nie wymagany do normalnego działania.
    explicit_flags = set()
    for token in sys.argv[1:]:
        if token.startswith("--"):
            explicit_flags.add(token.split("=")[0])

    config = load_config(args.config) if args.config else {}

    def resolved(flag: str, current_value, config_key: str, caster=lambda v: v):
        if flag in explicit_flags:
            return current_value
        if config_key in config:
            return caster(config[config_key])
        return current_value

    model_name = resolved("--model-name", args.model_name, "model_name")
    outputs_dir = resolved("--outputs-dir", args.outputs_dir, "outputs_dir", Path)
    reference_dir = resolved("--reference-dir", args.reference_dir, "reference_dir", Path)
    inference_times_path = resolved("--inference-times", args.inference_times, "inference_times", Path)
    output_path = resolved("--output", args.output, "output", Path)
    summary_output_path = resolved("--summary-output", args.summary_output, "summary_output", Path)

    if not reference_dir.exists():
        sys.exit(f"Nie znaleziono reference-dir: {reference_dir}")
    if not outputs_dir.exists():
        sys.exit(f"Nie znaleziono outputs-dir: {outputs_dir}")

    args.model_name = model_name
    args.outputs_dir = outputs_dir
    args.reference_dir = reference_dir
    args.inference_times = inference_times_path
    args.output = output_path
    args.summary_output = summary_output_path

    if not HAS_MUSEVAL:
        warnings.warn("museval niezainstalowany — kolumna SDR będzie pusta. pip install museval")
    if not HAS_AESTHETICS:
        warnings.warn("audiobox_aesthetics niezainstalowany — kolumny PQ/CE/CU będą puste. "
                       "pip install audiobox_aesthetics")

    inference_times = {}
    if args.inference_times and args.inference_times.exists():
        inference_times = json.loads(args.inference_times.read_text())

    tracks = find_tracks(args.reference_dir)
    if not tracks:
        sys.exit(f"Brak utworów w {args.reference_dir}")

    rows = []
    for track in tracks:
        ref_track_dir = args.reference_dir / track
        est_track_dir = args.outputs_dir / track
        t_time = inference_times.get(track, "")

        for stem in STEMS:
            ref_path = ref_track_dir / f"{stem}.wav"
            est_path = est_track_dir / f"{stem}.wav"

            if not ref_path.exists():
                # ten stem nie istnieje w ogóle w referencji, pomijamy
                continue

            row = evaluate_track_stem(
                model_name=args.model_name,
                track=track,
                stem=stem,
                ref_path=ref_path,
                est_path=est_path,
                inference_time=t_time,
            )
            rows.append(row)
            print(f"[{args.model_name}] {track}/{stem}: "
                  f"SDR={row['SDR']} SI-SDR={row['SI-SDR']} "
                  f"PQ={row['PQ']} CE={row['CE']} CU={row['CU']}")

    # zapis results.csv — format zgodny z pkt 8.0 protokołu:
    # model | track | stem | SDR | SI-SDR | PQ | CE | CU | inference_time_sec
    fieldnames = ["model", "track", "stem", "SDR", "SI-SDR", "PQ", "CE", "CU", "inference_time_sec"]
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nZapisano {len(rows)} wierszy do {args.output}")

    # opcjonalna agregacja
    if args.summary_output:
        summary_rows = summarize(rows)
        summary_fields = ["stem", "n_tracks"] + [
            f"{c}_{stat}" for c in ["SDR", "SI-SDR", "PQ", "CE", "CU"] for stat in ["mean", "median", "std"]
        ]
        with open(args.summary_output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=summary_fields)
            writer.writeheader()
            writer.writerows(summary_rows)
        print(f"Zapisano statystyki zbiorcze do {args.summary_output}")


if __name__ == "__main__":
    main()
