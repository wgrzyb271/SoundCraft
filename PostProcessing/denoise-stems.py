#!/usr/bin/env python3
"""
denoise_stem.py — narzędzie MCP do odszumiania wyseparowanych ścieżek audio.

Narzędzie wykorzystuje spectral gating (biblioteka noisereduce) do redukcji
szumu tła w pojedynczych ścieżkach po separacji.

UWAGA - WAŻNE OGRANICZENIE:
    Testy na ścieżkach po Spleeterze (MUSDB18 test set, 5 utworów × 4 stemy)
    wykazały, że klasyczny spectral gating:
    - redukuje szum tła (stacjonarny),
    - NIE USUWA artefaktów separacji (puszkowości wokalu, przenikania
       innych instrumentów).
    
    Artefakty po separacji nie są szumem stacjonarnym - są powiązane
    z sygnałem muzycznym, więc bramka widmowa ich nie usuwa. Potwierdza to
    hipotezę z sekcji 4.3 dokumentu architektury.
    

Wymóg techniczny:
    noisereduce oczekuje audio w formacie (kanały, próbki). Ponieważ
    soundfile zwraca (próbki, kanały), w funkcji jest transpozycja.
    Bez niej występuje OOM nawet przy 30 GB RAM (biblioteka próbuje
    przetworzyć miliony "kanałów").

Użycie:
    denoise_stem("vocals.wav", "vocals_denoised.wav", prop_decrease=0.7)

"""

import os
import numpy as np
import soundfile as sf
import noisereduce as nr
from typing import Optional


def denoise_stem(
    input_path: str,
    output_path: str,
    prop_decrease: float = 0.8,
    stationary: bool = False,
    n_fft: int = 2048,
    chunk_seconds: int = 10,
) -> dict:
    """
    Odszumianie metodą spectral gating (noisereduce).

    Args:
        input_path: ścieżka do pliku WAV (po separacji)
        output_path: ścieżka wyjściowa (WAV)
        prop_decrease: stopień redukcji (0.0–1.0). Zalecane 0.5–0.7.
            0.0 = brak redukcji, 1.0 = maksymalna redukcja (ryzyko zniekształceń)
        stationary: czy szum jest stacjonarny (False dla zmiennego w czasie)
        n_fft: rozmiar okna FFT
        chunk_seconds: długość kawałka do przetwarzania (unika OOM)

    Returns:
        dict z raportem: {"status": "SUCCESS", "output_path": ..., "details": ...}
        lub {"status": "FAILED", "error": ..., "details": ...}
    """
    try:
        if not os.path.exists(input_path):
            return {"status": "FAILED", "error": "FILE_NOT_FOUND",
                    "details": f"Nie znaleziono pliku: {input_path}"}

        audio, sr = sf.read(input_path, always_2d=True, dtype="float32")
        audio_t = audio.T  # (channels, samples) — wymóg noisereduce

        reduced = nr.reduce_noise(
            y=audio_t,
            sr=sr,
            stationary=stationary,
            prop_decrease=prop_decrease,
            n_fft=n_fft,
            chunk_size=int(chunk_seconds * sr),
        )

        sf.write(output_path, reduced.T, sr, subtype="PCM_16")

        return {
            "status": "SUCCESS",
            "output_path": output_path,
            "sample_rate": sr,
            "duration_sec": round(audio.shape[0] / sr, 2),
            "params": {
                "prop_decrease": prop_decrease,
                "stationary": stationary,
                "n_fft": n_fft,
                "chunk_seconds": chunk_seconds,
            },
            "details": "Odszumiono metodą spectral gating (noisereduce). "
                       "UWAGA: redukuje szum tła, nie usuwa artefaktów separacji."
        }

    except Exception as e:
        return {"status": "FAILED", "error": "RUNTIME_ERROR",
                "details": str(e)}


if __name__ == "__main__":
    # Przykład użycia - do celów testowych.
    import argparse

    parser = argparse.ArgumentParser(description="Odszumianie pojedynczego stema.")
    parser.add_argument("--input", required=True, help="Ścieżka do pliku WAV")
    parser.add_argument("--output", default="denoised.wav", help="Plik wyjściowy")
    parser.add_argument("--prop-decrease", type=float, default=0.7,
                        help="Stopień redukcji (0.0–1.0). Zalecane 0.5–0.7.")
    parser.add_argument("--stationary", action="store_true",
                        help="Szum stacjonarny (domyślnie False)")
    parser.add_argument("--chunk-seconds", type=int, default=10,
                        help="Długość kawałka w sekundach (unika OOM)")
    args = parser.parse_args()

    result = denoise_stem(
        input_path=args.input,
        output_path=args.output,
        prop_decrease=args.prop_decrease,
        stationary=args.stationary,
        chunk_seconds=args.chunk_seconds,
    )
    print(result)