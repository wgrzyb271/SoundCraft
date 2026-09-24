"""Etap DeployPipeline. Realnie: narzędzie MCP `deploy_user_pipeline` (tworzy katalog użytkownika,
przenosi WAV, zapisuje prompt.txt). Przesyłanie danych z frontendu jest POZA zakresem tego modułu."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol


class DeployError(RuntimeError):
    """Błąd wdrożenia plików. `code`: np. FILE_NOT_FOUND, BAD_FILE_TYPE, DISK_QUOTA."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class DeployFn(Protocol):
    async def __call__(self, username: str, temp_audio_path: str, prompt_text: str) -> str:
        """Zwraca `user_dir` (katalog zadania na zasobach WCSS)."""


def make_local_stub_deploy(user_root: str) -> DeployFn:
    """Stub lokalny (mock): tylko waliduje plik i buduje `user_dir` z `username`. Nic nie kopiuje."""

    async def _deploy(username: str, temp_audio_path: str, prompt_text: str) -> str:
        p = Path(temp_audio_path)
        if not p.is_file():
            raise DeployError("FILE_NOT_FOUND", f"brak pliku {temp_audio_path}")
        if p.suffix.lower() != ".wav":
            raise DeployError("BAD_FILE_TYPE", "oczekiwano pliku .wav")
        return os.path.join(user_root, username)

    return _deploy
