from .sftp import SftpTransfer
from .rsync import RsyncTransfer
from enum import Enum
import time

class UploadType(Enum):
    AUDIO = "audio"
    PROMPT = "prompt"

class ResultType(Enum):
    AUDIO="audio"
    AGENT_RESPONSE="agent response"
class TransferService:
    def __init__(
        self,
        rsync_transfer: RsyncTransfer,
        sftp_transfer: SftpTransfer,
        failure_cooldown_s: float = 60.0,
    ):
        self.rsync=rsync_transfer
        self.sftp=sftp_transfer
        self.failure_cooldown_s = failure_cooldown_s
        self._unavailable_until = 0.0

    def _sftp_fallback(self, operation: str, error: Exception):
        print(f"SSH/rsync {operation} failed, trying SFTP fallback: {error}")

    def _ensure_available(self):
        remaining = self._unavailable_until - time.monotonic()
        if remaining > 0:
            raise RuntimeError(
                f"WCSS transport cooling down after connection failure ({remaining:.0f}s remaining)"
            )

    def _run_with_fallback(self, operation, primary, fallback):
        self._ensure_available()
        try:
            return primary()
        except Exception as primary_error:
            self._sftp_fallback(operation, primary_error)
            try:
                return fallback()
            except Exception as fallback_error:
                self._unavailable_until = time.monotonic() + self.failure_cooldown_s
                raise RuntimeError(
                    f"Both SSH/rsync and SFTP failed for {operation}; "
                    f"retry allowed after {self.failure_cooldown_s:.0f}s"
                ) from fallback_error

    def transfer(self, file_path, request_id, upload_type: UploadType):
        match upload_type:
            case UploadType.AUDIO:
                remote_folder = f"{request_id}/input/audio_folder"
            case UploadType.PROMPT:
                remote_folder = f"{request_id}/input/prompt_folder"
            case _:
                raise ValueError("invalid upload data type")
        print(f"REMOTE_FOLDER: {remote_folder}")
        def primary():
            self.rsync.transfer(file_path, remote_folder)
            return {
                "method": "rsync",
                "success": True
            }

        def fallback():
            self.sftp.transfer(file_path, remote_folder)
            return {
                "method": "sftp",
                "success": True
            }

        return self._run_with_fallback("upload", primary, fallback)
    
    def download_result(self,request_id,filename,local_path, result_type:ResultType):
        match result_type:
            case ResultType.AUDIO:
                remote_folder=f"{request_id}/output/audio_folder"
            case ResultType.AGENT_RESPONSE:
                remote_folder=f"{request_id}/output/agent_response"
            case _:
                raise ValueError("invalid result data type")
        return self._run_with_fallback(
            "download",
            lambda: self.rsync.download(remote_folder, filename, local_path),
            lambda: self.sftp.download(remote_folder, filename, local_path),
        )

    def create_request(self,request_id: str):
        return self._run_with_fallback(
            "create",
            lambda: self.rsync.create_request(request_id),
            lambda: self.sftp.create_request(request_id),
        )

    def delete_request(self, request_id:str):
        return self._run_with_fallback(
            "delete",
            lambda: self.rsync.delete_request(request_id),
            lambda: self.sftp.delete_request(request_id),
        )

    def list_result_files(self, request_id:str, result_type:ResultType):
        match result_type:
            case ResultType.AUDIO:
                remote_folder=f"{request_id}/output/audio_folder"
                pattern="changed_audio_*.wav"
            case ResultType.AGENT_RESPONSE:
                remote_folder=f"{request_id}/output/agent_response"
                pattern="response_*.json"
            case _:
                raise ValueError("invalid result data type")
        print(f"RESULT REMOTE FOLDER: {remote_folder}")
        print(f"RESULT FILE PATTERN: {pattern}")

        return self._run_with_fallback(
            "list",
            lambda: self.rsync.list_files(remote_folder, pattern),
            lambda: self.sftp.list_files(remote_folder, pattern),
        )
