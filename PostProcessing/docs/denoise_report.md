# Raport: spectral gating dla ścieżek po Spleeterze (zadanie 3.3)

## Cel

Zweryfikować, czy klasyczny spectral gating poprawia jakość wyseparowanych
ścieżek audio. Odpowiedź na pytanie 15 z sekcji 9 dokumentu architektury
(`orkiestrator-sam-audio-wcss.md`).

## Metoda

- **Dane:** `track_001` z test setu MUSDB18 (Spleeter 4-stem output),
  wszystkie 4 stemy: vocals, drums, bass, other.
- **Narzędzie:** `noisereduce` 3.0.3 (spectral gating).
- **Parametry:** `prop_decrease` = 0.5, 0.7, 0.8, 0.9; `stationary=False`;
  `n_fft=2048`; `chunk_size=10 s`.
- **Środowisko:** Kaggle (30 GB RAM), Python 3.12.
- **Analiza:** spektrogramy i odsłuch A/B w Audacity 4.0.

## Wyniki

### Spektrogramy

Porównanie wersji `prop_decrease` 0.5, 0.7, 0.8, 0.9 wobec oryginału
pokazuje wyraźny gradient zależny od wartości parametru:

| Wartość | Tło (szum) | Sygnał wokalu |
| :---: | :--- | :--- |
| 0.5 | Subtelnie wyciszone | Zachowany bez zmian |
| 0.7 | Wyraźnie ciemniejsze | Zachowany, drobne ubytki wysokich tonów |
| 0.8 | Mocno ciemne | Zauważalne ubytki w wysokich częstotliwościach |
| 0.9 | Jaśniejsze od 0.8 (patrz uwaga niżej) | Znaczne ubytki, słyszalna „puszkowość" |

Na każdym poziomie `prop_decrease` **główny sygnał wokalu pozostaje
zachowany** – harmoniczne prążki są widoczne na spektrogramie. Redukcja
dotyczy głównie szumu tła i artefaktów wokół sygnału.

**Uwaga o `prop_decrease=0.9`:** wbrew intuicji, tło w wersji `pd90`
wygląda na **jaśniejsze** niż w `pd80`, mimo wyższej wartości redukcji.
Wynika to z dwóch czynników:

1. **Autoskalowanie kolorów w Audacity** - przy niższym poziomie sygnału
   Audacity rozciąga skalę kolorów, przez co tło wygląda na jaśniejsze,
   mimo że jest cichsze w liczbach bezwzględnych.
2. **Musical noise** - przy `prop_decrease=0.9` spectral gating zaczyna
   generować „ćwierkające" artefakty, które pojawiają się jako jasne punkty
   w tle. To znany efekt tej metody (opisany w sekcji 4.3 dokumentu
   architektury: „bez wygładzenia pojedyncze biny raz przechodzą, raz są
   tłumione, co daje brzęczące, migające artefakty").

Efekt ten potwierdza, że `prop_decrease ≥ 0.9` jest **zbyt agresywne** –
zamiast czyścić, wprowadza dodatkowe artefakty. Dlatego rekomendowane
pozostaje `pd70`.

### Odsłuch A/B

- **0.5** – subtelne, ledwo słyszalna różnica w stosunku do oryginału.
- **0.7** – słyszalna redukcja szumu tła, wokal pozostaje czytelny.
  **Najlepszy kompromis.**
- **0.8** – mocniejsza redukcja tła, ale wokal zaczyna brzmieć „puszkowo".
- **0.9** – agresywne, wokal zniekształcony, w tle obecny musical noise.

**Kluczowa obserwacja:** artefakt „puszkowości" wokalu (typowy efekt
separacji Spleetera) **pozostaje obecny na każdym poziomie** `prop_decrease`.
Filtr nie usuwa go, a przy wartościach ≥ 0.8 nawet go pogłębia.

## Wnioski

**Klasyczny spectral gating daje częściową poprawę, ale nie rozwiązuje
głównego problemu.**

- ✅ **Redukuje szum tła** - szczególnie w obszarach ciszy i pauz.
- ✅ **Zachowuje główny sygnał** - harmoniczne wokalu pozostają nienaruszone.
- ❌ **Nie usuwa artefaktów separacji** (puszkowości, przenikania instrumentów).
- ⚠️ Przy zbyt agresywnych ustawieniach (`prop_decrease ≥ 0.8`) **pogarsza**
  jakość wokalu, wycinając ciche fragmenty (spółgłoski, ogony pogłosu)
  i wprowadzając musical noise.

Potwierdza to hipotezę z sekcji 4.3 dokumentu architektury: artefakty po
separacji nie są szumem stacjonarnym, więc klasyczna bramka widmowa ich nie
usuwa. Filtr działa poprawnie **na tym, do czego został zaprojektowany** –
na szum tła.

## Odpowiedź na pytanie 15 z sekcji 9

> „Czy spectral gain w ogóle poprawia ścieżki po separacji?"

**Częściowo.** Spectral gating redukuje szum tła i artefakty wokół sygnału,
ale nie usuwa artefaktów separacji. Dla czyszczenia tła - warto użyć
(`prop_decrease=0.7`); dla usunięcia puszkowości wokalu - nie wystarczy,
potrzebny model neuronowy.

## Załączniki

- `tests/sample_outputs/track_001_vocals_pd70.mp3` – wynik z zalecanym
  `prop_decrease=0.7`
- `tests/sample_outputs/track_001_vocals_pd90.mp3` – dla kontrastu
  (agresywna redukcja, widoczny musical noise)
- `tests/spectrograms/vocals_comparison.png` – porównanie spektrogramów
  (oryginał + pd50 + pd70 + pd80 + pd90)
