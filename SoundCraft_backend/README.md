# SoundCraft Backend

Backend API aplikacji **SoundCraft** odpowiedzialny za przyjmowanie plików audio, przesyłanie ich na serwer HPC oraz pobieranie wyników wygenerowanych przez agenta.

Backend wykorzystuje **FastAPI**, **FFmpeg** oraz **SFTP**.

---

## 1. Jak działa system?

```text
Client
  │
  │ POST /upload
  ▼
FastAPI
  │
  ├── zapis audio
  ├── konwersja do WAV
  ├── metadata.json
  │
  ▼
HPC / request_<UUID>/
  │
  │ Agent
  ▼
HPC / request_<UUID>/output/
  │
  │ SFTP
  ▼
FastAPI
  │
  ├── GET /result/<UUID>
  └── GET /result/<UUID>/audio
```

Każdy request otrzymuje unikalny `request_id` w formacie UUID.

---

## 2. Struktura na HPC

Katalog bazowy:

```text
/home/wojgrz4918/backend_files
```

Struktura:

```text
backend_files/
└── request_<UUID>/
    ├── input/
    │   ├── audio.wav
    │   └── metadata.json
    │
    └── output/
        ├── audio.wav
        └── response.json
```

---

## 3. Upload — `POST /upload`

Endpoint przyjmuje `multipart/form-data`.

### Input

| Pole     | Typ    | Opis                  |
| -------- | ------ | --------------------- |
| `prompt` | string | Instrukcja dla agenta |
| `audio`  | file   | Plik audio            |

Przykład:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/upload" `
  -F "prompt=test upload" `
  -F "audio=@C:\audio\test.wav"
```

Backend:

1. generuje `request_id`,
2. zapisuje plik,
3. sprawdza format audio,
4. w razie potrzeby konwertuje audio przez FFmpeg,
5. tworzy `metadata.json`,
6. tworzy katalog requestu na HPC,
7. przesyła dane na HPC przez SFTP.

---

## 4. Format inputu dla agenta

Agent otrzymuje:

```text
request_<UUID>/
├── input/
│   ├── audio.wav
│   └── metadata.json
```

### `audio.wav`

Docelowy format:

```text
WAV
Stereo
44100 Hz
```

### `metadata.json`

```json
{
  "request_id": "25b356a4-a8e5-447a-a6a4-83c1febed4eb",
  "prompt": "make the drums more energetic",
  "audio": "audio.wav"
}
```

---

## 5. Output agenta

Po zakończeniu pracy agent powinien utworzyć:

```text
request_<UUID>/
└── output/
    ├── audio.wav
    └── response.json
```

### `response.json`

Przykładowy format:

```json
{
  "status": "success",
  "message": "Audio processed successfully"
}
```

Zawartość `response.json` może zostać rozszerzona w zależności od potrzeb agenta.

---

## 6. Pobieranie wyniku

### `GET /result/{request_id}`

Pobiera status oraz `response.json`.

Jeżeli agent jeszcze nie zakończył pracy:

```json
{
  "status": "processing"
}
```

Po zakończeniu:

```json
{
  "status": "completed",
  "request_id": "25b356a4-a8e5-447a-a6a4-83c1febed4eb",
  "response": {
    "status": "success",
    "message": "Audio processed successfully"
  }
}
```

### `GET /result/{request_id}/audio`

Pobiera wygenerowany plik:

```text
output/audio.wav
```

Zwracany jest jako:

```text
Content-Type: audio/wav
```

---

## 7. Endpointy

| Method   | Endpoint                     | Opis                  |
| -------- | ---------------------------- | --------------------- |
| `POST`   | `/upload`                    | Upload audio + prompt |
| `GET`    | `/result/{request_id}`       | Status i wynik JSON   |
| `GET`    | `/result/{request_id}/audio` | Pobranie audio        |
| `DELETE` | `/result/{request_id}`       | Usunięcie requestu    |

---

## 8. Transfer plików

Transfer plików na HPC oraz pobieranie wyników odbywa się przez:

```text
SFTP
```

Komunikacja:

```text
FastAPI
   │
   │ SFTP
   ▼
WCSS / HPC
```

---

## 9. Konfiguracja

Konfiguracja znajduje się w `.env`:

```env
SFTP_HOST=ui.wcss.pl
SFTP_USERNAME=wojgrz4918
SFTP_REMOTE_PATH=/home/wojgrz4918/backend_files
SFTP_PRIVATE_KEY=C:/Users/emili/.ssh/id_ed25519
SFTP_PORT=22
```

---

## 10. Uruchomienie

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

## 11. Pełny workflow

```text
POST /upload
      │
      ▼
request_id = UUID
      │
      ▼
audio + metadata.json
      │
      ▼
HPC/request_<UUID>/input/
      │
      │ Agent
      ▼
HPC/request_<UUID>/output/
      │
      ├── response.json
      └── audio.wav
      │
      ▼
GET /result/<UUID>
      │
      ▼
GET /result/<UUID>/audio
```

Najważniejszym kontraktem pomiędzy backendem a agentem jest struktura:

```text
request_<UUID>/
├── input/
│   ├── audio.wav
│   └── metadata.json
│
└── output/
    ├── audio.wav
    └── response.json
```
