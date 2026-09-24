from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    rsync_host:str
    rsync_remote_path:str

    sftp_host:str
    sftp_username:str
    sftp_remote_path:str
    sftp_private_key:str
    sftp_port:int=22

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()