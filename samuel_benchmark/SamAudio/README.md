# SamAudio

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
