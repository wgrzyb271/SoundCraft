# BS-RoFormer

## Informacje o modelu

* **Nazwa**: BS-RoFormer
* **Checkpoint**: `model\_bs\_roformer\_ep\_17\_sdr\_9.6568.ckpt`
* **Konfiguracja**: `config\_bs\_roformer\_384\_8\_2\_485100.yaml`
* **Liczba stemów**: 4 (`vocals`, `drums`, `bass`, `other`)
* **Obsługiwane audio**: stereo, 44.1 kHz
* **Architektura**: Band-Split RoFormer
* **Tryb inferencji**: GPU, mixed precision FP16
* **Flash Attention**: włączone

```

## odowisko

Inferencja modelu została wykonana na infrastrukturze WCSS przy użyciu SLURM.

* GPU: **NVIDIA H100**
* Python: **3.10.4**
* PyTorch: **2.14.0+cu130**
* CUDA używana przez PyTorch: **13.0**
* Partycja GPU: `lem-gpu-short`
* Model uruchamiany w osobnym środowisku `.venv`

Evaluator został uruchomiony w oddzielnym środowisku:

* Python: **3.12.3**
* `museval`
* `audiobox\_aesthetics`
* `soundfile`
* `numpy`
* `pyyaml`
* FFmpeg / FFprobe dostępne przez moduły WCSS

Dla evaluatora konieczne było zwiększenie pamięci joba z 16 GB do 32 GB ze względu na rosnące zużycie RAM podczas obliczania metryk.

## Dataset

Do benchmarku wykorzystano testowy zbiór **MUSDB18**:

* 50 utworów
* 4 źródła referencyjne:

  * `vocals`
  * `drums`
  * `bass`
  * `other`

Ground truth został wyodrębniony z odpowiednich strumieni MP4 i zapisany w strukturze:

```text
reference-dir/
├── track\_001/
│   ├── vocals.wav
│   ├── drums.wav
│   ├── bass.wav
│   └── other.wav
├── ...
└── track\_050/
```

Output modelu został zapisany analogicznie:

```text
output-dir/
├── track\_001/
│   ├── vocals.wav
│   ├── drums.wav
│   ├── bass.wav
│   └── other.wav
├── ...
└── track\_050/
```

Nazwy `track\_001 ... track\_050` są zgodne pomiędzy outputem modelu i ground truth.

## Preprocessing

Pliki wejściowe MP4 zostały przekonwertowane do WAV za pomocą FFmpeg.

* Sample rate: **44.1 kHz**
* Liczba kanałów: **2 (stereo)**
* Format wejściowy do modelu: **WAV**
* Normalizacja: brak dodatkowej normalizacji
* Dzielenie sygnału: fragmenty po **485100 próbek (\~11 s)**
* Overlap: **0.5**
* Krok między chunkami: ok. **5.5 s**

Przykładowa konwersja:

```bash
ffmpeg \\
    -i input.mp4 \\
    -vn \\
    -ac 2 \\
    -ar 44100 \\
    output.wav
