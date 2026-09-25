# PostProcessing - narzędzia MCP dla systemu wieloagentowego

Zadania 3.2 i 3.3 z dokumentu architektury (`orkiestrator-sam-audio-wcss.md`).

## Zawartość
- `stitch_stems.py` - narzędzie MCP do remiksu wyseparowanych ścieżek (3.2)
- `denoise_stem.py` - narzędzie MCP do odszumiania (3.3, spectral gating)
- `docs/denoise_report.md` - raport z testów spectral gating
- `tests/` - pliki audio i screeny z testów

## 3.2 stitch_stems - remix ze stemów

**Typ:** narzędzie MCP (deterministyczne, nie agent)

**Funkcja:** sumuje wyseparowane stemy z opcjonalnymi wagami, normalizuje
i zapisuje wynik. Orkiestrator tłumaczy komendy użytkownika (np. „usuń wokal",
„wokal głośniej") na wywołania tego narzędzia.

**Możliwości:**
- Pełny remiks (wszystkie stemy ×1.0)
- Karaoke (vocals=0.0)
- A cappella (drums=bass=other=0.0)
- Eksponowanie instrumentu (np. vocals=1.5)
- Dowolna kombinacja wag

**Testy:** 5 utworów × 4 scenariusze (full, karaoke, vocal_boost, swapped).
Wyniki: ✅ narzędzie działa poprawnie.

## 3.3 denoise_stem - odszumianie (spectral gating)

**Typ:** narzędzie MCP (spectral gating przez `noisereduce`)

**Funkcja:** odszumianie wyseparowanych ścieżek metodą bramki widmowej.

**Wynik testów:** ⚠️ częściowa poprawa - spectral gating redukuje szum tła
i artefakty wokół sygnału, ale **nie usuwa artefaktów separacji** („puszkowości"
wokalu, przenikania instrumentów).

**Zalecane parametry:** `prop_decrease=0.7` (najlepszy kompromis).

**Szczegóły:** patrz `docs/denoise_report.md`.

## Środowisko testów
- Kaggle (30 GB RAM), Python 3.12
- `noisereduce` 3.0.3
- Analiza: Audacity 4.0 (spektrogramy + odsłuch A/B)
