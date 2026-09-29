# SoundCraft — uruchomienie laptop + WCSS (bez SAM Audio)

Ten dokument opisuje kompletne odtworzenie i uruchomienie pipeline'u:

```text
UI na laptopie
  -> lokalny backend :8000
  -> SSH/rsync
  -> katalog requestu na WCSS
  -> worker CPU
  -> BS-RoFormer na GPU (Demucs jako fallback)
  -> mixAgent
  -> PostProcessing
  -> callback HTTPS przez Cloudflare
  -> gateway laptopa :8001
  -> WebSocket
  -> UI pobiera wynik przez SSH/rsync
```

SAM Audio nie jest wymagany dla klasycznych stemów. Prompt testowy
`wyciągnij wokal` uruchamia BS-RoFormer, a Demucs jest jego fallbackiem.

## Stałe ścieżki i parametry

```text
Użytkownik WCSS:  wojgrz4918
Repozytorium WCSS: /home/wojgrz4918/SoundCraft
Katalog roboczy:   /home/wojgrz4918/tmp
Katalog requestów: /home/wojgrz4918/backend_files
Repo na laptopie:  /Users/glitch/Desktop/SoundCraft
Worker CPU:         lem-cpu-short
Modele GPU:         lem-gpu-short
Konto/QOS:          hpc-danbor2008-1756464546
```

Wszystkie pliki, środowiska, cache i logi po stronie WCSS muszą znajdować się
w `/home/wojgrz4918`.

## Po co jest Cloudflare Tunnel?

WCSS musi po zakończeniu pipeline'u poinformować backend działający na
laptopie. Adres `127.0.0.1` laptopa nie jest widoczny z WCSS, a laptop zwykle
znajduje się za NAT-em i firewallem. Quick Tunnel tworzy publiczny adres HTTPS,
który prowadzi wyłącznie do lokalnego gatewaya callbacku na porcie `8001`.

Cloudflare nie przesyła plików audio. Audio oraz wyniki są przesyłane przez
SSH/rsync (z fallbackiem SFTP). Publiczny gateway udostępnia tylko:

```text
GET  /health
POST /internal/ml/completed
```

Callback wymaga wspólnego tokenu Bearer. Gateway nie wystawia uploadu,
pobierania wyników ani pełnego backendu.

Quick Tunnel otrzymuje nowy URL po każdym ponownym uruchomieniu. Po zmianie URL
trzeba zmienić `callback.url` na WCSS i ponownie uruchomić worker, ponieważ
worker wczytuje konfigurację tylko podczas startu.

# A. Czynności jednorazowe

## A1. Laptop — środowisko UI

```bash
cd /Users/glitch/Desktop/SoundCraft

python3 -m venv .venv-ui
source .venv-ui/bin/activate

python -m pip install -r requirements-ui.txt

cd SoundCraft_frontend
npm install
cd ..
```

## A2. Laptop — wspólny token callbacku

Wygeneruj token i zachowaj go do konfiguracji WCSS:

```bash
cd /Users/glitch/Desktop/SoundCraft
source .venv-ui/bin/activate

CALLBACK_TOKEN=$(openssl rand -hex 32)
printf '\nZAPISZ TEN TOKEN:\n%s\n\n' "$CALLBACK_TOKEN"
export CALLBACK_TOKEN
```

Zaktualizuj konfigurację laptopa bez kasowania pozostałych sekcji:

```bash
python - <<'PY'
import os
from pathlib import Path

import yaml

path = Path("/Users/glitch/Desktop/SoundCraft/llm_agent/config.local.yaml")
data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
data = data or {}

data["backend"] = {
    "rsync_host": "wojgrz4918@ui.wcss.pl",
    "rsync_remote_path": "/home/wojgrz4918/backend_files",
    "sftp_host": "ui.wcss.pl",
    "sftp_username": "wojgrz4918",
    "sftp_remote_path": "/home/wojgrz4918/backend_files",
    "sftp_private_key": "/Users/glitch/.ssh/id_ed25519",
    "sftp_port": 22,
    "processing_ttl": 5400,
    "callback_token": os.environ["CALLBACK_TOKEN"],
    "completion_wait_timeout": 5400,
}

temporary = path.with_suffix(".yaml.tmp")
temporary.write_text(
    yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
    encoding="utf-8",
)
temporary.replace(path)
path.chmod(0o600)

print("Zapisano:", path)
print("Token callbacku: USTAWIONY")
PY
```

