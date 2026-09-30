# SoundCraft na Windows + wspólne konto WCSS

Ta instrukcja dotyczy laptopa z Windows 10/11. Modele, worker i pliki wynikowe
pozostają na istniejącym koncie WCSS `wojgrz4918`. Na Windows działają frontend,
backend, gateway callbacku i Cloudflare Tunnel.

## 1. Wymagania

Zainstaluj i dodaj do `PATH`:

- Git,
- Python 3.11 lub 3.12,
- Node.js LTS z `npm`,
- Cloudflare `cloudflared`,
- klient OpenSSH (polecenie `ssh`).

Sprawdź w PowerShell:

```powershell
git --version
py --version
npm.cmd --version
ssh -V
cloudflared --version
```

`rsync` nie jest wymagany. Na Windows backend automatycznie używa SFTP.

## 2. Repozytorium i zależności

```powershell
git clone --branch SoundCraftWindows https://github.com/wgrzyb271/SoundCraft.git
Set-Location SoundCraft

Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup_windows.ps1
```

## 3. Test SSH

Klucz publiczny tej osoby musi już znajdować się w
`/home/wojgrz4918/.ssh/authorized_keys` na WCSS. Prywatny klucz pozostaje na jej
laptopie.

```powershell
ssh -i "$HOME\.ssh\id_ed25519" wojgrz4918@ui.wcss.pl
```

Po zalogowaniu `whoami` ma zwrócić `wojgrz4918`. Zakończ sesję poleceniem
`exit`.

## 4. Konfiguracja laptopa

```powershell
$Python = ".\.venv-ui\Scripts\python.exe"
& $Python .\scripts\configure_windows.py `
  --private-key "$HOME\.ssh\id_ed25519"
```

Skrypt zapisze `llm_agent\config.local.yaml` i wyświetli nowy token callbacku.
Token należy przekazać operatorowi WCSS bez publikowania go w repozytorium ani
na publicznym kanale.

## 5. Uruchomienie aplikacji

Pierwszy PowerShell:

```powershell
Set-Location SoundCraft
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\run_windows.ps1
```

Oczekiwane adresy:

```text
UI:               http://127.0.0.1:5173
API:              http://127.0.0.1:8000
Callback gateway: http://127.0.0.1:8001
```

Drugi PowerShell:

```powershell
cloudflared tunnel --url http://127.0.0.1:8001
```

Skopiuj adres `https://....trycloudflare.com` i sprawdź:

```powershell
curl.exe --fail-with-body https://ADRES.trycloudflare.com/health
```

Oczekiwane: `{"status":"ok"}`.

## 6. Przełączenie callbacku na WCSS

Operator WCSS wpisuje nowy URL i ten sam token w:

```text
/home/wojgrz4918/SoundCraft/llm_agent/config.local.yaml
```

```yaml
callback:
  url: "https://ADRES.trycloudflare.com/internal/ml/completed"
  token: "TOKEN_Z_LAPTOPA_WINDOWS"
  request_timeout_s: 5
  total_timeout_s: 30
  max_attempts: 4
  retry_base_s: 2
```

Następnie musi ponownie uruchomić `soundcraft-worker`, ponieważ worker czyta
konfigurację tylko podczas startu:

```bash
squeue -u "$USER" -n soundcraft-worker
scancel NUMER_STAREGO_WORKERA

cd /home/wojgrz4918/SoundCraft
WCSS_WORKER_PARTITION=lem-cpu-short ./scripts/submit_wcss_worker.sh
```

## 7. Test

Otwórz `http://127.0.0.1:5173`, prześlij krótki WAV i wpisz:

```text
Wyciągnij wokal z nagrania i zwróć go jako osobny plik WAV.
```

Przepływ powinien wyglądać następująco:

```text
Windows UI -> Windows backend -> SFTP -> WCSS worker -> GPU
-> wynik na WCSS -> Cloudflare -> Windows gateway -> WebSocket -> UI
```

## 8. Codzienne uruchomienie

1. Uruchom `.\scripts\run_windows.ps1`.
2. Uruchom `cloudflared tunnel --url http://127.0.0.1:8001`.
3. Przekaż operatorowi WCSS nowy URL Quick Tunnel.
4. Zmień `callback.url` i uruchom ponownie worker.
5. Otwórz `http://127.0.0.1:5173`.

## 9. Ważne ograniczenie wspólnego konta

Worker ma jeden globalny URL callbacku. Po przełączeniu go na laptop Windows
callbacki nie będą trafiały na poprzedni laptop. Obecny wariant zakłada pracę
jednej osoby naraz. Jednoczesna praca wielu laptopów wymaga callbacku zapisanego
osobno dla każdego requestu albo wspólnego, stale dostępnego backendu.

## 10. Zatrzymanie

W PowerShell z aplikacją i Cloudflare naciśnij `Ctrl+C`. Launcher Windows zamyka
backend, gateway oraz całe drzewo procesu `npm`/Vite, aby porty nie pozostały
zajęte.