```

Podczas inferencji każdy chunk był przenoszony na GPU, przetwarzany w FP16, a predykcje były następnie konwertowane do `float32` i składane metodą overlap-add.

Pliki wynikowe WAV były zapisywane za pomocą `soundfile`.

## Metryki

Obliczone za pomocą wspólnego `evaluator.py` zgodnego z benchmark protocol v1.0:

* **SDR** (`museval`)
* **SI-SDR** (własna implementacja evaluatora)
* **PQ** (`audiobox\_aesthetics`)
* **CE** (`audiobox\_aesthetics`)
* **CU** (`audiobox\_aesthetics`)
* **inference\_time\_sec**

Wyniki per utwór/stem:

```text
results.csv
```

Agregaty (mean / median / std):

```text
summary\_results.csv
```

Czas inferencji był mierzony osobno dla każdego utworu. Pomiar obejmował właściwą separację i transfer wyników GPU → CPU, ale nie obejmował wczytywania wejściowego WAV ani zapisu końcowych stemów na dysk.

## Analiza jakościowa

### Wybrane utwory

Do odsłuchu jakościowego można wykorzystać wspólnie wybrane utwory:

* track\_001: Timboz - Pony
* track\_002: Skelpolu - Resurrection
* track\_003: Side Effects Project - Sing With Me
* track\_004: Girls Under Glass - We Feel Alright
* track\_005: Al James - Schoolboy Facination

### Analiza liczbowa

Poniższe sekcje należy uzupełnić na podstawie `results.csv` i `summary\_results.csv`.

#### Statystyki zbiorcze (mean / median / std)

|Stem|SDR mean|SDR median|SDR std|SI-SDR mean|SI-SDR median|SI-SDR std|
|-|-:|-:|-:|-:|-:|-:|
|vocals|9.551|10.838|5.621|3.191|10.862|23.721|
|drums|10.098|11.232|5.591|5.494|11.441|19.819|
|bass|7.222|8.096|5.614|1.738|7.483|18.611|
|other|6.604|7.722|4.206|0.407|6.362|18.049|

|Stem|PQ mean|PQ median|PQ std|CE mean|CE median|CE std|CU mean|CU median|CU std|
|-|-:|-:|-:|-:|-:|-:|-:|-:|-:|
|vocals|7.012|7.148|0.484|5.067|5.173|1.081|6.141|6.257|0.607|
|drums|7.528|7.543|0.375|5.872|6.044|0.785|7.734|7.790|0.313|
|bass|6.351|6.470|0.627|4.262|4.088|0.786|6.266|6.336|0.460|
|other|7.059|7.081|0.731|6.357|6.645|1.053|7.132|7.173|0.559|

#### Rankingi źródeł

**Według SDR (średnia):**

1. drums — 10.098 dB
2. vocals — 9.551 dB
3. bass — 7.222 dB
4. other — 6.604 dB

**Według SI-SDR (średnia):**

1. drums — 5.494 dB
2. vocals — 3.191 dB
3. bass — 1.738 dB
4. other — 0.407 dB

**Według PQ:**

1. drums — 7.528
2. other — 7.059
3. vocals — 7.012
4. bass — 6.351

**Według CE:**

1. other — 6.357
2. drums — 5.872
3. vocals — 5.067
4. bass — 4.262

**Według CU:**

1. drums — 7.734
2. other — 7.132
3. bass — 6.266
4. vocals — 6.141

#### Kluczowe wnioski

**a) Perkusja jest najmocniejszym i najbardziej stabilnym stemem modelu.**

* Ma najwyższy średni SDR: **10.098 dB**.
* Ma także najwyższy średni SI-SDR: **5.494 dB**.
* Osiąga najwyższe PQ (**7.528**) i CU (**7.734**).
* Niskie odchylenia standardowe PQ (**0.375**) i CU (**0.313**) wskazują, że ocena percepcyjna perkusji jest stosunkowo spójna między utworami.

**b) Wokal również jest separowany bardzo dobrze, ale wyniki SI-SDR są nierówne.**

* Średni SDR wokalu wynosi **9.551 dB**, a mediana **10.838 dB**.
* Mediana SI-SDR jest wysoka (**10.862 dB**), ale średnia spada do **3.191 dB**.
* Bardzo wysokie odchylenie standardowe SI-SDR (**23.721 dB**) wskazuje na obecność silnych przypadków odstających, które mocno obniżają średnią.

**c) Bass i other są słabsze pod względem czystości separacji.**

* Bass osiąga średni SDR **7.222 dB** i średni SI-SDR **1.738 dB**.
* Other ma najniższy średni SDR (**6.604 dB**) i SI-SDR (**0.407 dB**).
* Jednocześnie mediany są wyraźnie wyższe od średnich, szczególnie dla SI-SDR, co ponownie wskazuje na wpływ pojedynczych bardzo słabych przypadków.

**d) Metryki percepcyjne nie są bezpośrednio zgodne z SDR i SI-SDR.**

* `other` ma najsłabszy średni SI-SDR (**0.407 dB**), ale najwyższe CE (**6.357**) i drugie najwyższe CU (**7.132**).
* `vocals` ma drugi najwyższy SDR, ale najniższe CU (**6.141**).
* Oznacza to, że dobra separacja sygnałowa i dobra ocena percepcyjna nie są tym samym kryterium.

**e) Różnica między średnią a medianą SI-SDR jest bardzo duża.**

* vocals: mean **3.191**, median **10.862**
* drums: mean **5.494**, median **11.441**
* bass: mean **1.738**, median **7.483**
* other: mean **0.407**, median **6.362**

Tak duża różnica oznacza, że typowy wynik dla wielu utworów jest znacznie lepszy niż sugeruje sama średnia, ale kilka ekstremalnie słabych przypadków mocno ją obniża. Dlatego przy interpretacji BS-RoFormera warto patrzeć jednocześnie na średnią, medianę i odchylenie standardowe.

#### 

#### Czas inferencji

Czasy inferencji znajdują się w:

```text
inference\_times.json
```

Do uzupełnienia po analizie pełnego benchmarku:

* **minimum**: TODO s
* **maksimum**: TODO s
* **średnia**: TODO s / utwór
* **mediana**: TODO s / utwór
* **łączny czas dla 50 utworów**: TODO
* **sprzęt**: NVIDIA H100

## Problemy napotkane podczas benchmarku

### Obsługa MP4

Bezpośrednie wczytywanie plików MP4 przez `librosa` / `soundfile` nie działało w środowisku WCSS ze względu na brak odpowiedniego backendu dekodującego.

Rozwiązanie:

* konwersja MP4 → WAV za pomocą FFmpeg,
* dalsza inferencja na plikach WAV.

### Flash Attention i precyzja

Inferencja w `float32` powodowała błąd związany z brakiem dostępnego kernela Flash Attention.

Próba użycia `BF16` rozwiązywała problem attention, ale prowadziła do błędu przy:

```python
torch.view\_as\_complex(...)
```

Finalnie zastosowano:

```python
with torch.autocast(device\_type="cuda", dtype=torch.float16):
    prediction = model(chunk)
