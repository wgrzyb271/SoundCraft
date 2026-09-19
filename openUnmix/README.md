# Open-Unmix – benchmark

## Środowisko

* Google Colab
* GPU T4

## Dataset i preprocessing

Do benchmarku wykorzystano testowy zbiór **MUSDB18 obejmujący 50 utworów**. Wszystkie sygnały są stereofoniczne i mają częstotliwość próbkowania **44,1 kHz**.

Jako wejście do Open-Unmix wykorzystywany jest sygnał `mixture`. Pliki `.stem.mp4` są odczytywane za pomocą `stempeg` z częstotliwością 44,1 kHz, a następnie konwertowane do tensora PyTorch.

W zastosowanym pipeline nie wykonywano dodatkowej normalizacji, filtracji ani augmentacji. Utwory nie były dzielone na fragmenty.

Po wykonaniu separacji wygenerowane źródła są zapisywane jako osobne pliki WAV: `vocals.wav`, `drums.wav`, `bass.wav` i `other.wav`. Pliki te są następnie wykorzystywane przez `evaluator.py` do porównania z referencyjnymi źródłami MUSDB18. Utwory źródłowe zostały przygotowane do działania z `evaluator.py` poprzez podzielenie ich również na poszczególne ścieżki WAV (jak powyżej).

Łącznie oceniono **50 utworów × 4 stemy = 200 pomiarów**.

## Metryki

Wyniki obliczono za pomocą wspólnego `evaluator.py`:

* SDR
* SI-SDR
* PQ
* CE
* CU

SDR i SI-SDR służą do oceny jakości separacji względem źródeł referencyjnych. PQ, CE i CU opisują właściwości percepcyjne wygenerowanego audio.

Wyniki dla poszczególnych utworów i stemów znajdują się w `results.csv`, natomiast statystyki zbiorcze (mean/median/std) w `summary_results.csv`.

## Wyniki

### Analiza liczbowa

| Stem   | SDR mean | SDR median | SDR std | SI-SDR mean | SI-SDR median | SI-SDR std |
| :----- | -------: | ---------: | ------: | ----------: | ------------: | ---------: |
| vocals |     6.21 |       6.58 |    2.71 |        4.84 |          6.11 |       5.15 |
| drums  |     6.41 |       5.94 |    2.63 |        5.42 |          5.20 |       3.65 |
| bass   |     4.78 |       4.70 |    3.28 |        3.05 |          3.27 |       4.79 |
| other  |     3.83 |       4.33 |    2.04 |        0.52 |          2.38 |       4.94 |

| Stem   | PQ mean | PQ median | PQ std | CE mean | CE median | CE std | CU mean | CU median | CU std |
| :----- | ------: | --------: | -----: | ------: | --------: | -----: | ------: | --------: | -----: |
| vocals |    6.52 |      6.67 |   0.49 |    4.87 |      5.07 |   0.96 |    5.78 |      5.96 |   0.67 |
| drums  |    6.76 |      6.68 |   0.50 |    5.02 |      5.12 |   0.90 |    6.87 |      6.96 |   0.51 |
| bass   |    5.49 |      5.58 |   0.58 |    3.43 |      3.36 |   0.47 |    5.25 |      5.31 |   0.49 |
| other  |    6.50 |      6.56 |   0.67 |    5.88 |      6.31 |   1.05 |    6.47 |      6.67 |   0.57 |

Wyniki SDR i SI-SDR pokazują, że jakość separacji jest zależna od rodzaju źródła i charakteryzuje się różną zmiennością między utworami. Duże odchylenia standardowe, szczególnie dla SI-SDR `bass` i `other`, wskazują na niejednorodne działanie modelu dla poszczególnych nagrań. Metryki AudioBox-Aesthetics dodatkowo pokazują jakość dźwięku po separacji, która nie zawsze odpowiada bezpośrednio wynikom SDR i SI-SDR.

## Analiza jakościowa

Do analizy jakościowej wykorzystano 5 utworów:

* Timboz – *Pony*
* Skelpolu – *Resurrection*
* Side Effects Project – *Sing With Me*
* Girls Under Glass – *We Feel Alright*
* Al James – *Schoolboy Facination*

Odsłuch pozwala ocenić obecność artefaktów, przecieków innych źródeł oraz utraty części separowanego sygnału. Największe różnice między wynikami występują zależnie od charakterystyki utworu i rodzaju źródła. Szczególnie istotna jest ocena ścieżek `vocals` i `other`, gdzie błędy separacji są łatwo zauważalne podczas odsłuchu.

## Podsumowanie

Open-Unmix najlepiej radzi sobie z separacją perkusji i wokalu, dla których uzyskano najwyższe średnie wartości SDR i SI-SDR. Separacja basu jest bardziej zależna od konkretnego utworu, natomiast największe problemy występują dla ścieżki `other`, ponieważ w zależności od gatunku utworu jej charakter będzie znacząco się różnił.
