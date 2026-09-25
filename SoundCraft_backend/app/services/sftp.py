import paramiko
from pathlib import Path
from fnmatch import fnmatch

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
                f"{self.remote_path}/{request_id}"
            )
            input_dir = f"{request_dir}/input"
            output_dir = f"{request_dir}/output"

            audio_in_dir = f"{input_dir}/audio_folder"
            prompt_dir = f"{input_dir}/prompt_folder"

            audio_out_dir = f"{output_dir}/audio_folder"
            agent_response_dr = f"{output_dir}/agent_response"

            self.mkdir_if_not_exists(sftp, request_dir)
            self.mkdir_if_not_exists(sftp, input_dir)
            self.mkdir_if_not_exists(sftp, output_dir)
            self.mkdir_if_not_exists(sftp, audio_in_dir)
            self.mkdir_if_not_exists(sftp, prompt_dir)
            self.mkdir_if_not_exists(sftp, audio_out_dir)
            self.mkdir_if_not_exists(sftp, agent_response_dr)


        finally:
            sftp.close()
            transport.close()
    

    def transfer(self, local_path:Path,remote_folder:str):

        transport, sftp = self.connect()
        try:
            remote_file = (f"{self.remote_path}/"f"{remote_folder}/"f"{local_path.name}")
            sftp.put(str(local_path),remote_file)

        finally:
            sftp.close()
            transport.close()

    def download(self, remote_folder: str, filename: str, local_path: Path):
        print("=== SFTP DOWNLOAD INPUT ===")
        print(f"remote_folder: {remote_folder}")
        print(f"filename: {filename}")
        print(f"local_path: {local_path}")

        transport,sftp = self.connect()
        try:
            remote_file = (f"{self.remote_path}/"f"{remote_folder}/"f"{filename}")
            print(f"SFTP DOWNLOAD: {remote_file}")

            sftp.get(remote_file,str(local_path))
        finally:
            sftp.close()
            transport.close()

    def delete_request(self, request_id: str):
        transport, sftp = self.connect()

        try:
            request_dir = (f"{self.remote_path}/{request_id}")
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

    def list_files(self, remote_folder:str, pattern:str):
        transport, sftp = self.connect()
        try:
            remote_dir = (f"{self.remote_path}/"f"{remote_folder}")
            print("=== SFTP LIST FILES ===")
            print(f"remote_path: {self.remote_path}")
            print(f"remote_folder: {remote_folder}")
            print(f"remote_dir: {remote_dir}")
            print(f"pattern: {pattern}")

            items = sftp.listdir_attr(remote_dir)

            print("FILES ON SERVER:")
            for item in items:
                print(f"  {item.filename} | mtime={item.st_mtime}")
            files = [item for item in sftp.listdir_attr(remote_dir) if fnmatch(item.filename,pattern)]
            return files
        finally:
            sftp.close()
            transport.close()