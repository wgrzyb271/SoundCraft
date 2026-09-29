# SoundCraft — konfiguracja, demo i uruchomienie na WCSS

## 1. Elementy systemu

- `SoundCraft_frontend` — interfejs React/Vite.
- `SoundCraft_backend` — API FastAPI, upload i pobieranie wyników.
- `llm_agent` — orkiestrator i worker obserwujący katalog żądań na WCSS.
- `agent_bs_roformer`, `demucs`, `agent_sam_audio` — wykonawcy GPU.
- `mixAgent` i `PostProcessing` — obowiązkowy etap po separacji.

`run_ui.py` uruchamia frontend i backend. Worker WCSS jest osobnym procesem,
ponieważ działa na klastrze i wysyła zadania GPU przez `sbatch`.

## 2. Lokalne demo bez WCSS i GPU

W katalogu głównym repozytorium:

```bash
python3 -m venv .venv-ui
source .venv-ui/bin/activate
python -m pip install -r requirements-ui.txt
cd SoundCraft_frontend && npm install && cd ..
python run_ui.py --demo
```

Następnie otwórz `http://127.0.0.1:5173`, wgraj plik audio i użyj np.:

```text
wyciągnij wokal
wyodrębnij dźwięk gitary
zrób wokal głośniej
```

W demo modele GPU są symulowane, ale działają prawdziwe: upload HTTP,
orkiestrator, routing, fallback, `mixAgent`, Pedalboard, `PostProcessing`,
lokalne powiadomienie WebSocket i pobieranie finalnego WAV. Zatrzymanie
`Ctrl+C` kończy oba procesy.

## 3. Prywatny plik konfiguracyjny

```bash
cp llm_agent/config.yaml llm_agent/config.local.yaml
chmod 600 llm_agent/config.local.yaml
```

Uzupełnij `llm_agent/config.local.yaml`:

- `api_keys.deepseek` — klucz DeepSeek do klasyfikacji i efektów miksu;
- `api_keys.huggingface` — token konta z dostępem do SAM Audio;
- `paths.request_root` — katalog żądań na WCSS;
- `wcss` — konto Slurm, QoS i partycja GPU;
- `agents.bs_roformer` — kod agenta, Python, YAML modelu, checkpoint i repo modelu;
- `agents.demucs` — Python Demucs, skrypt agenta i katalog `llm_agent`;
- `agents.sam_audio` — Python SAM Audio, katalog agenta i ID checkpointu;
- `backend` — host rsync/SFTP, zdalny katalog, użytkownik i lokalny klucz SSH.
- `callback` — osiągalny z WCSS URL callbacku i jego token;
- `backend.callback_token` — ten sam token po stronie laptopa.

Ważne zależności ścieżek:

```text
paths.request_root == backend.sftp_remote_path == backend.rsync_remote_path
```

Plik `config.local.yaml` jest ignorowany przez Git. Można utrzymywać dwie
kopie tego samego schematu: lokalną dla backendu i prywatną na WCSS dla
workera. Zmienne środowiskowe mają pierwszeństwo przed YAML.

## 4. Przygotowanie WCSS

Na WCSS sklonuj repozytorium i przygotuj środowisko orkiestratora:

```bash
cd /home/USER
git clone REPOSITORY_URL SoundCraft
cd SoundCraft
python3 -m venv .venv-orchestrator
source .venv-orchestrator/bin/activate
python -m pip install -r llm_agent/requirements.txt
```

Skopiuj prywatną konfigurację na WCSS i popraw wszystkie ścieżki `/home/USER`:

```bash
scp llm_agent/config.local.yaml USER@ui.wcss.pl:/home/USER/SoundCraft/llm_agent/config.local.yaml
ssh USER@ui.wcss.pl chmod 600 /home/USER/SoundCraft/llm_agent/config.local.yaml
```

### BS-RoFormer

Środowisko oraz pliki wskazane w `agents.bs_roformer` muszą zawierać:

- repozytorium modelu,
- konfigurację YAML,
- checkpoint,
- zależności z `agent_bs_roformer/requirements-agent.txt`.

### Demucs

Utwórz osobne środowisko wykonawcze i wskaż jego interpreter w
`agents.demucs.python`:

```bash
python3.11 -m venv /home/USER/venvs/demucs
source /home/USER/venvs/demucs/bin/activate
python -m pip install -r demucs/requirements.txt
```

### SAM Audio Base

Checkpoint jest chroniony. Najpierw zaakceptuj licencję i uzyskaj dostęp do
`facebook/sam-audio-base`, a następnie w środowisku Python 3.11+:

```bash
git clone https://github.com/facebookresearch/sam-audio.git
python3.11 -m venv /home/USER/venvs/sam-audio
source /home/USER/venvs/sam-audio/bin/activate
python -m pip install ./sam-audio
huggingface-cli login
```

Ustaw odpowiednie `agents.sam_audio.python`, `agents.sam_audio.root` oraz
`api_keys.huggingface` w prywatnym YAML.

## 5. Uruchomienie workera na WCSS

```bash
cd /home/USER/SoundCraft
./scripts/submit_wcss_worker.sh
```

Worker obserwuje `paths.request_root`, wybiera model i wysyła zadanie przez
Slurm. Sam worker również działa jako lekki job CPU, a nie jako stały proces na
węźle dostępowym.

Test jednego istniejącego requestu:

```bash
python -m llm_agent.orchestrator.wcss_request \
  /home/USER/backend_files/REQUEST_UUID \
  --config llm_agent/config.local.yaml
```

## 6. Uruchomienie UI połączonego z WCSS

Na komputerze mającym dostęp SSH do WCSS:

```bash
cd SoundCraft
python3 -m venv .venv-ui
source .venv-ui/bin/activate
python -m pip install -r requirements-ui.txt
cd SoundCraft_frontend && npm install && cd ..
python run_ui.py --config llm_agent/config.local.yaml
```

Launcher uruchomi:

- API: `http://127.0.0.1:8000`,
- ograniczony gateway callbacku: `http://127.0.0.1:8001`,
- UI: `http://127.0.0.1:5173`.

Gateway udostępnia wyłącznie `/health` i `/internal/ml/completed`; nie wystawia
uploadu ani pobierania wyników. Do testu callbacku z WCSS można skierować na
port 8001 tymczasowy tunel HTTPS. UI czeka lokalnie przez WebSocket zamiast
odpytywać WCSS.

Jeżeli któryś port jest zajęty, zatrzymaj poprzednie uruchomienie albo wybierz
inne porty jawnie:

```bash
python run_ui.py --demo --backend-port 8010 --frontend-port 5180
```

Launcher nie przełącza portów automatycznie, dzięki czemu frontend zawsze
korzysta z właściwego adresu API.

Backend prześle pliki do `backend.sftp_remote_path`, a działający worker WCSS
odbierze żądanie. `PASSED` publikuje finalny WAV; `FAILED` publikuje tylko JSON
z informacją dla UI.

## 7. Diagnostyka

```bash
# sprawdzenie konfiguracji i jednorazowy skan katalogu
python -m llm_agent.orchestrator.wcss_worker \
  --config llm_agent/config.local.yaml --once

# stan jobów
squeue -u "$USER"
sacct -j JOB_ID --format=JobID,State,ExitCode,Elapsed,MaxRSS

# testy lokalne
python -m unittest -v llm_agent.tests.test_pipeline
npm --prefix SoundCraft_frontend run build
```

Najczęstsze problemy:

- `NO_RESOURCES`/długi `PENDING` — brak zasobów GPU lub zła partycja/QoS;
- `HF 401/403` — brak zaakceptowanego dostępu do checkpointu SAM Audio;
- `FILE_NOT_FOUND` — niezgodne ścieżki w `agents.*`;
- UI stale pokazuje `processing` — worker nie działa albo backend i worker
  wskazują różne katalogi żądań.
