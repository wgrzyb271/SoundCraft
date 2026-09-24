import subprocess
from pathlib import Path


class RsyncTransfer:
    def __init__(self, host: str, remote_path: str):
        self.host = host
        self.remote_path = remote_path

    def transfer(self, local_path: Path, remote_dir):
        remote_directory = f"{self.remote_path}/{remote_dir}/"

        command = [
            "rsync",
            "-avz",
            "--partial",
            "--progress",
            str(local_path),
            f"{self.host}:{remote_directory}"
        ]

        subprocess.run(command, check=True)