```

czyli mixed precision **FP16**.

### Zapis WAV

`torchaudio.save()` wymagało dodatkowej zależności `torchcodec`.

Rozwiązanie:

```python
soundfile.write(...)
```

### Środowisko evaluatora

Evaluator wymagał nowszego środowiska niż model inferencyjny.

* inferencja: Python 3.10.4
* evaluator: Python 3.12.3

Osobne środowisko evaluatora pozwoliło uniknąć konfliktów zależności.

### FFmpeg / FFprobe w evaluatorze

`museval` korzysta pośrednio z `musdb` i `stempeg`, które wymagają dostępności FFmpeg oraz FFprobe.

Konieczne było załadowanie kompatybilnego modułu FFmpeg w jobie evaluatora.



co zapewniło bezpieczny zapas pamięci.

## Obserwacje po odsłuchu

### Wokale

* TODO
* Ocenić obecność instrumentów w tle.
* Ocenić pogłos, szum i artefakty.
* Porównać odsłuch z SDR / SI-SDR.

### Perkusja

* TODO
* Ocenić czystość transientów i talerzy.
* Sprawdzić przenikanie wokalu i instrumentów harmonicznych.

### Bass

* TODO
* Ocenić zachowanie barwy, dynamiki i niskich częstotliwości.
* Sprawdzić przenikanie basu do `other`.

### Other

* TODO
* Ocenić ilość pozostałości wokalu, perkusji i basu.
* Sprawdzić, czy stem zachowuje naturalne brzmienie instrumentów harmonicznych.

## Podsumowanie

* **BS-RoFormer najlepiej separuje perkusję i wokal** — średni SDR wynosi odpowiednio **10.098 dB** i **9.551 dB**.
* **Drums jest najbardziej zbalansowanym stemem**: ma najwyższe SDR, SI-SDR, PQ i CU oraz niski rozrzut metryk percepcyjnych.
* **Bass i other są słabsze pod względem separacji sygnałowej** — szczególnie `other`, którego średni SI-SDR wynosi **0.407 dB**.
* **Metryki percepcyjne nie pokrywają się bezpośrednio z SDR/SI-SDR** — `other` ma słabą separację sygnałową, ale wysokie CE i CU.
* **SI-SDR ma bardzo duży rozrzut**, szczególnie dla wokalu. Wysokie mediany przy znacznie niższych średnich wskazują na obecność ekstremalnie słabych outlierów.
* Model został przetestowany na pełnym zbiorze **MUSDB18 (50 utworów)**, na GPU **NVIDIA H100**, z inferencją w mixed precision **FP16**.
* Najważniejsze problemy techniczne podczas benchmarku dotyczyły dekodowania MP4, Flash Attention, braku kompatybilności BF16 z `view\_as\_complex`, zależności FFmpeg/FFprobe oraz zużycia pamięci przez evaluator.
* Do pełnej analizy jakościowej pozostaje uzupełnienie obserwacji odsłuchowych oraz wskazanie konkretnych najlepszych i najgorszych przypadków z `results.csv`.

