#!/usr/bin/env python3
"""
stitch_stems.py — narzędzie MCP do remiksu wyseparowanych ścieżek audio.

Narzędzie deterministyczne: przyjmuje ścieżki do stemów, sumuje je
z opcjonalnymi wagami, normalizuje wynik i zapisuje do pliku WAV.

Użycie:
    # Pełny remiks (wszystkie stemy ×1.0)
    stitch_stems(
        stems_paths={"vocals": "v.wav", "drums": "d.wav",
                     "bass": "b.wav", "other": "o.wav"},
        output_path="remix.wav",
    )

    # Karaoke (usuń wokal)
    stitch_stems(stems, "karaoke.wav",
                 weights={"vocals": 0.0, "drums": 1.0,
                          "bass": 1.0, "other": 1.0})

    # Wokal głośniej
    stitch_stems(stems, "vocal_boost.wav",
                 weights={"vocals": 1.5, "drums": 0.9,
                          "bass": 0.9, "other": 0.9})

Konwencja nazewnictwa wag:
    0.0  = wyciszony
    1.0  = bez zmian
    >1.0 = głośniej (może wymagać normalizacji)

"""

import os
import numpy as np
import soundfile as sf
from typing import Optional


def stitch_stems(
    stems_paths: dict,
    output_path: str,
    weights: Optional[dict] = None,
    normalize: bool = True,
    target_peak: float = 0.99,
) -> dict:
    """
    Skleja audio z powrotem ze stemów (remix).

    Args:
        stems_paths: dict, np. {"vocals": "path.wav", "drums": "path.wav", ...}
        output_path: ścieżka wyjściowa (WAV)
        weights: opcjonalne wagi per stem, np. {"vocals": 1.5, "drums": 0.8}
        normalize: czy normalizować peak do target_peak
        target_peak: docelowy peak (domyślnie 0.99, żeby uniknąć clippingu)

    Returns:
        dict z raportem: {"status": "SUCCESS", "output_path": ..., "details": ...}
        lub {"status": "FAILED", "error": ..., "details": ...}
    """
    try:
        if not stems_paths:
            return {"status": "FAILED", "error": "EMPTY_INPUT",
                    "details": "Brak ścieżek stemów do sklejenia."}

        if weights is None:
            weights = {k: 1.0 for k in stems_paths}

        audios = {}
        sample_rates = set()
        for stem, path in stems_paths.items():
            if not os.path.exists(path):
                return {"status": "FAILED", "error": "FILE_NOT_FOUND",
                        "details": f"Nie znaleziono pliku: {path}"}

            audio, sr = sf.read(path, always_2d=True, dtype="float32")
            audios[stem] = audio * weights.get(stem, 1.0)
            sample_rates.add(sr)

        if len(sample_rates) > 1:
            return {"status": "FAILED", "error": "SAMPLE_RATE_MISMATCH",
                    "details": f"Różne sample rate: {sample_rates}"}

        sr = sample_rates.pop()

        min_len = min(a.shape[0] for a in audios.values())
        audios = {k: v[:min_len] for k, v in audios.items()}
        mix = sum(audios.values())

        peak = float(np.max(np.abs(mix)))
        if normalize and peak > target_peak:
            mix = mix * (target_peak / peak)

        sf.write(output_path, mix, sr, subtype="PCM_16")

        return {
            "status": "SUCCESS",
            "output_path": output_path,
            "sample_rate": sr,
            "duration_sec": round(min_len / sr, 2),
            "stems_used": list(stems_paths.keys()),
            "weights": weights,
            "original_peak": round(peak, 4),
            "details": f"Sklejono {len(stems_paths)} stemów "
                       f"({min_len} próbek, {sr} Hz)."
        }

    except Exception as e:
        return {"status": "FAILED", "error": "RUNTIME_ERROR",
                "details": str(e)}


if __name__ == "__main__":
    # Przykład użycia - do celów testowych.
    import argparse

    parser = argparse.ArgumentParser(description="Remix wyseparowanych stemów.")
    parser.add_argument("--vocals", required=True, help="Ścieżka do vocals.wav")
    parser.add_argument("--drums", required=True, help="Ścieżka do drums.wav")
    parser.add_argument("--bass", required=True, help="Ścieżka do bass.wav")
    parser.add_argument("--other", required=True, help="Ścieżka do other.wav")
    parser.add_argument("--output", default="remix.wav", help="Plik wyjściowy")
    parser.add_argument("--w-vocals", type=float, default=1.0, help="Waga vocals")
    parser.add_argument("--w-drums", type=float, default=1.0, help="Waga drums")
    parser.add_argument("--w-bass", type=float, default=1.0, help="Waga bass")
    parser.add_argument("--w-other", type=float, default=1.0, help="Waga other")
    args = parser.parse_args()

    result = stitch_stems(
        stems_paths={
            "vocals": args.vocals,
            "drums": args.drums,
            "bass": args.bass,
            "other": args.other,
        },
        output_path=args.output,
        weights={
            "vocals": args.w_vocals,
            "drums": args.w_drums,
            "bass": args.w_bass,
            "other": args.w_other,
        },
    )
    print(result)