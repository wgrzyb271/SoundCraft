# SoundCraft Backend

Opis zmian wykonanych podczas integracji z WCSS znajduje się w
[README_ZMIANY.md](README_ZMIANY.md).

Backend API aplikacji **SoundCraft** odpowiedzialny za przyjmowanie plików audio, przesyłanie ich na serwer HPC oraz pobieranie wyników wygenerowanych przez agenta.

Backend wykorzystuje **FastAPI**, **FFmpeg** oraz **SFTP** i **rsync** jako backup.

---

## 1. Jak działa system?

```text
Client
  │
  │ POST /upload/audio
  ▼
FastAPI
  │
  ├── zapis audio
  ├── konwersja do WAV
  ├── upload audio
  │
  ▼
HPC / request_<UUID>/
  │
  │ POST /upload/<UUID>/prompt
  ▼
HPC / request_<UUID>/input/
  │
  │ Agent / ML
  ▼
HPC / request_<UUID>/output/
  │
  │ SFTP
  ▼
FastAPI
  │
  ├── WebSocket /ws/result/<UUID>
  │       └── notification: completed
  │
  ├── GET /result/<UUID>/agent_response
  └── GET /result/<UUID>/audio
```

Każdy request otrzymuje unikalny `request_id` w formacie UUID.

Jeden `request_id` reprezentuje jedno przetwarzanie audio i promptu. Aby wykonać
kolejną operację, prześlij audio ponownie i użyj nowego `request_id`.

---

## 2. Struktura na HPC

Katalog bazowy:

```text
/home/wojgrz4918/backend_files
```

Struktura:

```text
backend_files/
└── <request_UUID>/
    ├── input/
    │   ├── audio_folder/
    │   │   └── audio.wav
    │   │
    │   └── prompt_folder/
    │       └── prompt_<timestamp>.json
    │
    └── output/
        ├── audio_folder/
        │   ├── changed_audio_<timestamp>.wav
        │   └── ...
        │
        └── agent_response/
            ├── response_<timestamp>.json
            └── ...
```

---

## 3. Upload — `POST /upload/audio`

Endpoint przyjmuje `multipart/form-data`.

### Input

| Pole    | Typ  | Opis       |
| ------- | ---- | ---------- |
| `audio` | file | Plik audio |

Przykład:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/upload/audio" `
  -F "audio=@C:\audio\test.wav"
```

Backend:

1. generuje `request_id`,
2. tworzy strukturę katalogów requestu na HPC,
3. zapisuje plik,
4. sprawdza format audio,
5. w razie potrzeby konwertuje audio przez FFmpeg,
6. przesyła audio do `input/audio_folder/` przez rsync lub SFTP.

---

## 4. Upload promptu — `POST /upload/{request_id}/prompt`

Prompt jest przesyłany osobno dla istniejącego `request_id`.

### Input

| Pole     | Typ    | Opis                  |
| -------- | ------ | --------------------- |
| `prompt` | string | Instrukcja dla agenta |

Przykład:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/upload/<request_id>/prompt" `
  -F "prompt=make the drums more energetic"
```

Backend tworzy plik:

```text
input/
└── prompt_folder/
    └── prompt_<timestamp>.json
```

Przykładowa zawartość:

```json
{
  "request_id": "25b356a4-a8e5-447a-a6a4-83c1febed4eb",
  "prompt": "make the drums more energetic",
  "created_at": "2026-09-25T21:42:00+00:00",
  "expires_at": "2026-09-25T21:47:00+00:00",
  "status": "processing"
}
```

---

## 5. Format inputu dla agenta

Agent otrzymuje:

```text
<request_UUID>/
└── input/
    ├── audio_folder/
    │   └── audio.wav
    │
    └── prompt_folder/
        └── prompt_<timestamp>.json
```

### `audio.wav`

Docelowy format:

```text
WAV
Stereo
44100 Hz
```

### `prompt_<timestamp>.json`

Zawiera informacje potrzebne agentowi do przetworzenia requestu, w tym `request_id`, prompt oraz informacje o czasie utworzenia i wygaśnięcia requestu.

---

## 6. Output agenta

Po zakończeniu pracy agent powinien utworzyć:

```text
<request_UUID>/
└── output/
    ├── audio_folder/
    │   ├── changed_audio_<timestamp>.wav
    │   └── ...
    │
    └── agent_response/
        ├── response_<timestamp>.json
        └── ...
