import hashlib
import os
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID


@dataclass(frozen=True)
class RemoteFile:
    filename: str
    st_mtime: float


class RsyncTransfer:
    def __init__(
        self,
        host: str,
        remote_path: str,
        private_key: str = "",
        port: int = 22,
    ):
        self.host = host
        self.remote_path = remote_path.rstrip("/")
        self.private_key = private_key
        self.port = port
        control_root = Path(tempfile.gettempdir()) / f"soundcraft-ssh-{os.getuid()}"
        control_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        control_root.chmod(0o700)
        identity = f"{host}\0{port}\0{private_key}".encode()
        self.control_path = control_root / hashlib.sha256(identity).hexdigest()[:24]

    def _ssh_options(self) -> list[str]:
        options = [
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=30",
            "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=3",
            "-o", "ControlMaster=auto",
            "-o", "ControlPersist=600",
            "-o", f"ControlPath={self.control_path}",
            "-p", str(self.port),
        ]
        if self.private_key:
            options.extend(["-i", self.private_key])
        return options

    def _ssh_transport(self) -> str:
        return " ".join(shlex.quote(part) for part in ["ssh", *self._ssh_options()])

    def _run_ssh(self, *remote_command: str, capture_output: bool = False):
        command = ["ssh", *self._ssh_options(), self.host]
        command.append(" ".join(shlex.quote(part) for part in remote_command))
        return subprocess.run(
            command,
            check=True,
            capture_output=capture_output,
            text=capture_output,
        )

    def _request_path(self, request_id: str) -> str:
        # Request IDs originate from uuid4. Validation also prevents a remote
        # shell path from ever being constructed from arbitrary input.
        UUID(request_id)
        return f"{self.remote_path}/{request_id}"

    def transfer(self, local_path: Path, remote_dir):
        remote_directory = f"{self.remote_path}/{remote_dir}/"

        command = [
            "rsync",
            "-avz",
            "--partial",
            "--progress",
            "-e",
            self._ssh_transport(),
            str(local_path),
            f"{self.host}:{remote_directory}"
        ]

        subprocess.run(command, check=True)

    def create_request(self, request_id: str):
        request_dir = self._request_path(request_id)
        self._run_ssh(
            "mkdir", "-p",
            f"{request_dir}/input/audio_folder",
            f"{request_dir}/input/prompt_folder",
            f"{request_dir}/output/audio_folder",
            f"{request_dir}/output/agent_response",
        )

    def download(self, remote_folder: str, filename: str, local_path: Path):
        local_path.parent.mkdir(parents=True, exist_ok=True)
        remote_file = f"{self.remote_path}/{remote_folder}/{filename}"
        command = [
            "rsync", "-az", "-e", self._ssh_transport(),
            f"{self.host}:{remote_file}", str(local_path),
        ]
        subprocess.run(command, check=True)

    def list_files(self, remote_folder: str, pattern: str) -> list[RemoteFile]:
        remote_dir = f"{self.remote_path}/{remote_folder}"
        result = self._run_ssh(
            "find", remote_dir, "-maxdepth", "1", "-type", "f",
            "-name", pattern, "-printf", "%f\\t%T@\\n",
            capture_output=True,
        )
        files: list[RemoteFile] = []
        for line in result.stdout.splitlines():
            try:
                filename, modified = line.rsplit("\t", 1)
                files.append(RemoteFile(filename=filename, st_mtime=float(modified)))
            except ValueError:
                continue
        return files

    def delete_request(self, request_id: str):
        self._run_ssh("rm", "-rf", "--", self._request_path(request_id))
