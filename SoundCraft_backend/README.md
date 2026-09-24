# SoundCraft Backend

Backend API aplikacji **SoundCraft** odpowiedzialny za przyjmowanie plików audio, przesyłanie ich na serwer HPC oraz pobieranie wyników wygenerowanych przez agenta.

Backend wykorzystuje **FastAPI**, **FFmpeg**, **SFTP** oraz opcjonalnie **rsync**.

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
HPC / input/request<UUID>/
  │
  │ Agent
  ▼
HPC / output/request<UUID>/
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
/lustre/pd03/hpc-danbor2008-1756464546/wojgrz4918/soundcraft
```

Struktura:

```text
soundcraft/
├── input/
│   └── request<UUID>/
│       ├── audio.wav
│       └── metadata.json
│
└── output/
    └── request<UUID>/
        ├── audio.wav
        └── response.json
```

Przykład:

```text
input/request25b356a4-a8e5-447a-a6a4-83c1febed4eb/
├── audio.wav
└── metadata.json
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
6. przesyła dane na HPC.

---

## 4. Format inputu dla agenta

Agent otrzymuje:

```text
input/request<UUID>/
├── audio.wav
└── metadata.json
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
output/request<UUID>/
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
output/request<UUID>/audio.wav
```

Zwracany jest jako:

```text
Content-Type: audio/wav
```

---

## 7. Endpointy

| Method | Endpoint                     | Opis                  |
| ------ | ---------------------------- | --------------------- |
| `POST` | `/upload`                    | Upload audio + prompt |
| `GET`  | `/result/{request_id}`       | Status i wynik JSON   |
| `GET`  | `/result/{request_id}/audio` | Pobranie audio        |

---

## 8. Transfer plików

Upload na HPC próbuje użyć:

```text
rsync
```

Jeżeli `rsync` nie zadziała, backend używa:

```text
SFTP
```

Pobieranie wyników odbywa się przez SFTP.

---

## 9. Konfiguracja

Konfiguracja znajduje się w `.env`:

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
HPC/input/request<UUID>/
      │
      │ Agent
      ▼
HPC/output/request<UUID>/
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
input/request<UUID>/
├── audio.wav
└── metadata.json

output/request<UUID>/
├── audio.wav
└── response.json
```
