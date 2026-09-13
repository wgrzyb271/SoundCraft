# Spleeter – benchmark

## Informacje o modelu
- **Nazwa**: Spleeter
- **Wersja**: 2.4.2
- **Repozytorium**: https://github.com/deezer/spleeter
- **Konfiguracja**: `spleeter:4stems` (vocals, drums, bass, other)
- **Obsługiwane audio**: stereo, 44.1 kHz

## Środowisko
- Google Colab
- GPU: Tesla T4
- Python 3.9 (środowisko `spleeter_env` dla modelu)
- Python 3.11 (środowisko bazowe dla evaluatora)
- museval 0.4.1
- audiobox_aesthetics 0.0.4

## Preprocessing
- Sample rate: 44.1 kHz (bez resamplingu – MUSDB18 już jest 44.1 kHz)
- Liczba kanałów: 2 (stereo, bez zmian)
- Format wejściowy: WAV (zapisany przez `soundfile`)
- Normalizacja: brak
- Dzielenie na fragmenty: brak – całe utwory

## Metryki
Obliczone za pomocą `evaluator.py` z repozytorium grupy:
- SDR (museval)
- SI-SDR (własna implementacja)
- PQ, CE, CU (audiobox_aesthetics)

Wyniki per utwór/stem: `results.csv`  
Agregaty (mean/median/std): `summary_results.csv`

## Analiza jakościowa

### Wybrane utwory
- track_001:
- track_002:
- track_003:
- track_004:
- track_005:

### Obserwacje
- **Wokale**:
- **Perkusja**:
- **Bass**:
- **Other**:
- **Ogólne artefakty**:
- **Utrata dźwięku**:

## Uwagi
- Benchmark przeprowadzony zgodnie z `benchmark-protocol-v1.0`.
- Czas inferencji mierzony na GPU w Colabie.
- Metryki PQ/CE/CU obliczone z użyciem `audiobox_aesthetics`.
- Czasy inferencji: 55–100 s/utwór (różnice wynikają z długości utworów
  i zmiennego obciążenia GPU w Colabie)
