# SoundCraft na WCSS — odtworzenie środowiska

Poniższe komendy są przygotowane dla konta `wojgrz4918`. Wszystko na WCSS
pozostaje w `/home/wojgrz4918`; środowiska i cache są w
`/home/wojgrz4918/tmp`.

## Podział systemu

Laptop uruchamia wyłącznie `SoundCraft_frontend` i `SoundCraft_backend`.
Backend wysyła request przez SSH/SFTP do `/home/USER/backend_files`.

WCSS uruchamia `llm_agent`, modele GPU, `mixAgent` i `PostProcessing`.
Worker obserwuje katalog requestów i wysyła inferencję do Slurma.

## Wymagane katalogi

Wszystkie pliki są przechowywane w katalogu domowym użytkownika:

```text
/home/wojgrz4918/SoundCraft
/home/wojgrz4918/backend_files
/home/wojgrz4918/tmp/venvs
/home/wojgrz4918/tmp/cache
/home/wojgrz4918/tmp/logs
```

Skrypt odmawia pracy, jeżeli `TMPDIR` wskazuje poza katalog domowy.

## Automatyczna instalacja

Domyślny, działający wariant bez SAM Audio:

```bash
cd /home/wojgrz4918/SoundCraft
chmod 700 scripts/setup_wcss.sh
./scripts/setup_wcss.sh --without-sam
```

Skrypt tworzy lub aktualizuje środowiska:

- `orchestrator` — `llm_agent`, `mixAgent`, Pedalboard i PostProcessing;
- `bs-roformer` — PyTorch 2.4.1 oraz zależności BS-RoFormer;
- `demucs` — PyTorch 2.4.1, Demucs 4.0.1 i Pydantic.

Nie pobiera checkpointu BS-RoFormer. Oczekuje istniejących plików:

```text
/home/wojgrz4918/bs_roformer/model_files/config_bs_roformer_384_8_2_485100.yaml
/home/wojgrz4918/bs_roformer/model_files/model_bs_roformer_ep_17_sdr_9.6568.ckpt
/home/wojgrz4918/bs_roformer/Music-Source-Separation-Training
```

Opcjonalny wariant instalujący również SAM Audio:

```bash
./scripts/setup_wcss.sh --with-sam
```

Instalacja SAM używa Pythona 3.11, PyTorch 2.6, TorchCodec 0.2.1 oraz
FFmpeg 6.1 w katalogu domowym. SAM wymaga zaakceptowanego dostępu do
`facebook/sam-audio-base`. Tryb bez SAM pozostaje w pełni użyteczny dla
klasycznych stemów.

## Konfiguracja prywatna

Plik `llm_agent/config.local.yaml` nie jest wersjonowany. Powinien wskazywać:

```yaml
paths:
  models_yaml: models.yaml
  user_root: /home/wojgrz4918/tmp/soundcraft/users
  request_root: /home/wojgrz4918/backend_files

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
```

Jeżeli SAM jest aktywny, sekcja `env` musi zawierać:

```yaml
env:
  LD_LIBRARY_PATH: /home/wojgrz4918/tmp/ffmpeg-env/lib
```

Tokeny DeepSeek i Hugging Face wpisuje się wyłącznie do prywatnego YAML.
Uprawnienia pliku:

```bash
chmod 600 llm_agent/config.local.yaml
```

## Worker jako zadanie Slurm

Workera nie uruchamiamy jako stałego procesu na węźle `ui`. Skrypt wybiera
dostępną partycję CPU (`lem-cpu-short`, a następnie `lem-cpu`) i wysyła go do
Slurma. Job ma limit `2-23:00:00`, zgodny z limitem trzech dni partycji
`lem-cpu-short`:

```bash
cd /home/wojgrz4918/SoundCraft
chmod 700 scripts/submit_wcss_worker.sh scripts/wcss_worker.sbatch
./scripts/submit_wcss_worker.sh
```

Jeżeli automatyczne wykrywanie partycji nie znajdzie właściwej kolejki, podaj ją
jawnie na podstawie `sinfo`:

```bash
sinfo -o '%P %a %l %D'
WCSS_WORKER_PARTITION=NAZWA_PARTYCJI ./scripts/submit_wcss_worker.sh
```

Status i logi:

```bash
squeue -j JOB_ID
cat /home/wojgrz4918/tmp/logs/soundcraft-worker-JOB_ID.out
cat /home/wojgrz4918/tmp/logs/soundcraft-worker-JOB_ID.err
```

Worker korzysta z pełnej ścieżki
`/home/wojgrz4918/tmp/venvs/orchestrator/bin/python` i wcześniej ładuje moduł
`Python/3.11.5-GCCcore-13.2.0`. Nie wymaga `source .../activate`. Brak tekstu w
logu przy pustej kolejce jest prawidłowy.

Zatrzymanie workera:

```bash
scancel JOB_ID
```

## Test bez SAM Audio

Na laptopie plik `llm_agent/config.local.yaml` może zawierać pełną konfigurację,
ale sekcja używana przez backend musi wyglądać tak:

```yaml
backend:
  rsync_host: wojgrz4918@ui.wcss.pl
  rsync_remote_path: /home/wojgrz4918/backend_files
  sftp_host: ui.wcss.pl
  sftp_username: wojgrz4918
  sftp_remote_path: /home/wojgrz4918/backend_files
  sftp_private_key: /Users/glitch/.ssh/id_ed25519
  sftp_port: 22
  processing_ttl: 5400
  callback_token: "TEN_SAM_LOSOWY_TOKEN_CO_NA_WCSS"
  completion_wait_timeout: 5400
```

Po zakończeniu pipeline'u worker WCSS wysyła pojedyncze, uwierzytelnione
powiadomienie HTTP. Backend przekazuje je do UI przez WebSocket, dlatego UI nie
odpytuje cyklicznie WCSS. URL callbacku musi być osiągalny z węzłów WCSS —
`127.0.0.1` i adres LAN laptopa zwykle nie zadziałają.

Konfiguracja na WCSS:

```yaml
callback:
  url: https://PUBLICZNY-LUB-TUNELOWANY-ADRES/internal/ml/completed
  token: "TEN_SAM_LOSOWY_TOKEN_CO_NA_LAPTOPIE"
  request_timeout_s: 5
  total_timeout_s: 30
  max_attempts: 4
  retry_base_s: 2
```

Callback próbuje maksymalnie cztery razy, z opóźnieniem wykładniczym, ale kończy
wszystkie próby po 30 sekundach. Błąd callbacku nie usuwa wyniku — JSON i WAV
pozostają w katalogu requestu na WCSS.

Przed testem modelu sprawdź callback z WCSS:

```bash
curl --fail-with-body \
  -H "Authorization: Bearer TEN_SAM_LOSOWY_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"request_id":"11111111-1111-4111-8111-111111111111","execution_code":"PASSED","audio_ready":true}' \
  https://PUBLICZNY-LUB-TUNELOWANY-ADRES/internal/ml/completed
```

Oczekiwany wynik: `{"status":"accepted", ...}`. Nie uruchamiaj produkcyjnego
testu, dopóki ten request nie przechodzi z węzła WCSS.

Do krótkiego testu można wystawić wyłącznie gateway na porcie 8001 przez
Cloudflare Quick Tunnel:

```bash
# osobny terminal na laptopie, po uruchomieniu run_ui.py
brew install cloudflared
cloudflared tunnel --url http://127.0.0.1:8001
```

Skopiuj wygenerowany adres `https://...trycloudflare.com` do `callback.url`.
Quick Tunnel jest przeznaczony tylko do testów i nie ma gwarancji dostępności;
do stałego wdrożenia użyj kontrolowanego, stabilnego endpointu HTTPS. Po teście
zatrzymaj tunel przez `Ctrl+C`.

Najpierw sprawdź z laptopa połączenie i dostęp do katalogu:

```bash
ssh -i /Users/glitch/.ssh/id_ed25519 wojgrz4918@ui.wcss.pl \
  'test -d /home/wojgrz4918/backend_files && echo WCSS_CONNECTION_OK'
```

Na laptopie uruchom frontend i backend bez flagi `--demo`:

```bash
cd /Users/LOCAL_USER/Desktop/SoundCraft
source .venv-ui/bin/activate
python run_ui.py --config llm_agent/config.local.yaml
```

Dla tego projektu dokładna pierwsza linia to:

```bash
cd /Users/glitch/Desktop/SoundCraft
```

Do testu użyj promptu klasy A, na przykład:

```text
wyciągnij wokal
```

Routing dla klasycznych stemów to:

```text
BS-RoFormer -> Demucs (fallback) -> mixAgent -> PostProcessing
```

Brak SAM Audio nie wpływa na tę ścieżkę. Prompt otwarty, na przykład
`wyodrębnij dźwięk gitary`, zakończy się błędem do czasu uruchomienia SAM.
Nie uruchamiaj laptopowego UI z `--demo`, bo ta flaga omija WCSS.

Po uploadzie frontend utrzymuje jeden WebSocket do lokalnego backendu. Nie ma
pollingu SSH. Dopiero po callbacku backend jednokrotnie pobiera response JSON, a
dla `PASSED` także finalny WAV.

## Zweryfikowane wersje

| Komponent | Python | Wersje | Status |
|---|---:|---|---|
| Orkiestrator i callback | 3.11 | wymagania `llm_agent/requirements.txt` | testy 19/19 |
| BS-RoFormer | 3.10.4 | torch/torchaudio 2.4.1+cu121 | H100, model załadowany |
| Demucs | 3.11.5 | torch/torchaudio 2.4.1+cu121, Demucs 4.0.1 | H100, model załadowany |
| SAM Audio Base | 3.11.5 | torch 2.6, TorchCodec 0.2.1, FFmpeg 6.1 | opcjonalny, w trakcie walidacji |

## Diagnostyka Slurma

```bash
squeue -u "$USER"
sacct -j JOB_ID --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS
```

Logi generowane przez pipeline znajdują się w katalogu `work` danego requestu
oraz w `/home/USER/tmp/logs` dla samodzielnych testów modeli.