```

### `response_<timestamp>.json`

Przykładowy format:

```json
{
  "status": "success",
  "message": "Audio processed successfully"
}
```

Zawartość odpowiedzi może zostać rozszerzona w zależności od potrzeb agenta.

---

## 7. WebSocket — powiadomienie o zakończeniu

Backend udostępnia WebSocket:

```text
WS /ws/result/{request_id}
```

Frontend otwiera połączenie WebSocket po przyjęciu promptu. Backend zachowuje
wcześniejszy callback przez dwie godziny, więc szybkie zakończenie zadania nie
powoduje utraty powiadomienia.

Po zakończeniu przetwarzania agent/ML powinien powiadomić backend przez endpoint:

```text
POST /internal/ml/completed
```

### Request

```json
{
  "request_id": "25b356a4-a8e5-447a-a6a4-83c1febed4eb",
  "execution_code": "PASSED",
  "status": "PASSED",
  "audio_ready": true
}
```

Backend następnie wysyła przez WebSocket do klienta:

```json
{
  "status": "completed",
  "request_id": "25b356a4-a8e5-447a-a6a4-83c1febed4eb"
}
```

Frontend po otrzymaniu komunikatu `completed` pobiera wynik przez:

```text
GET /result/{request_id}/agent_response
GET /result/{request_id}/audio
```

### Co musi zrobić agent / ML?

Po zakończeniu przetwarzania agent musi:

1. zapisać wynik audio w `output/audio_folder/`,
2. zapisać `response_<timestamp>.json` w `output/agent_response/`,
3. wykonać HTTP POST do backendu:

```text
POST http://<backend-host>:8000/internal/ml/completed
```

Callback wymaga nagłówka `Authorization: Bearer <callback_token>`. Worker wykonuje
maksymalnie cztery próby w łącznym budżecie 30 sekund; błąd callbacku nie usuwa
wyniku zapisanego na WCSS.

z body:

```json
{
  "request_id": "<request_UUID>"
}
```

Agent **nie musi łączyć się bezpośrednio z WebSocketem**. WebSocket jest połączeniem między frontendem a backendem. Agent jedynie informuje backend przez HTTP, że przetwarzanie danego `request_id` zostało zakończone.

---

## 8. Pobieranie wyniku

### `GET /result/{request_id}/agent_response`

Pobiera status oraz najnowszy `response_<timestamp>.json`.

Jeżeli agent jeszcze nie zakończył pracy:

```json
{
  "status": "processing",
  "request_id": "25b356a4-a8e5-447a-a6a4-83c1febed4eb"
}
```

Po zakończeniu:

```json
{
  "status": "completed",
  "request_id": "25b356a4-a8e5-447a-a6a4-83c1febed4eb",
  "filename": "response_20260925_231942.json",
  "response": {
    "status": "success",
    "message": "Audio processed successfully"
  }
}
```

### `GET /result/{request_id}/audio`

Pobiera najnowszy plik:

```text
output/audio_folder/changed_audio_<timestamp>.wav
```

Zwracany jest jako:

```text
Content-Type: audio/wav
```

---

## 9. Endpointy

| Method   | Endpoint                              | Opis                        |
| -------- | ------------------------------------- | --------------------------- |
| `POST`   | `/upload/audio`                       | Upload audio                |
| `POST`   | `/upload/{request_id}/prompt`         | Upload prompt               |
| `WS`     | `/ws/result/{request_id}`             | Powiadomienie o zakończeniu |
| `POST`   | `/internal/ml/completed`              | Callback agenta/ML          |
| `GET`    | `/result/{request_id}/agent_response` | Odpowiedź od agenta         |
| `GET`    | `/result/{request_id}/audio`          | Pobranie zmienionego audio  |
| `DELETE` | `/result/{request_id}`                | Usunięcie requestu          |

---

## 10. Transfer plików

Transfer plików na HPC oraz pobieranie wyników odbywa się przez:

```text
Rsync
  │
  └── backup ──► SFTP
```

Komunikacja:

```text
FastAPI
   │
   ├── rsync
   │
   └── SFTP
        │
        ▼
    WCSS / HPC
```

---

## 11. Konfiguracja

Konfiguracja znajduje się w `.env` / `.config`:

```env
SFTP_HOST=ui.wcss.pl
SFTP_USERNAME=wojgrz4918
SFTP_REMOTE_PATH=/home/wojgrz4918/backend_files
SFTP_PRIVATE_KEY=C:/Users/emili/.ssh/id_ed25519
SFTP_PORT=22
```

---

## 12. Uruchomienie

Aktywacja środowiska:

```powershell
.\venv\Scripts\Activate.ps1
```

Uruchomienie API:

```powershell
uvicorn app.main:app --reload
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

---

## 13. Pełny workflow

```text
POST /upload/audio
      │
      ▼
request_id = UUID
      │
      ▼
audio.wav
      │
      ▼
HPC/<request_UUID>/input/audio_folder/
      │
      │
      │ Frontend otwiera:
      │ WS /ws/result/<request_UUID>
      │
      │
POST /upload/<request_id>/prompt
      │
      ▼
prompt_<timestamp>.json
      │
      ▼
HPC/<request_UUID>/input/prompt_folder/
      │
      │ Agent / ML
      ▼
HPC/<request_UUID>/output/
      │
      ├── audio_folder/
      │     └── changed_audio_<timestamp>.wav
      │
      └── agent_response/
            └── response_<timestamp>.json
      │
      │ Agent / ML
      │
      ▼
POST /internal/ml/completed
      │
      ▼
FastAPI
      │
      ▼
WebSocket → Frontend
      │
      │ {"status": "completed", ...}
      ▼
GET /result/<UUID>/agent_response
      │
      ▼
GET /result/<UUID>/audio
```

Najważniejszym kontraktem pomiędzy backendem a agentem jest struktura plików oraz callback HTTP po zakończeniu przetwarzania:

```text
<request_UUID>/
├── input/
│   ├── audio_folder/
│   │   └── audio.wav
│   │
│   └── prompt_folder/
│       └── prompt_<timestamp>.json
│       └── ...
│
└── output/
    ├── audio_folder/
    │   ├── changed_audio_<timestamp>.wav
    │   └── ...
    │
    └── agent_response/
        ├── response_<timestamp>.json
        └── ...
```

Backend zapisuje:

* plik audio wejściowy do `input/audio_folder/`,
* dane promptu wraz z metadanymi do `input/prompt_folder/`.

Agent zapisuje:

* przetworzony plik audio do `output/audio_folder/`,
* odpowiedź agenta w formacie JSON do `output/agent_response/`,
* po zakończeniu przetwarzania wykonuje `POST /internal/ml/completed` z odpowiednim `request_id`.

Backend pobiera najnowszy plik wynikowy na podstawie odpowiedniego prefiksu i rozszerzenia:

* `changed_audio_*.wav` dla przetworzonego audio,
* `response_*.json` dla odpowiedzi agenta.
