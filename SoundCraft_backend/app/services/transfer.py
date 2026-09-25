from .sftp import SftpTransfer
from .rsync import RsyncTransfer
from enum import Enum

class UploadType(Enum):
    AUDIO = "audio"
    PROMPT = "prompt"

class ResultType(Enum):
    AUDIO="audio"
    AGENT_RESPONSE="agent response"
class TransferService:
    def __init__(self, rsync_transfer:RsyncTransfer, sftp_transfer:SftpTransfer):
        self.rsync=rsync_transfer
        self.sftp=sftp_transfer

    def transfer(self, file_path, request_id, upload_type: UploadType):
        match upload_type:
            case UploadType.AUDIO:
                remote_folder = f"{request_id}/input/audio_folder"
            case UploadType.PROMPT:
                remote_folder = f"{request_id}/input/prompt_folder"
            case _:
                raise ValueError("invalid upload data type")
        print(f"REMOTE_FOLDER: {remote_folder}")
        try:
            self.rsync.transfer(file_path, remote_folder)
            return {
                "method": "rsync",
                "success": True
                }
        
        except Exception as rsync_error:
            print(f"rsync failed: {rsync_error}")
            try:
                self.sftp.transfer(file_path,remote_folder)
                return {
                    "method":"sftp",
                    "success":True
                }
            except Exception as sftp_error:
                print(f"sftp failed: {sftp_error}")
                raise RuntimeError("Both rsync and sftp failed") from sftp_error
    
    def download_result(self,request_id,filename,local_path, result_type:ResultType):
        match result_type:
            case ResultType.AUDIO:
                remote_folder=f"{request_id}/output/audio_folder"
            case ResultType.AGENT_RESPONSE:
                remote_folder=f"{request_id}/output/agent_response"
            case _:
                raise ValueError("invalid result data type")
        self.sftp.download(remote_folder, filename, local_path)

    def create_request(self,request_id: str):
        self.sftp.create_request(request_id)

    def delete_request(self, request_id:str):
        self.sftp.delete_request(request_id)

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

        return self.sftp.list_files(remote_folder,pattern)