Plik `config.local.yaml` nie może być commitowany.

## A3. WCSS — aktualizacja repozytorium

Git na węźle logowania może przekraczać limit wątków. Używaj trybu
jednowątkowego:

```bash
cd /home/wojgrz4918/SoundCraft

git config --local pack.threads 1
git config --local index.threads 1
git config --local fetch.parallel 1
git config --local core.preloadindex false

git -c pack.threads=1 \
    -c index.threads=1 \
    fetch --no-tags origin llm_agent

git switch llm_agent
git merge --ff-only origin/llm_agent
```

Nie używaj `|| exit 1` w interaktywnej sesji SSH — w razie błędu zamknie całą
sesję.

## A4. WCSS — pełna konfiguracja orkiestratora

W heredocu wpisz własny token DeepSeek i ten sam token callbacku, który jest
ustawiony na laptopie. URL Cloudflare można później zmieniać helperem.

```bash
cat > /home/wojgrz4918/SoundCraft/llm_agent/config.local.yaml <<'YAML'
debug: false

api_keys:
  deepseek: "TU_WKLEJ_DEEPSEEK_TOKEN"
  huggingface: ""

env: {}

deepseek:
  model: deepseek-v4-flash
  thinking: false
  timeout_s: 60

orchestrator:
  classifier: hybrid
  max_failures: 3
  max_attempts_per_agent: 1
  agent_timeout_s: 3600
  postprocessing_timeout_s: 900
  count_unsupported_task: true

paths:
  models_yaml: /home/wojgrz4918/SoundCraft/llm_agent/models.yaml
  user_root: /home/wojgrz4918/backend_files
  request_root: /home/wojgrz4918/backend_files

callback:
  url: "https://TYMCZASOWY-ADRES.trycloudflare.com/internal/ml/completed"
  token: "TU_WKLEJ_TEN_SAM_CALLBACK_TOKEN"
  request_timeout_s: 5
  total_timeout_s: 30
  max_attempts: 4
  retry_base_s: 2

wcss:
  slurm_account: hpc-danbor2008-1756464546
  slurm_qos: hpc-danbor2008-1756464546
  slurm_partition: lem-gpu-short
  python_module: ""

agents:
  bs_roformer:
    root: /home/wojgrz4918/SoundCraft/agent_bs_roformer
    python: /home/wojgrz4918/tmp/venvs/bs-roformer/bin/python
    config: /home/wojgrz4918/bs_roformer/model_files/config_bs_roformer_384_8_2_485100.yaml
    checkpoint: /home/wojgrz4918/bs_roformer/model_files/model_bs_roformer_ep_17_sdr_9.6568.ckpt
    model_repo: /home/wojgrz4918/bs_roformer/Music-Source-Separation-Training

  demucs:
    python: /home/wojgrz4918/tmp/venvs/demucs/bin/python
    script: /home/wojgrz4918/SoundCraft/demucs/agent.py
    orchestrator_root: /home/wojgrz4918/SoundCraft/llm_agent

  sam_audio:
    python: /home/wojgrz4918/tmp/venvs/sam-audio/bin/python
    root: /home/wojgrz4918/SoundCraft/agent_sam_audio
    model: facebook/sam-audio-base

mcp:
  command: ""
  args: []
  env: {}
YAML

chmod 600 /home/wojgrz4918/SoundCraft/llm_agent/config.local.yaml
```

Obecność sekcji `sam_audio` nie uruchamia SAM dla promptu `wyciągnij wokal`.

## A5. WCSS — instalacja środowisk bez SAM Audio

Na `ui.wcss.pl` funkcja `module` może być niedostępna dla skryptów. Uruchom
instalację jako job Slurma. Jawnie ustaw `TMPDIR` w katalogu domowym, ponieważ
Slurm domyślnie ustawia go na `/mnt/lscratch`.

