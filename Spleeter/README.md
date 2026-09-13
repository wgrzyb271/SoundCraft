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
_(do uzupełnienia po ustaleniu 5 utworów)_

### Analiza liczbowa

Poniższe wnioski opierają się wyłącznie na metrykach z `results.csv` (50 utworów × 4 stemy = 200 pomiarów).

#### Statystyki zbiorcze (mean / median / std)

| Stem | SDR mean | SDR median | SDR std | SI-SDR mean | SI-SDR median | SI-SDR std |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| vocals | 6.70 | 6.88 | 2.87 | 5.36 | 6.42 | 5.82 |
| drums | 6.49 | 6.09 | 2.40 | 5.55 | 5.07 | 3.18 |
| bass | 4.81 | 4.60 | 3.03 | 3.11 | 3.05 | 4.15 |
| other | 4.52 | 4.94 | 2.03 | 2.09 | 2.74 | 3.31 |

| Stem | PQ mean | CE mean | CU mean |
| :--- | ---: | ---: | ---: |
| vocals | 6.15 | 4.29 | 5.31 |
| drums | 6.80 | 4.59 | 6.82 |
| bass | 5.83 | 3.36 | 5.73 |
| other | 6.32 | 5.77 | 6.27 |

#### Rankingi źródeł

**Według SDR (jakość separacji):**
1. vocals (6.70)
2. drums (6.49)
3. bass (4.81)
4. other (4.52)

**Według SI-SDR (jakość separacji, skalowanie):**
1. drums (5.55)
2. vocals (5.36)
3. bass (3.11)
4. other (2.09)

**Według PQ (Production Quality):**
1. drums (6.80)
2. other (6.32)
3. vocals (6.15)
4. bass (5.83)

**Według CE (Content Enjoyment):**
1. other (5.77)
2. drums (4.59)
3. vocals (4.29)
4. bass (3.36)

**Według CU (Content Usefulness):**
1. drums (6.82)
2. other (6.27)
3. bass (5.73)
4. vocals (5.31)

#### Kluczowe wnioski

**a) Wokale i perkusja wychodzą najlepiej pod względem separacji.**
- Wokale mają najwyższy SDR (6.70), a perkusja najwyższy SI-SDR (5.55).
- Perkusja ma też najwyższe PQ (6.80) i CU (6.82), co sugeruje, że brzmi najbardziej „użytecznie” i „produkcyjnie”.
- Wokale mają jednak najwyższy std SDR (2.87) i SI-SDR (5.82) – wyniki są bardzo nierówne: w niektórych utworach SDR przekracza 12 dB, w innych spada poniżej 0 dB.

**b) Bass i other są najsłabsze pod względem separacji.**
- Bass ma średni SI-SDR 3.11 przy std 4.15 – to największy rozrzut w całym zbiorze.
- Other ma najniższy SDR (4.52) i najniższy SI-SDR (2.09).
- W praktyce: w wielu utworach bas przenika do „other”, a „other” zawiera resztki wokalu i perkusji.

**c) Metryki percepcji (PQ, CE, CU) NIE pokrywają się z metrykami separacji.**
- „Other” ma najgorszy SI-SDR (2.09), ale najwyższy CE (5.77) i drugi najwyższy CU (6.27).
- „Vocals” ma najwyższy SDR (6.70), ale najniższy CU (5.31).
- To ważna obserwacja: dobra separacja ≠ dobre brzmienie. „Other” może brzmieć przyjemnie, bo zawiera wszystko po trochu, mimo że nie jest dobrze odseparowane.

**d) Drums to najbardziej zbalansowane źródło.**
- Wysokie SDR (6.49), najwyższe SI-SDR (5.55), najwyższe PQ (6.80), najwyższe CU (6.82).
- Niskie std dla PQ (0.55) i CU (0.66) – wyniki są spójne między utworami.

**e) Bass ma najniższe CE (3.36) ze wszystkich źródeł.**
- Oznacza to, że odsłuchowo bas jest najmniej „przyjemny” – prawdopodobnie przez buczenie, zniekształcenia lub przenikanie innych instrumentów.

#### Skrajne przypadki (outliers)

**Najlepsze wyniki SDR (> 10 dB):**

| Utwór | Stem | SDR | SI-SDR |
| :--- | :--- | ---: | ---: |
| Speak Softly – Like Horses | bass | 14.87 | 14.90 |
| Tom McKenzie – Directions | drums | 12.35 | 12.40 |
| PR – Happy Daze | drums | 12.16 | 12.01 |
| Lyndsey Ollard – Catching Up | vocals | 12.04 | 12.54 |
| Sambasevam Shanmugam – Kaathaadi | vocals | 11.11 | 11.59 |
| Mu – Too Bright | drums | 10.98 | 11.60 |
| Side Effects Project – Sing With Me | drums | 10.89 | 10.99 |
| Speak Softly – Broken Man | bass | 10.62 | 10.43 |
| Skelpolu – Resurrection | bass | 10.19 | 9.90 |
| BKS – Too Much | vocals | 10.19 | 10.60 |

