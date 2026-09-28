# Mix Agent — postprocessing/mix na bazie Pedalboard

Agent odpowiedzialny za postprocessing i miksowanie wyseparowanych ścieżek
(stemów) na podstawie prośby użytkownika w języku naturalnym. Wykorzystuje
DeepSeek (tool calling) do decydowania, których efektów audio użyć, oraz
bibliotekę Pedalboard (Spotify) do ich realnego zastosowania.

## Jak to działa

1. Backend/orkiestrator przekazuje manifest (lista stemów + ścieżki) oraz
   prompt użytkownika.
2. Dla każdego stemu osobno wysyłane jest zapytanie do DeepSeek z pytaniem,
   jakich narzędzi (gain, eq, compressor, limiter) użyć i z jakimi parametrami.
3. Wybrane efekty są budowane jako łańcuch Pedalboard i stosowane na pliku audio.
4. Niezależnie od decyzji modelu, na końcu zawsze stosowany jest bezpieczny
   limiter (ochrona przed przesterowaniem/clippingiem).
5. Wynik zapisywany jest w `STORAGE_ROOT`, funkcja zwraca też informację,
   jakie efekty zostały użyte.

## Struktura plików

- `config.py` — wczytuje `.env`, trzyma stałe (kolejność efektów, limity parametrów)
- `effects.py` — buduje obiekty Pedalboard (gain/eq/compressor/limiter)
- `agent.py` — komunikacja z DeepSeek, tool calling, parsowanie odpowiedzi
- `server.py` — `process_stem()` (jeden plik) i `process_job()` (cały manifest)
- `requirements.txt` — zależności Pythona
- `setup.sh` — tworzy środowisko wirtualne i instaluje zależności

## Instalacja

\`\`\`bash
git clone <link-do-repo>
cd mix_agent
chmod +x setup.sh
./setup.sh
source venv/bin/activate
\`\`\`

## Konfiguracja

Skopiuj szablon i uzupełnij własnymi wartościami:

\`\`\`bash
cp .env_template .env
nano .env   # wklej DEEPSEEK_API_KEY i sprawdź STORAGE_ROOT
\`\`\`

Zmienne w `.env`:
- `DEEPSEEK_API_KEY` — klucz API do DeepSeek (nie commitować!)
- `DEEPSEEK_BASE_URL` — endpoint API (domyślnie `https://api.deepseek.com`)
- `STORAGE_ROOT` — ścieżka, w której zapisywane są przetworzone stemy
  (lokalnie: dowolny folder testowy, na WCSS: uzgodniona z zespołem ścieżka
  współdzielona z innymi agentami)

## Użycie

\`\`\`python
from server import process_job

manifest = {
    "job_id": "test1",
    "stems": {
        "vocals": "sciezka/do/vocals.wav",
        "bass":   "sciezka/do/bass.wav",
        "drums":  "sciezka/do/drums.wav",
        "other":  "sciezka/do/other.wav",
    }
}

results = process_job(manifest, "zrób głośniejszy wokal, dodaj kompresję na bębnach")
