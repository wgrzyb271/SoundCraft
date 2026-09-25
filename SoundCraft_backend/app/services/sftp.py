import paramiko
from pathlib import Path

class SftpTransfer():
    def __init__(self, host:str, username:str, remote_path:str,private_key:str, port:int=22):
        self.host = host
        self.username=username
        self.remote_path=remote_path
        self.private_key=private_key
        self.port=port

        print("=== SFTP CONFIG ===")
        print(f"host: {self.host}")
        print(f"username: {self.username}")
        print(f"remote_path: {self.remote_path}")
        print(f"port: {self.port}")

    def connect(self):
        key = paramiko.Ed25519Key.from_private_key_file(self.private_key)
       
        transport = paramiko.Transport((self.host, self.port))
        transport.connect(username=self.username,pkey=key)

        sftp = paramiko.SFTPClient.from_transport(transport)

        return transport,sftp 

    def mkdir_if_not_exists(self,sftp,path:str):
        try:
            sftp.stat(path)
        except FileNotFoundError:
            sftp.mkdir(path)

    def create_request(self,request_id:str):
        transport, sftp = self.connect()
        try:
            request_dir = (
                f"{self.remote_path}/request_{request_id}"
            )
            input_dir = f"{request_dir}/input"
            output_dir = f"{request_dir}/output"

            self.mkdir_if_not_exists(sftp, request_dir)
            self.mkdir_if_not_exists(sftp, input_dir)
            self.mkdir_if_not_exists(sftp, output_dir)

        finally:
            sftp.close()
            transport.close()
    

    def transfer(self, local_path:Path,request_id:str):

        transport, sftp = self.connect()
        try:
            remote_file = (f"{self.remote_path}/"f"request_{request_id}/"f"input/"f"{local_path.name}")
            sftp.put(str(local_path),remote_file)

        finally:
            sftp.close()
            transport.close()

    def download(self, request_id:str, filename,local_path):
        print("=== SFTP DOWNLOAD INPUT ===")
        print(f"request_id: {request_id}")
        print(f"filename: {filename}")
        print(f"remote_path: {self.remote_path}")
        transport,sftp = self.connect()
        try:
            remote_file = (f"{self.remote_path}/"f"request_{request_id}/"f"output/"f"{filename}")
            print(f"SFTP DOWNLOAD: {remote_file}")

            sftp.get(remote_file,str(local_path))
        finally:
            sftp.close()
            transport.close()

    def delete_request(self, request_id: str):
        transport, sftp = self.connect()

        try:
            request_dir = (f"{self.remote_path}/request_{request_id}")
            self.remove_directory_recursive(sftp,request_dir)

        finally:
            sftp.close()
            transport.close()

    def remove_directory_recursive(self, sftp, path: str):

        for item in sftp.listdir_attr(path):
            item_path = f"{path}/{item.filename}"

            if item.st_mode & 0o40000:
                self.remove_directory_recursive(sftp,item_path,)
            else:
                sftp.remove(item_path)

        sftp.rmdir(path)