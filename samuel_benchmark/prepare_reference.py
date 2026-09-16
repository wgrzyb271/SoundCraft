#!/usr/bin/env python3
"""
prepare_reference.py — jednorazowy eksport MUSDB18 (test set) do WAV-ów.

WAŻNE: to skrypt WSPÓLNY dla całego zespołu — uruchamia się GO RAZ (najlepiej
przez jedną osobę albo wspólnie, na tym samym pobranym MUSDB18), a wynikowy
reference-dir/ jest potem współdzielony przez wszystkich devów. Zgodnie z
protokołem pkt 3.0 ("Wszyscy korzystają z tego samego test setu") — nie
generuj swojej własnej kopii z osobnego pobrania datasetu, tylko użyj
tego samego reference-dir/ co reszta zespołu.

Co robi:
1. Wczytuje MUSDB18 (subset "test", czyli 50 utworów) przez pakiet `musdb`.
2. Dla każdego utworu zapisuje mixture.wav + vocals/drums/bass/other.wav
   (44.1kHz, stereo, float32) do reference-dir/<safe_track_name>/.
3. Zapisuje track_names.json — mapowanie bezpiecznej nazwy katalogu na
   oryginalną nazwę utworu w MUSDB18 (przydatne w README / raportach).

mixture.wav w reference-dir/ jest też WEJŚCIEM dla modeli (run_*_benchmark.py
czytają je stamtąd) — dzięki temu wszystkie modele dostają identyczny input,
zgodnie z pkt 3.0/4.0 protokołu.

-----------------------------------------------------------------------------
ZALEŻNOŚCI
-----------------------------------------------------------------------------
pip install musdb soundfile numpy --break-system-packages

`musdb` domyślnie dekoduje oryginalne pliki .stem.mp4 przez `stempeg`, co
wymaga zainstalowanego systemowo ffmpeg. Jeśli macie wersję MUSDB18 już
rozpakowaną jako WAV (is_wav=True), użyjcie flagi --is-wav.

-----------------------------------------------------------------------------
UŻYCIE
-----------------------------------------------------------------------------
python prepare_reference.py \
    --musdb-root /sciezka/do/musdb18 \
    --reference-dir ./musdb18_test_wav \
    [--is-wav] [--limit 5]
"""

import argparse
import json
import sys
from pathlib import Path

from benchmark_common import STEMS, TARGET_SR, sanitize_track_name, save_wav, ensure_dir

try:
    import musdb
except ImportError:
    sys.exit("Brakuje pakietu 'musdb'. Zainstaluj: pip install musdb --break-system-packages")


def main():
    parser = argparse.ArgumentParser(description="Eksport MUSDB18 test set do WAV (reference-dir).")
    parser.add_argument("--musdb-root", type=Path, required=True, help="Katalog z pobranym MUSDB18")
    parser.add_argument("--reference-dir", type=Path, required=True, help="Docelowy katalog WAV-ów")
    parser.add_argument("--subset", default="test", choices=["test", "train"],
                         help="Zgodnie z protokołem używamy 'test' (domyślnie)")
    parser.add_argument("--is-wav", action="store_true",
                         help="Ustaw, jeśli MUSDB18 jest już rozpakowany jako WAV (bez stempeg/ffmpeg)")
    parser.add_argument("--limit", type=int, default=None,
                         help="Ogranicz do N pierwszych utworów (przydatne do szybkiego testu)")
    args = parser.parse_args()

    mus = musdb.DB(root=str(args.musdb_root), subsets=args.subset, is_wav=args.is_wav)
    tracks = list(mus)
    if not tracks:
        sys.exit(f"musdb nie znalazł żadnych utworów w {args.musdb_root} (subset={args.subset})")
    if args.limit:
        tracks = tracks[: args.limit]

    ensure_dir(args.reference_dir)
    name_map = {}

    for i, track in enumerate(tracks, 1):
        safe_name = sanitize_track_name(track.name)
        # Zabezpieczenie przed kolizją nazw po sanityzacji.
        if safe_name in name_map:
            safe_name = f"{safe_name}_{i:03d}"
        name_map[safe_name] = track.name

        track_dir = args.reference_dir / safe_name
        sr = int(track.rate)
        if sr != TARGET_SR:
            print(f"⚠️  {track.name}: sample rate {sr} != {TARGET_SR} — sprawdź wersję datasetu.")

        save_wav(track_dir / "mixture.wav", track.audio.astype("float32"), sr)
        for stem in STEMS:
            target = track.targets.get(stem)
            if target is None:
                print(f"⚠️  {track.name}: brak stemu '{stem}' w MUSDB18 (nieoczekiwane).")
                continue
            save_wav(track_dir / f"{stem}.wav", target.audio.astype("float32"), sr)

        print(f"[{i}/{len(tracks)}] {track.name} -> {track_dir}")

    (args.reference_dir / "track_names.json").write_text(
        json.dumps(name_map, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n✅ Gotowe. {len(tracks)} utworów zapisanych do {args.reference_dir}")
    print(f"   Mapowanie nazw: {args.reference_dir / 'track_names.json'}")


if __name__ == "__main__":
    main()
