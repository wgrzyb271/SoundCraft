from .sftp import SftpTransfer
from .rsync import RsyncTransfer

class TransferService:
    def __init__(self, rsync_transfer:RsyncTransfer, sftp_transfer:SftpTransfer):
        self.rsync=rsync_transfer
        self.sftp=sftp_transfer

    def create_directory(self, remote_dir):
        self.sftp.create_directory(remote_dir)

    def transfer(self, file_path, remote_dir):

    
        try:
            self.rsync.transfer(file_path,remote_dir)
            return {
                "method": "rsync",
                "success": True
                }
        
        except Exception as rsync_error:
            print(f"rsync failed: {rsync_error}")
            try:
                self.sftp.transfer(file_path,remote_dir)
                return {
                    "method":"sftp",
                    "success":True
                }
            except Exception as sftp_error:
                print(f"sftp failed: {sftp_error}")
                raise RuntimeError("Both rsync and sftp failed") from sftp_error
    
    def download_result(self,request_id,filename,local_path):
        remote_dir = f"output/request{request_id}"
        self.sftp.download(remote_dir,filename,local_path)