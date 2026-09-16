#!/usr/bin/env python3
"""
package_results.py — składa finalną strukturę katalogu modelu zgodną
z pkt 9.0 protokołu:

<model_name>/
├── README.md          (piszesz ręcznie / uzupełniasz szablon poniżej)
├── results.csv         (z evaluator.py --output)
├── audio/
│   ├── track_001/{mixture,vocals,drums,bass,other}.wav
│   ├── ...
│   └── track_005/...

Kopiuje TYLKO 5 wspólnie ustalonych utworów (pkt 5.0 protokołu — audio/
ma zawierać wyłącznie te 5, reszta test setu istnieje tylko jako liczby
w results.csv, żeby nie zapychać repo).

-----------------------------------------------------------------------------
UŻYCIE
-----------------------------------------------------------------------------
python package_results.py \
    --model-name SamAudio \
    --outputs-dir ./samaudio_outputs \
    --results-csv ./samaudio_results.csv \
    --selected-tracks track_003 track_017 track_022 track_035 track_048 \
    --dest ./SamAudio

Lista --selected-tracks MUSI być identyczna dla wszystkich devów w zespole
(pkt 5.0: "5 wspólnie wybranych utworów") — nazwy katalogów odpowiadają
tym z reference-dir wygenerowanego przez prepare_reference.py.
"""

import argparse
import shutil
import sys
from pathlib import Path

README_TEMPLATE = """# {model_name}

## Opis modelu
TODO: krótki opis modelu i architektury.

## Wersja modelu
TODO: konkretna wersja / checkpoint / commit hash.

## Dataset
MUSDB18 (test set, 50 utworów), 44.1kHz, stereo. https://sigsep.github.io/datasets/musdb.html

## Preprocessing
TODO: sample rate, kanały, normalizacja, resampling, dzielenie na fragmenty
(patrz komentarz na górze run_*_benchmark.py użytego dla tego modelu jako
punkt startowy).

## Zastosowane metryki jakości separacji
SDR, SI-SDR (museval / evaluator.py), AudioBox-Aesthetics: PQ, CE, CU.

## Wyniki
Pełne wyniki per utwór/stem: results.csv
Zagregowane statystyki (mean/median/std): TODO dołącz summary.csv jeśli generowany.

## Problemy
TODO: napotkane problemy podczas benchmarku.

## Wnioski
TODO: krótkie wnioski jakościowe (pkt 9.0 protokołu — artefakty, przecieki
innych instrumentów, utrata dźwięku, distortion, różnice między źródłami).
"""


def main():
    parser = argparse.ArgumentParser(description="Złóż finalną strukturę katalogu modelu (pkt 9.0 protokołu).")
    parser.add_argument("--model-name", required=True, help="np. Spleeter, SamAudio")
    parser.add_argument("--outputs-dir", type=Path, required=True, help="Katalog z outputem modelu (wszystkie utwory)")
    parser.add_argument("--results-csv", type=Path, required=True, help="results.csv z evaluator.py")
    parser.add_argument("--selected-tracks", nargs=5, required=True,
                         help="Dokładnie 5 nazw katalogów utworów (wspólnie ustalonych w zespole)")
    parser.add_argument("--dest", type=Path, required=True, help="Docelowy katalog <model_name>/")
    args = parser.parse_args()

    if not args.results_csv.exists():
        sys.exit(f"Nie znaleziono {args.results_csv} — uruchom najpierw evaluator.py")

    dest = args.dest
    audio_dest = dest / "audio"
    audio_dest.mkdir(parents=True, exist_ok=True)

    shutil.copy(args.results_csv, dest / "results.csv")

    readme_path = dest / "README.md"
    if not readme_path.exists():
        readme_path.write_text(README_TEMPLATE.format(model_name=args.model_name), encoding="utf-8")
        print(f"Utworzono szablon README.md — UZUPEŁNIJ pola TODO ręcznie: {readme_path}")
    else:
        print(f"README.md już istnieje, nie nadpisuję: {readme_path}")

    for track in args.selected_tracks:
        src_track_dir = args.outputs_dir / track
        if not src_track_dir.exists():
            print(f"⚠️  Brak {src_track_dir} w outputs-dir — pomijam (sprawdź nazwę utworu).")
            continue
        dst_track_dir = audio_dest / track
        if dst_track_dir.exists():
            shutil.rmtree(dst_track_dir)
        shutil.copytree(src_track_dir, dst_track_dir)
        print(f"Skopiowano audio: {track}")

    print(f"\n✅ Struktura gotowa w {dest}/")
    print("   Pamiętaj uzupełnić README.md przed commitem do repo (pkt 9.0 protokołu).")


if __name__ == "__main__":
    main()
