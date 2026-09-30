import os
import tempfile
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    rsync_host:str = ""
    rsync_remote_path:str = ""

    sftp_host:str = ""
    sftp_username:str = ""
    sftp_remote_path:str = ""
    sftp_private_key:str = ""
    sftp_port:int=22
    processing_ttl:int = 5400 #in sec
    callback_token:str = ""
    completion_wait_timeout:float = 5400.0
    local_request_root:str = str(Path(tempfile.gettempdir()) / "soundcraft-agent-requests")

    model_config = SettingsConfigDict(
        env_file=(".env",".config"),
        env_file_encoding="utf-8"
    )


def _yaml_backend_settings() -> dict[str, Any]:
    configured = os.environ.get("SOUNDCRAFT_CONFIG")
    if not configured:
        return {}
    path = Path(configured).expanduser()
    if not path.is_file():
        raise RuntimeError(f"SOUNDCRAFT_CONFIG does not exist: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    backend = data.get("backend") or {}
    if not isinstance(backend, dict):
        raise RuntimeError("SOUNDCRAFT_CONFIG: 'backend' must be a mapping")
    if backend.get("sftp_private_key"):
        backend["sftp_private_key"] = str(Path(str(backend["sftp_private_key"])).expanduser())
    return backend


settings = Settings(**_yaml_backend_settings())


def is_demo_mode() -> bool:
    return os.environ.get("SOUNDCRAFT_DEMO", "").strip().lower() in {"1", "true", "yes", "on"}