```bash
mkdir -p /home/wojgrz4918/tmp/logs

cat > /home/wojgrz4918/tmp/soundcraft-setup.sbatch <<'EOF'
#!/bin/bash -l
#SBATCH --job-name=soundcraft-setup
#SBATCH --account=hpc-danbor2008-1756464546
#SBATCH --qos=hpc-danbor2008-1756464546
#SBATCH --partition=lem-cpu-short
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --output=/home/wojgrz4918/tmp/logs/soundcraft-setup-%j.out
#SBATCH --error=/home/wojgrz4918/tmp/logs/soundcraft-setup-%j.err

source /etc/profile
set -eo pipefail

export TMPDIR=/home/wojgrz4918/tmp
export PIP_CACHE_DIR=/home/wojgrz4918/tmp/cache/pip
export XDG_CACHE_HOME=/home/wojgrz4918/tmp/cache/xdg
export TORCH_HOME=/home/wojgrz4918/tmp/cache/torch
export HF_HOME=/home/wojgrz4918/tmp/cache/huggingface

mkdir -p \
  /home/wojgrz4918/tmp/logs \
  /home/wojgrz4918/tmp/cache/pip \
  /home/wojgrz4918/tmp/cache/xdg \
  /home/wojgrz4918/tmp/cache/torch \
  /home/wojgrz4918/tmp/cache/huggingface

cd /home/wojgrz4918/SoundCraft
source ./scripts/setup_wcss.sh --without-sam
EOF

chmod 700 /home/wojgrz4918/tmp/soundcraft-setup.sbatch
bash -n /home/wojgrz4918/tmp/soundcraft-setup.sbatch
```

Wyślij instalację:

```bash
SETUP_JOB=$(sbatch --parsable /home/wojgrz4918/tmp/soundcraft-setup.sbatch)
echo "Setup Job ID: $SETUP_JOB"
```

Po zakończeniu:

```bash
sacct -j "$SETUP_JOB" \
  --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS

tail -n 50 "/home/wojgrz4918/tmp/logs/soundcraft-setup-${SETUP_JOB}.out"
tail -n 50 "/home/wojgrz4918/tmp/logs/soundcraft-setup-${SETUP_JOB}.err"
```

Prawidłowy rezultat kończy się komunikatem:

```text
== SAM Audio skipped (use --with-sam when ready) ==
Setup completed.
```

## A6. WCSS — helper do zmiany URL callbacku

```bash
mkdir -p /home/wojgrz4918/bin

cat > /home/wojgrz4918/bin/set-soundcraft-callback <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 1 ]]; then
    echo "Użycie: $0 https://ADRES.trycloudflare.com" >&2
    exit 2
fi

BASE_URL="${1%/}"
case "$BASE_URL" in
    https://*) ;;
    *) echo "URL musi zaczynać się od https://" >&2; exit 2 ;;
esac

if [[ "$BASE_URL" == */internal/ml/completed ]]; then
    CALLBACK_URL="$BASE_URL"
else
    CALLBACK_URL="${BASE_URL}/internal/ml/completed"
fi

CONFIG=/home/wojgrz4918/SoundCraft/llm_agent/config.local.yaml
TEMP="${CONFIG}.tmp.$$"
test -f "$CONFIG"

if ! awk -v callback_url="$CALLBACK_URL" '
BEGIN { in_callback = 0; replaced = 0 }
/^callback:[[:space:]]*$/ { in_callback = 1; print; next }
in_callback && /^[^[:space:]]/ { in_callback = 0 }
in_callback && /^  url:/ {
    print "  url: \"" callback_url "\""
    replaced = 1
    next
}
{ print }
END { if (!replaced) exit 42 }
' "$CONFIG" > "$TEMP"
then
    rm -f "$TEMP"
    echo "Nie znaleziono callback.url w $CONFIG" >&2
    exit 1
fi

chmod 600 "$TEMP"
mv "$TEMP" "$CONFIG"
chmod 600 "$CONFIG"

echo "Ustawiono callback:"
echo "$CALLBACK_URL"
echo "Po zmianie URL uruchom ponownie worker."
EOF

chmod 700 /home/wojgrz4918/bin/set-soundcraft-callback
```

# B. Szybkie uruchomienie — za każdym razem

## B1. Laptop, terminal 1 — UI, backend i gateway

```bash
cd /Users/glitch/Desktop/SoundCraft
source .venv-ui/bin/activate

python run_ui.py \
  --config /Users/glitch/Desktop/SoundCraft/llm_agent/config.local.yaml
```

