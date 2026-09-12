#!/usr/bin/env python3
"""
evaluator.py — wspólny skrypt ewaluacyjny dla benchmarku modeli separacji źródeł audio
(zgodnie z benchmark-protocol-v1.0)
"""

import argparse
import csv
import json
import statistics
import sys
import warnings
from pathlib import Path

import numpy as np

try:
    import yaml
except ImportError:
    sys.exit("Brakuje pakietu 'PyYAML'. Zainstaluj: pip install pyyaml --break-system-packages")

try:
    import soundfile as sf
except ImportError:
    sys.exit("Brakuje pakietu 'soundfile'. Zainstaluj: pip install soundfile --break-system-packages")

# --- opcjonalne zależności ---------------------------------------------------

try:
    import museval
    HAS_MUSEVAL = True
except ImportError:
    HAS_MUSEVAL = False

try:
    from audiobox_aesthetics.infer import initialize_predictor
    HAS_AESTHETICS = True
except ImportError:
    HAS_AESTHETICS = False


STEMS = ["vocals", "drums", "bass", "other"]
TARGET_SR = 44100


# =============================================================================
# I/O
# =============================================================================

def load_audio(path: Path) -> np.ndarray:
    audio, sr = sf.read(str(path), always_2d=True, dtype="float32")
    if sr != TARGET_SR:
        warnings.warn(
            f"{path}: sample rate {sr} != {TARGET_SR}. "
            "Resampling powinien być wykonany PRZED ewaluacją."
        )
    return audio


def find_tracks(reference_dir: Path) -> list[str]:
    return sorted(p.name for p in reference_dir.iterdir() if p.is_dir())


def align_length(ref: np.ndarray, est: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n = min(len(ref), len(est))
    return ref[:n], est[:n]


# =============================================================================
# METRYKI
# =============================================================================

def compute_si_sdr(reference: np.ndarray, estimate: np.ndarray, eps: float = 1e-8) -> float:
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
    if not HAS_MUSEVAL:
        return None

    ref, est = align_length(reference, estimate)
    ref_ = ref[np.newaxis, ...]
    est_ = est[np.newaxis, ...]
    sdr, _, _, _ = museval.evaluate(ref_, est_, win=ref_.shape[1], hop=ref_.shape[1])
    return float(np.nanmedian(sdr))


_aesthetics_predictor = None

def get_aesthetics_predictor():
    global _aesthetics_predictor
    if _aesthetics_predictor is None and HAS_AESTHETICS:
        _aesthetics_predictor = initialize_predictor()
    return _aesthetics_predictor


def compute_aesthetics(path: Path) -> dict:
    predictor = get_aesthetics_predictor()
    if predictor is None:
        return {"PQ": "", "CE": "", "CU": ""}

    result = predictor.forward([{"path": str(path)}])[0]
    return {
        "PQ": result.get("Production_Quality", ""),
        "CE": result.get("Content_Enjoyment", ""),
        "CU": result.get("Content_Usefulness", ""),
    }


# =============================================================================
# EWALUACJA I PODSUMOWANIE
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


def main():
    parser = argparse.ArgumentParser(description="Evaluator benchmarku separacji źródeł audio.")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"), help="Ścieżka do pliku YAML z konfiguracją")
    parser.add_argument("--model-name", help="Nazwa modelu, np. Demucs")
    parser.add_argument("--outputs-dir", type=Path, help="Katalog z outputem modelu")
    parser.add_argument("--reference-dir", type=Path, help="Katalog z ground truth")
    parser.add_argument("--inference-times", type=Path, help="JSON {track: sekundy}")
    parser.add_argument("--output", type=Path, help="Ścieżka wyjściowego CSV")
    parser.add_argument("--summary-output", type=Path, help="Ścieżka do wyników zagregowanych")
    args = parser.parse_args()

    # Wczytywanie konfiguracji z pliku YAML
    config = {}
    if args.config.exists():
        with open(args.config, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    # Domyślne wartości: Flag CLI > Konfiguracja YAML > Wartość Domyślna
    model_name = args.model_name or config.get("model_name")
    outputs_dir = args.outputs_dir or (Path(config["outputs_dir"]) if "outputs_dir" in config else None)
    reference_dir = args.reference_dir or (Path(config["reference_dir"]) if "reference_dir" in config else None)

    inf_times_cfg = args.inference_times or config.get("inference_times")
    inference_times_path = Path(inf_times_cfg) if inf_times_cfg else None

    output_path = args.output or Path(config.get("output", "results.csv"))

    sum_out_cfg = args.summary_output or config.get("summary_output")
    summary_output_path = Path(sum_out_cfg) if sum_out_cfg else None

    # Walidacja
    if not model_name or not outputs_dir or not reference_dir:
        sys.exit("Błąd: Wymagane argumenty (model_name, outputs_dir, reference_dir) muszą być podane w CLI lub w pliku YAML.")

    if not reference_dir.exists():
        sys.exit(f"Nie znaleziono reference-dir: {reference_dir}")
    if not outputs_dir.exists():
        sys.exit(f"Nie znaleziono outputs-dir: {outputs_dir}")

    if not HAS_MUSEVAL:
        warnings.warn("museval niezainstalowany — kolumna SDR będzie pusta.")
    if not HAS_AESTHETICS:
        warnings.warn("audiobox_aesthetics niezainstalowany — kolumny PQ/CE/CU będą puste.")

    inference_times = {}
    if inference_times_path and inference_times_path.exists():
        inference_times = json.loads(inference_times_path.read_text())

    tracks = find_tracks(reference_dir)
    if not tracks:
        sys.exit(f"Brak utworów w {reference_dir}")

    rows = []
    for track in tracks:
        ref_track_dir = reference_dir / track
        est_track_dir = outputs_dir / track
        t_time = inference_times.get(track, "")

        for stem in STEMS:
            ref_path = ref_track_dir / f"{stem}.wav"
            est_path = est_track_dir / f"{stem}.wav"

            if not ref_path.exists():
                continue

            row = evaluate_track_stem(
                model_name=model_name,
                track=track,
                stem=stem,
                ref_path=ref_path,
                est_path=est_path,
                inference_time=t_time,
            )
            rows.append(row)
            print(f"[{model_name}] {track}/{stem}: SDR={row['SDR']} SI-SDR={row['SI-SDR']}")

    fieldnames = ["model", "track", "stem", "SDR", "SI-SDR", "PQ", "CE", "CU", "inference_time_sec"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nZapisano {len(rows)} wierszy do {output_path}")

    if summary_output_path:
        summary_rows = summarize(rows)
        summary_fields = ["stem", "n_tracks"] + [
            f"{c}_{stat}" for c in ["SDR", "SI-SDR", "PQ", "CE", "CU"] for stat in ["mean", "median", "std"]
        ]
        with open(summary_output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=summary_fields)
            writer.writeheader()
            writer.writerows(summary_rows)
        print(f"Zapisano statystyki zbiorcze do {summary_output_path}")


if __name__ == "__main__":
    main()