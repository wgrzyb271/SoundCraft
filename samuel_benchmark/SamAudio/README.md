# SamAudio

## Opis modelu
TODO: krótki opis modelu i architektury.

## Wersja modelu
`facebook/sam-audio-small`
Rewizja (sha): `20b65f56888142eebe7c37448c6f6b3b32600e9b`
Ostatnia modyfikacja na HF Hub: 2025-12-30 19:52:21 UTC

## Dataset
MUSDB18 (test set, 50 utworów), 44.1kHz, stereo. https://sigsep.github.io/datasets/musdb.html

Benchmark w tym przebiegu wykonano na 5 wybranych utworach:
- Timboz - Pony
- Skelpolu - Resurrection
- Side Effects Project - Sing With Me
- Girls Under Glass - We Feel Alright
- Al James - Schoolboy Facination

## Preprocessing
TODO: sample rate, kanały, normalizacja, resampling, dzielenie na fragmenty
(patrz komentarz na górze run_*_benchmark.py użytego dla tego modelu jako
punkt startowy).

Uwaga: model zwraca audio mono — na potrzeby ewaluacji względem stereo
referencji MUSDB18, pojedynczy kanał był duplikowany na L/R (patrz
run_samaudio_benchmark.py). To uproszczenie, nie prawdziwa separacja stereo.

## Zastosowane metryki jakości separacji
SDR, SI-SDR (museval / evaluator.py), AudioBox-Aesthetics: PQ, CE, CU.

## Wyniki

Pełne wyniki per utwór/stem: `samaudio_results.csv` (20 wierszy — 5 utworów × 4 stemy)
Zagregowane statystyki: `samaudio_summary.csv`

| Stem | n | SDR (mean / median / std) | SI-SDR (mean / median / std) | PQ (mean) | CE (mean) | CU (mean) |
|---|---|---|---|---|---|---|
| vocals | 5 | -4.86 / -6.07 / 4.42 | -11.43 / -14.38 / 5.53 | 6.17 | 4.07 | 5.54 |
| drums | 5 | 0.34 / 0.19 / 2.33 | -4.68 / -6.96 / 4.48 | 6.05 | 2.86 | 5.41 |
| bass | 5 | 1.61 / 2.30 / 1.60 | -15.65 / -1.18 / 21.28 | 5.17 | 2.78 | 4.35 |
| other | 5 | -3.07 / -2.51 / 3.28 | -12.32 / -11.57 / 8.90 | 6.06 | 3.24 | 5.39 |

> Uwaga do SI-SDR dla `bass`: bardzo wysokie odchylenie standardowe
> (21.28) przy jednocześnie dodatnim SDR sugeruje pojedynczy skrajny
> outlier w tej piątce, a nie spójne zachowanie modelu — warto sprawdzić
> `samaudio_results.csv` per-utwór przed wyciąganiem wniosków o jakości
> separacji basu jako takiej.

## Problemy
TODO: napotkane problemy podczas benchmarku.

(Kontekst techniczny, jeśli przydatny do tej sekcji: podczas przygotowania
środowiska napotkano i rozwiązano m.in. niezgodność wersji
`huggingface_hub`/`transformers`, fragmentację pamięci CUDA przy
dekodowaniu kodeka audio, oraz niekompletne przygotowanie części utworów
referencyjnych z MUSDB18 — szczegóły w manualu projektu.)

## Wnioski
TODO: krótkie wnioski jakościowe (pkt 9.0 protokołu — artefakty, przecieki
innych instrumentów, utrata dźwięku, distortion, różnice między źródłami).

Wstępna obserwacja z samych metryk liczbowych (wymaga weryfikacji
słuchowej przed wpisaniem na stałe):
- `bass` ma najwyższe średnie i medianowe SDR (1.61 / 2.30) — najlepiej
  separowany stem w tym zestawie.
- `vocals` i `other` mają wyraźnie ujemne SDR (odpowiednio -4.86 i -3.07
  średnio), sugerując istotne przecieki innych źródeł lub artefakty w
  separacji tych stemów.
- SI-SDR jest ujemne dla wszystkich stemów średnio, co przy dodatnim SDR
  dla `drums`/`bass` wskazuje na możliwe niedopasowanie skali/poziomu
  głośności między estymatą a referencją, a nie tylko błędy w samej
  treści separowanego sygnału — warto to zweryfikować.