**Najgorsze wyniki SDR (< 0 dB):**

| Utwór | Stem | SDR | SI-SDR |
| :--- | :--- | ---: | ---: |
| PR – Happy Daze | vocals | -4.90 | -24.81 |
| The Sunshine Garcia Band – For I Am The Moon | other | -0.66 | -3.20 |

**Uwaga do „PR – Happy Daze / vocals”:** SDR -4.90 i SI-SDR -24.81 to wynik katastrofalny. Estymata wokalu jest gorsza niż zwykłe odtworzenie mieszanki. Prawdopodobnie wokal jest mocno przetworzony efektami lub nakłada się z instrumentami, co myli Spleetera. Co ciekawe, perkusja w tym samym utworze ma SDR 12.16 – jeden z najlepszych wyników w całym zbiorze. Pokazuje to, jak bardzo Spleeter jest wrażliwy na charakter utworu.

**Uwaga do „Skelpolu – Resurrection / vocals”:** SDR 0.24, SI-SDR -12.11 – bardzo słabo. Prawdopodobnie utwór z mocno przetworzonym wokalem albo ekstremalnym metalem, gdzie wokal jest wmiksowany w gitarę.

**Uwaga do „The Sunshine Garcia Band / other”:** SDR -0.66, SI-SDR -3.20 – „other” w tym utworze prawdopodobnie zawiera dużo wokalu i perkusji.

#### Rozrzut wyników per utwór

W wielu utworach widać bardzo duży rozrzut między stemami:

| Utwór | vocals | drums | bass | other | Rozstęp SDR |
| :--- | ---: | ---: | ---: | ---: | ---: |
| PR – Happy Daze | -4.90 | 12.16 | 3.41 | 3.01 | 17.06 dB |
| Skelpolu – Resurrection | 0.24 | 6.38 | 10.19 | 3.10 | 9.95 dB |
| Mu – Too Bright | 6.38 | 10.98 | 2.93 | 3.85 | 8.05 dB |
| Arise – Run Run Run | 5.70 | 1.05 | 1.66 | 0.57 | 5.13 dB |
| AM Contra – Heart Peripheral | 9.76 | 5.13 | -1.05 | 0.73 | 10.81 dB |

**Wniosek:** Spleeter potrafi świetnie wyodrębnić jedno źródło, a kompletnie zawieść na innym w tym samym utworze. Wynika to z tego, że model stosuje wytrenowane wzorce do każdego fragmentu osobno, bez „rozumienia” całości utworu.

#### Czas inferencji

- **Zakres:** 27.58 s (PR – Oh No) do 107.23 s (Girls Under Glass – We Feel Alright)
- **Średnia:** ~68 s/utwór
- **Suma dla 50 utworów:** ~56 minut
- **Rozrzut ponad 4×** między najkrótszym a najdłuższym utworem – wynika głównie z długości utworu i zmiennego obciążenia GPU w Colabie.
- Wszystkie czasy mierzone na Tesla T4 (Colab).

#### Wnioski praktyczne

**Co Spleeter robi dobrze:**
- Wyodrębnianie wokalu w utworach o klasycznej aranżacji (wokal na przodzie, akompaniament z tyłu).
- Separacja perkusji – zwłaszcza w utworach z wyraźnym rytmem.
- Radzi sobie z różnymi gatunkami: rock, pop, elektronika, folk.

**Co Spleeter robi źle:**
- **Bass** – bardzo nierówny, czasem SDR poniżej 0 dB, przenika do other.
- **Other** – najbardziej zanieczyszczone źródło; zawiera resztki wokalu, perkusji i basu.
- **Utwory o gęstej aranżacji** – gdzie wokal jest przetworzony efektami albo mocno wmiksowany w instrumenty (PR – Happy Daze, Skelpolu – Resurrection).
- **Wokale w ciężkich gatunkach** (metal, punk) – SDR 0.24 w Skelpolu.

**Porównanie metryk:**
- SDR i SI-SDR dają spójny obraz rankingu źródeł (drums/vocals > bass > other), ale różnią się w wartościach – SI-SDR jest bardziej wrażliwy na błędy skali.
- PQ, CE, CU nie zastępują SDR/SI-SDR – mierzą co innego. Wysokie PQ nie znaczy, że separacja jest dobra (patrz: other).
- Dla porównania modeli w benchmarku SDR i SI-SDR są kluczowe, a PQ/CE/CU to uzupełnienie.

### Analiza odsłuchowa
_(do uzupełnienia po ustaleniu 5 utworów)_
