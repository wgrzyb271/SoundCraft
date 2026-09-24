import paramiko
from pathlib import Path

class SftpTransfer():
    def __init__(self, host:str, username:str, remote_path:str,private_key:str, port:int=22):
        self.host = host
        self.username=username
        self.remote_path=remote_path
        self.private_key=private_key
        self.port=port

    def create_directory(self, remote_dir):
            key = paramiko.Ed25519Key.from_private_key_file(
                self.private_key
            )

            transport = paramiko.Transport((self.host, self.port))
            transport.connect(
                username=self.username,
                pkey=key
            )

            sftp = paramiko.SFTPClient.from_transport(transport)

            remote_directory = f"{self.remote_path}/{remote_dir}"

            print("REMOTE PATH:", self.remote_path)
            print("REMOTE DIR:", remote_dir)
            print("FULL PATH:", remote_directory)

            try:
                sftp.stat(remote_directory)
            except FileNotFoundError:
                sftp.mkdir(remote_directory)

            sftp.close()
            transport.close()

    def transfer(self, local_path:Path,remote_dir):
        key = paramiko.Ed25519Key.from_private_key_file(self.private_key)
        transport = paramiko.Transport((self.host, self.port))
        transport.connect(username=self.username,pkey=key)

        sftp = paramiko.SFTPClient.from_transport(transport)
        remote_file = f"{self.remote_path}/{remote_dir}/{local_path.name}"
        sftp.put(str(local_path),remote_file)

        sftp.close()
        transport.close()

    def download(self, remote_dir, filename,local_path):
        key = paramiko.Ed25519Key.from_private_key_file(self.private_key)

        transport = paramiko.Transport((self.host, self.port))
        transport.connect(username=self.username,pkey=key)

        sftp = paramiko.SFTPClient.from_transport(transport)
        remote_file = f"{self.remote_path}/{remote_dir}/{filename}"

        sftp.get(remote_file,str(local_path))

        sftp.close()
        transport.close()