Oczekiwane:

```text
UI: http://127.0.0.1:5173
API: http://127.0.0.1:8000
Callback gateway: http://127.0.0.1:8001
```

Pozostaw proces uruchomiony.

## B2. Laptop, terminal 2 — Cloudflare Quick Tunnel

Jednorazowa instalacja, jeżeli polecenia jeszcze nie ma:

```bash
command -v cloudflared >/dev/null 2>&1 || brew install cloudflared
```

Uruchom tunel:

```bash
cloudflared tunnel --url http://127.0.0.1:8001
```

Skopiuj wygenerowany adres `https://....trycloudflare.com`. Pozostaw tunel
uruchomiony. Sprawdź publiczny gateway w trzecim terminalu:

```bash
curl --fail-with-body https://TU_WKLEJ_ADRES.trycloudflare.com/health
```

Oczekiwane:

```json
{"status":"ok"}
```

## B3. WCSS — ustaw URL i uruchom worker

```bash
/home/wojgrz4918/bin/set-soundcraft-callback \
  https://TU_WKLEJ_ADRES.trycloudflare.com
```

Jeśli działa worker uruchomiony ze starym URL-em, zatrzymaj wyłącznie jego Job
ID:

```bash
scancel STARY_WORKER_JOB_ID
```

Uruchom nowy worker, jawnie podając partycję. Pomija to `sinfo`, które na węźle
logowania może zakończyć się błędem `pthread_create`:

```bash
cd /home/wojgrz4918/SoundCraft

WCSS_WORKER_PARTITION=lem-cpu-short \
  ./scripts/submit_wcss_worker.sh
```

Zapisz zwrócony Job ID:

```bash
WORKER_JOB=TU_WKLEJ_JOB_ID

squeue -j "$WORKER_JOB" \
  -o "%.18i %.14P %.24j %.8T %.10M %.30R"
```

Worker musi mieć stan `RUNNING`. Same komunikaty `Loading Python/...` w pliku
`.err` są normalne.

## B4. Test callbacku z WCSS (opcjonalny po zmianie tunelu)

Wstaw aktualny URL i ten sam token co w konfiguracji:

```bash
cat > /home/wojgrz4918/tmp/callback-check.sbatch <<'EOF'
#!/bin/bash -l
#SBATCH --job-name=soundcraft-callback
#SBATCH --account=hpc-danbor2008-1756464546
#SBATCH --qos=hpc-danbor2008-1756464546
#SBATCH --partition=lem-cpu-short
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=256M
#SBATCH --time=00:05:00
#SBATCH --output=/home/wojgrz4918/tmp/logs/callback-check-%j.out
#SBATCH --error=/home/wojgrz4918/tmp/logs/callback-check-%j.err

set -euo pipefail

CALLBACK_URL='https://TU_WKLEJ_ADRES.trycloudflare.com/internal/ml/completed'
CALLBACK_TOKEN='TU_WKLEJ_CALLBACK_TOKEN'

curl --fail-with-body \
  --connect-timeout 5 \
  --max-time 15 \
  -H "Authorization: Bearer ${CALLBACK_TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{
    "request_id": "11111111-1111-4111-8111-111111111111",
    "execution_code": "PASSED",
    "status": "PASSED",
    "audio_ready": true
  }' \
  "$CALLBACK_URL"

echo
echo "CALLBACK CHECK PASSED"
EOF

chmod 700 /home/wojgrz4918/tmp/callback-check.sbatch
CALLBACK_JOB=$(sbatch --parsable /home/wojgrz4918/tmp/callback-check.sbatch)
echo "Callback Job ID: $CALLBACK_JOB"
```

Po zakończeniu:

```bash
sacct -j "$CALLBACK_JOB" \
  --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS

cat "/home/wojgrz4918/tmp/logs/callback-check-${CALLBACK_JOB}.out"
cat "/home/wojgrz4918/tmp/logs/callback-check-${CALLBACK_JOB}.err"
```

Prawidłowy wynik zawiera `CALLBACK CHECK PASSED` oraz status `accepted`.

## B5. Test w UI

Otwórz:

```text
http://127.0.0.1:5173
```

Wybierz plik:

```text
/Users/glitch/Desktop/SoundCraft/samples/5s.wav
```

Wyślij dokładnie jeden prompt:

