# SAM-Audio Benchmark na MUSDB18 — Manual

Instrukcja uruchomienia i rozwiązywania problemów dla benchmarku modelu
`facebook/sam-audio-small` na zbiorze testowym MUSDB18.

## Spis treści

1. [Wymagania wstępne](#wymagania-wstępne)
2. [Struktura projektu](#struktura-projektu)
3. [Pierwsze uruchomienie](#pierwsze-uruchomienie)
4. [Uruchamianie benchmarku](#uruchamianie-benchmarku)
5. [Co robi `run_all.sh`](#co-robi-run_allsh)
6. [Znane problemy i rozwiązania](#znane-problemy-i-rozwiązania)
7. [Pobieranie wyników na lokalny komputer](#pobieranie-wyników-na-lokalny-komputer)
8. [Struktura wyników](#struktura-wyników)

---

## Wymagania wstępne

- Dostęp do klastra WCSS (`ui.wcss.pl`) i partycji GPU (`lem-gpu-short` lub
  podobna, z GPU generacji Hopper).
- Token HuggingFace z dostępem do `facebook/sam-audio-small` i modeli
  pomocniczych (Roberta judge ranker itd.), zapisany w pliku `.env` w
  katalogu projektu jako `HF_TOKEN=...`.
- Katalog `.env` musi mieć uprawnienia `600` (skrypt sam to sprawdza i
  ostrzega, jeśli nie).

## Struktura projektu

```
samuel_benchmark/
├── benchmark_common.py       # wspólne funkcje: wczytywanie/zapis wav, listowanie utworów, timer
├── config.yaml                # konfiguracja (progi, ścieżki domyślne itd.)
├── evaluator.py                # liczenie metryk SDR/SI-SDR/PQ/CE/CU (museval)
├── package_results.py          # składanie finalnej struktury repo (krok 4)
├── prepare_reference.py        # przygotowanie referencyjnego zbioru wav z MUSDB18
├── run_all.sh                  # główny skrypt orkiestrujący cały pipeline
├── run_samaudio_benchmark.py   # właściwe uruchomienie inferencji SAM-Audio
├── requirements.txt
├── musdb18 -> /lustre/.../datasets/musdb18          # symlink, surowy dataset
├── musdb18_test_wav/                                  # przygotowany zbiór referencyjny (wav)
├── venv -> /lustre/.../venvs/samuel_benchmark_venv    # symlink, wirtualne środowisko
├── samaudio_outputs/            # separowane stemy (wyjście modelu)
├── samaudio_inference_times.json
├── samaudio_results.csv         # metryki per utwór/stem
├── samaudio_summary.csv         # statystyki zbiorcze
└── SamAudio/                    # gotowa struktura do wrzucenia na repo (krok 4)
```

`venv` i `musdb18` to symlinki na `/lustre` — nie kopiuj ich bezpośrednio
przy transferze na inny komputer (patrz [sekcja o rsync](#pobieranie-wyników-na-lokalny-komputer)).

## Pierwsze uruchomienie

1. Zaloguj się na klaster:
   ```bash
   ssh wojgrz4918@ui.wcss.pl
   ```

2. Wejdź w sesję interaktywną z GPU:
   ```bash
   sub-interactive -t 4 -c 8 --mem 128 -p lem-gpu-short --gres=gpu:hopper:1
   ```
   - `-c 8` / `--mem 128` to zasoby CPU/RAM systemowego — **nie mają
     wpływu na pamięć GPU**. `--gres=gpu:hopper:1` daje jedną pełną kartę
     GPU (Hopper, ~93 GiB).
   - `-t 4` = limit czasu 4h. Dostosuj do liczby utworów, jeśli
     uruchamiasz pełny benchmark, nie tylko `--limit 5`.

3. Załaduj moduł Pythona (wymagane przed aktywacją venv — venv jest
   zbudowany na konkretnej wersji systemowego Pythona, bez tego modułu
   `python`/`python3` może wskazywać na inną, niekompatybilną wersję):
   ```bash
   module load python/3.11
   ```

4. Aktywuj wirtualne środowisko:
   ```bash
   source ~/samuel_benchmark/venv/bin/activate
   which python   # sanity check — MUSI pokazać .../samuel_benchmark/venv/bin/python
   ```
   **Jeśli `which python` pokaże inną ścieżkę** (np. `~/samuel/venv/...`),
   patrz [Problem: activate wskazuje na złe środowisko](#problem-activate-wskazuje-na-złe-środowisko).

## Uruchamianie benchmarku

Szybki test na 5 utworach (bez instalacji zależności, jeśli już są
zainstalowane):

```bash
./run_all.sh --skip-install --limit 5
```

Pełny benchmark (wszystkie utwory w `musdb18_test_wav/`, prawdopodobnie
bez `--limit`):

```bash
./run_all.sh --skip-install
```

Benchmark na konkretnie wybranych utworach (zgodnie z protokołem zespołu,
pkt 5.0):

```bash
./run_all.sh --skip-install --selected-tracks "Utwor_1" "Utwor_2" "Utwor_3" "Utwor_4" "Utwor_5"
```

### Flagi `run_all.sh`

> ⚠️ Poniższy opis oparty jest na tym, co faktycznie zaobserwowano w
> tej sesji (komunikaty skryptu, użyte flagi) — nie na przeczytaniu
> pełnego kodu `run_all.sh`. Przed poleganiem na tym w praktyce,
> zweryfikuj przez `./run_all.sh --help` lub `grep -n "^\s*--" run_all.sh`.

| Flaga | Działanie |
|---|---|
| `--skip-install` | Pomija krok `[0/4]` — instalację zależności z `requirements.txt`. Użyj, gdy środowisko jest już skonfigurowane; przyspiesza kolejne uruchomienia. |
| `--limit N` | Ogranicza inferencję (`[2/4]`) do pierwszych N utworów z automatycznie posortowanej (`LC_ALL=C`) lub jawnie podanej (`--selected-tracks`) listy. **Nie ogranicza** kroku `[3/4]` (evaluator) — ten zawsze liczy metryki dla wszystkich utworów w `musdb18_test_wav/`, resztę oznaczając jako `not_supported`. |
| `--selected-tracks "Nazwa_1" "Nazwa_2" ...` | Jawnie podaje, które utwory przetworzyć, zamiast automatycznego wyboru pierwszych N wg sortowania. **Zalecane**, gdy zespół ustalił konkretną piątkę wg protokołu (pkt 5.0) — omija ryzyko niespójności sortowania opisane w sekcji o problemie z `sort`/`sorted()`. Nazwy muszą odpowiadać nazwom katalogów w `musdb18_test_wav/` (podkreślenia zamiast spacji, bez rozszerzenia). |
| *(bez flag)* | Pełny pipeline: instalacja zależności, przygotowanie referencji (jeśli brak), inferencja na **wszystkich** utworach w `musdb18_test_wav/`, ewaluacja, złożenie struktury repo. |

### Przykład: uruchomienie na konkretnej piątce utworów

Jeśli zespół wskazał następujące utwory (np. z listy plików `.stem`):

```
Timboz - Pony.stem
Skelpolu - Resurrection.stem
Side Effects Project - Sing With Me.stem
Girls Under Glass - We Feel Alright.stem
Al James - Schoolboy Facination.stem
```

Nazwy `.stem` (natywny format MUSDB18) trzeba przekonwertować na format
katalogów używany w `musdb18_test_wav/` — spacje na podkreślenia, bez
rozszerzenia `.stem` (wzorzec potwierdzony np. przez
`Al_James_-_Schoolboy_Facination`, który pojawiał się w każdym
uruchomieniu w tej sesji):

```bash
module load python/3.11
source ~/samuel_benchmark/venv/bin/activate

./run_all.sh --skip-install --selected-tracks \
    "Timboz_-_Pony" \
    "Skelpolu_-_Resurrection" \
    "Side_Effects_Project_-_Sing_With_Me" \
    "Girls_Under_Glass_-_We_Feel_Alright" \
    "Al_James_-_Schoolboy_Facination"
```

> ⚠️ Konwersja nazw (spacja → `_`, usunięcie `.stem`) jest wnioskiem z
> obserwowanego wzorca nazewnictwa katalogów, nie z przeczytania kodu
> `prepare_reference.py`. Przed uruchomieniem na produkcyjnym zestawie
> sprawdź realne nazwy katalogów:
> ```bash
> ls musdb18_test_wav/ | grep -iE "timboz|skelpolu|side_effects|girls_under_glass"
> ```
> i w razie rozbieżności popraw nazwy we flagach `--selected-tracks`
> zamiast zakładać, że powyższa konwersja jest bezbłędna dla każdego
> tytułu (np. znaki specjalne, apostrofy, wielkie/małe litery mogą być
> obsługiwane inaczej niż tu założono).

Bez `--skip-install`, skrypt najpierw instaluje zależności z
`requirements.txt` (krok `[0/4]`).

## Co robi `run_all.sh`

Pipeline ma 4 kroki:

1. **`[0/4]`** — instalacja zależności (pomijana z `--skip-install`).
2. **`[1/4]`** — przygotowanie referencyjnego zbioru wav
   (`prepare_reference.py`), pomijane jeśli `musdb18_test_wav/` już
   istnieje. Bez `--selected-tracks`, automatycznie wybiera pierwsze 5
   utworów **w sortowaniu `LC_ALL=C`** (patrz niżej — to musi być spójne
   z sortowaniem w Pythonie).
3. **`[2/4]`** — uruchamia `run_samaudio_benchmark.py`: właściwa
   inferencja modelu SAM-Audio na każdym utworze × każdym stemie
   (vocals/drums/bass/other), zapisuje separowane audio do
   `samaudio_outputs/` i czasy inferencji do
   `samaudio_inference_times.json`.
4. **`[3/4]`** — `evaluator.py` liczy metryki (SDR, SI-SDR, PQ, CE, CU)
   dla **wszystkich** utworów w `musdb18_test_wav/`, nie tylko tych z
   `--limit`/`--selected-tracks`. Utwory bez odpowiadających wyników w
   `samaudio_outputs/` dostają `not_supported` we wszystkich kolumnach —
   to oczekiwane zachowanie przy `--limit`, nie błąd.
5. **`[4/4]`** — `package_results.py` (lub odpowiednik) składa finalną
   strukturę repo w `SamAudio/`: README (szablon z TODO), skopiowane
   audio wybranych utworów. Jeśli `SamAudio/README.md` już istnieje, nie
   jest nadpisywany.

## Znane problemy i rozwiązania

### Problem: `activate` wskazuje na złe środowisko

**Objaw:** `which python` po `source venv/bin/activate` pokazuje ścieżkę
inną niż `~/samuel_benchmark/venv/...` (np. starą lokalizację projektu
sprzed przeniesienia).

**Przyczyna:** plik `venv/bin/activate` zawiera **zahardkodowaną**
absolutną ścieżkę `VIRTUAL_ENV`, ustawioną w momencie tworzenia
środowiska. Jeśli projekt (albo tylko katalog `venv`) został potem
przeniesiony/zmieniona nazwa, `activate` nadal wskazuje starą ścieżkę —
niezależnie od tego, skąd faktycznie go `source`ujesz.

**Rozwiązanie (trwałe, bo `venv` leży na `/lustre` i jest współdzielony
między węzłami):**
```bash
grep VIRTUAL_ENV= ~/samuel_benchmark/venv/bin/activate   # sprawdź co tam jest
sed -i 's|^VIRTUAL_ENV=.*|VIRTUAL_ENV="/home/wojgrz4918/samuel_benchmark/venv"|' \
    ~/samuel_benchmark/venv/bin/activate
```

**Obejście doraźne (bez edycji pliku):**
```bash
deactivate 2>/dev/null
export PATH="/home/wojgrz4918/samuel_benchmark/venv/bin:$PATH"
export VIRTUAL_ENV="/home/wojgrz4918/samuel_benchmark/venv"
hash -r
```
Uwaga: to obejście nie ustawia `PS1` (prompt straci prefiks `(venv)`),
ale środowisko jest mimo to poprawnie aktywne — zweryfikuj `which python`.

### Problem: `TypeError: ... missing required keyword-only arguments: 'proxies' and 'resume_download'`

**Przyczyna:** nowsze wersje `huggingface_hub` usunęły/zdeprecjonowały
`resume_download`, ale `sam_audio`'s `BaseModel._from_pretrained` (i
klasy pochodne — w tym wewnętrzny `SAMAudioJudgeModel` ładowany przez
`JudgeRanker`) nadal go oczekują jako wymaganego argumentu
keyword-only.

**Rozwiązanie:** patch na poziomie `BaseModel._from_pretrained` (nie
tylko `SAMAudio._from_pretrained` — musi objąć wszystkie klasy
pochodne):
```python
from sam_audio.model.base import BaseModel

_orig_base_fp = BaseModel._from_pretrained.__func__

@classmethod
def _patched_base_fp(cls, *, proxies=None, resume_download=False, **kwargs):
    return _orig_base_fp(cls, proxies=proxies, resume_download=resume_download, **kwargs)

BaseModel._from_pretrained = _patched_base_fp
```
Ten patch jest już wbudowany w `run_samaudio_benchmark.py`.

### Problem: `TypeError: SAMAudioProcessor.__call__() got an unexpected keyword argument 'sampling_rate'`

**Przyczyna:** API procesora różni się od intuicyjnego/oczekiwanego —
nie przyjmuje `sampling_rate` ani `return_tensors`, a prompt tekstowy
idzie jako `descriptions=[...]` (lista), nie `text=...`.

**Poprawne wywołanie:**
```python
inputs = processor(audios=mixture_tensor, descriptions=[prompt])
```
Audio musi być tensorem 3D: `(batch, channels, samples)`.

### Problem: CUDA OOM podczas dekodowania kodeka audio (`dacvae`)

**Objaw:** `torch.OutOfMemoryError` w `audio_codec.decode(...)`, zwykle
po kilku przetworzonych utworach, z komunikatem że dużo pamięci jest
"reserved but unallocated" (fragmentacja).

**Rozwiązanie 1 — fragmentacja pamięci:** ustaw PRZED importem torch:
```python
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
```
oraz jawnie zwalniaj pamięć po każdym stemie/utworze:
```python
del inputs, outputs, separated, separated_np
torch.cuda.empty_cache()
gc.collect()
```

**Rozwiązanie 2 — realny brak pamięci (nie fragmentacja):** załaduj wagi
modelu w bf16 zamiast domyślnego fp32 (połowa zużycia pamięci):
```python
dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float32
model = SAMAudio.from_pretrained(model_id, torch_dtype=dtype, low_cpu_mem_usage=True)
model = model.eval().to(device, dtype=dtype)
```

> ⚠️ **NIE rzutuj ręcznie wejść (`inputs`) na bf16** przez rekurencyjne
> rzutowanie każdego tensora zmiennoprzecinkowego — to psuje wewnętrzne
> wartości procesora (np. długość audio przechowywaną jako float),
> prowadząc do cichego błędu w indeksowaniu (`unbatch()` przycina do
> złej długości, o kilkadziesiąt tysięcy próbek za dużej). Zamiast tego
> użyj `torch.autocast` wokół właściwego wywołania modelu — PyTorch sam
> dobiera precyzję per operacja, nie dotykając wartości przechowywanych
> w `inputs`:
> ```python
> with torch.no_grad():
>     with torch.autocast(device_type="cuda", dtype=dtype):
>         outputs = model.separate(inputs)
> ```

### Problem: `ValueError: shape of estimated sources and true sources should match` (museval)

**Przyczyna:** SAM-Audio zwraca audio **mono** (1 kanał), ale referencje
MUSDB18 są **stereo** (2 kanały). `museval.bss_eval` wymaga zgodnej
liczby kanałów.

**Rozwiązanie:** przed zapisem duplikuj kanał mono na L/R:
```python
if separated_np.ndim == 2 and separated_np.shape[1] == 1:
    separated_np = np.repeat(separated_np, 2, axis=1)
```
To jest jawne uproszczenie (nie prawdziwa separacja stereo) — jeśli w
przyszłości potrzebna będzie ocena jakości obrazu stereo, ten punkt
wymaga innego podejścia.

### Problem: lista utworów w `run_all.sh` nie zgadza się z tym, co faktycznie przetworzył `run_samaudio_benchmark.py`

**Przyczyna:** `run_all.sh` używa `find ... | sort | head -n 5` — zwykły
`sort` w powłoce respektuje **locale** (np. `en_US.UTF-8`), które sortuje
w przybliżeniu bez rozróżniania wielkości liter. `benchmark_common.py`
używa Pythonowego `sorted()`, które jest **zawsze** ścisłym porównaniem
bajtowym (ASCII) — wielkie litery zawsze przed małymi. Dla nazw typu
`BKS_-_Bulldozer` vs `Ben_Carrigan_...`, te dwa sortowania dają różny
5. element.

**Rozwiązanie:** wymuś sortowanie w stylu C (bajtowe) po stronie
powłoki, żeby zgadzało się z Pythonem:
```bash
find "$REFERENCE_DIR" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | LC_ALL=C sort | head -n 5
```
Ta zmiana **zmienia, które utwory zostają wybrane domyślnie** (bez
`--selected-tracks`) — jeśli zespół ma ustalony konkretny zestaw utworów
wg protokołu (pkt 5.0), **zawsze podawaj `--selected-tracks` jawnie**
zamiast polegać na automatycznym wyborze.

### Problem: HuggingFace re-downloaduje wagi (kilkanaście GB) na każdym nowym węźle

**Przyczyna:** domyślny cache `~/.cache/huggingface` może być lokalny
dla węzła (nie współdzielony), więc każdy nowy węzeł ściąga wagi od
nowa.

**Rozwiązanie:** przekieruj `HF_HOME` na współdzielony `/lustre` PRZED
importem `torch`/`transformers`/`huggingface_hub`:
```python
if "PDDIR" in os.environ:
    os.environ.setdefault("HF_HOME", os.path.join(os.environ["PDDIR"], "wojgrz4918", "hf_cache"))
```
Sprawdź, czy `$PDDIR` jest w ogóle ustawiony w Twojej sesji:
```bash
echo "PDDIR=$PDDIR"
```
Jeśli puste, ustaw ścieżkę na sztywno na Twój katalog `/lustre` zamiast
polegać na tej zmiennej.

## Pobieranie wyników na lokalny komputer

Ze swojego **laptopa** (nie z klastra), pobierz tylko gotową strukturę
do repo, pomijając surowe dane/symlinki:

```bash
rsync -avz --progress \
  wojgrz4918@ui.wcss.pl:~/samuel_benchmark/SamAudio/ \
  ~/Downloads/SamAudio/
```

Jeśli chcesz pominąć audio (np. bo nie trafia do gita, tylko
kod/wyniki):
```bash
rsync -avz --progress --exclude '*.wav' \
  wojgrz4918@ui.wcss.pl:~/samuel_benchmark/SamAudio/ \
  ~/Downloads/SamAudio/
```

Jeśli potrzebujesz całego projektu roboczego (skrypty, logi, CSV) —
**nie** `venv` ani `musdb18` (symlinki na `/lustre`, bardzo duże):
```bash
rsync -avz --progress \
  --exclude 'venv' --exclude 'musdb18' --exclude '__pycache__' \
  wojgrz4918@ui.wcss.pl:~/samuel_benchmark/ \
  ~/Downloads/samuel_benchmark/
```

## Struktura wyników

- **`samaudio_results.csv`** — jeden wiersz na (utwór, stem), kolumny:
  SDR, SI-SDR, PQ, CE, CU. Utwory spoza wybranej piątki mają
  `not_supported` we wszystkich kolumnach.
- **`samaudio_summary.csv`** — statystyki zbiorcze (prawdopodobnie
  średnie/mediany per stem — zweryfikuj dokładną zawartość w pliku).
- **`samaudio_inference_times.json`** — czas inferencji (sekundy) per
  utwór.
- **`SamAudio/README.md`** — szablon do ręcznego uzupełnienia przed
  commitem (pola TODO, pkt 9.0 protokołu zespołu).

---

*Dokument utworzony na podstawie sesji debugowania — jeśli coś się nie
zgadza z aktualnym stanem skryptów, zaufaj kodowi, nie temu README, i
zgłoś rozbieżność do aktualizacji.*