```text
wyciągnij wokal
```

Prawidłowy backend pokazuje kolejno:

```text
POST /upload/audio/                         200
POST /upload/<request_id>/prompt            200
WebSocket /ws/result/<request_id>           accepted
POST /internal/ml/completed                 200
GET /result/<request_id>/agent_response     200
GET /result/<request_id>/audio              200
```

Na WCSS można obserwować joby:

```bash
watch -n 10 'squeue -u "$USER" -o "%.18i %.14P %.24j %.8T %.10M %.30R"'
```

Powinien pojawić się job `soundcraft_bs`. Przy niepowodzeniu BS-RoFormer
orkiestrator uruchomi `soundcraft_demucs`. SAM Audio nie bierze udziału w tym
teście.

Log workera:

```bash
tail -f \
  "/home/wojgrz4918/tmp/logs/soundcraft-worker-${WORKER_JOB}.out" \
  "/home/wojgrz4918/tmp/logs/soundcraft-worker-${WORKER_JOB}.err"
```

# C. Zatrzymanie

Zatrzymaj worker WCSS:

```bash
scancel "$WORKER_JOB"
```

Na laptopie użyj `Ctrl+C` w terminalach:

1. `run_ui.py`,
2. `cloudflared`.

# D. Diagnostyka

## Port lokalny jest zajęty

`run_ui.py` używa `--strictPort` i kończy się czytelnym błędem. Zatrzymaj starą
instancję `run_ui.py`; nie uruchamiaj drugiej równolegle.

## `unix_listener ... path too long`

Aktualna wersja używa krótkiej ścieżki socketu:

```text
/tmp/sc-ssh-<uid>/<hash>
```

Jeżeli w logu występuje długa ścieżka z macOS `TMPDIR`, uruchomiona jest stara
wersja backendu. Zaktualizuj gałąź i uruchom ponownie `run_ui.py`.

## SSH i SFTP jednocześnie mają timeout

Nie ponawiaj uploadu wielokrotnie. Backend po awarii obu transportów aktywuje
60-sekundowy cooldown. Sprawdź później jednym połączeniem:

```bash
ssh \
  -o BatchMode=yes \
  -o ConnectTimeout=10 \
  -i /Users/glitch/.ssh/id_ed25519 \
  wojgrz4918@ui.wcss.pl \
  'echo WCSS_SSH_OK'
```

Nowy klucz SSH nie omija blokady konta lub adresu IP po stronie WCSS.

## `Resource temporarily unavailable` albo `pthread_create`

To limit procesów lub wątków na węźle logowania. Dla Git używaj jednego
wątku, dla workera podawaj `WCSS_WORKER_PARTITION=lem-cpu-short`, a instalację
środowisk uruchamiaj jako job Slurma.

## `/etc/profile.d/debuginfod.sh: fork: retry`

To komunikat węzła logowania WCSS. Jeżeli rsync kończy się sukcesem i endpoint
zwraca HTTP 200, transfer został wykonany. Jeśli SSH oraz SFTP kończą się
timeoutem, nie wykonuj kolejnych uploadów.

## Callback nie dociera

Sprawdź kolejno:

```text
1. Czy run_ui.py nadal działa?
2. Czy cloudflared nadal działa?
3. Czy publiczne /health zwraca {"status":"ok"}?
4. Czy callback.url zawiera /internal/ml/completed?
5. Czy token na WCSS jest identyczny z backend.callback_token laptopa?
6. Czy worker został uruchomiony ponownie po zmianie URL?
```

Callback wykonuje maksymalnie cztery próby, po maksymalnie pięć sekund, z
łącznym limitem 30 sekund. Błąd callbacku nie usuwa WAV ani JSON z WCSS.

# E. Co wykonuje się tylko raz

Nie trzeba przy każdym uruchomieniu:

- tworzyć środowisk Python,
- instalować zależności npm,
- wykonywać `setup_wcss.sh`,
- instalować `cloudflared`,
- generować nowego callback tokenu,
- ponownie testować modele BS-RoFormer i Demucs.

Codzienne uruchomienie to:

```text
run_ui.py
-> cloudflared
-> aktualizacja callback URL
-> uruchomienie workera
-> upload 5s.wav
-> prompt „wyciągnij wokal”
```
