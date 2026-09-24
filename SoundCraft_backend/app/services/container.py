from .rsync import RsyncTransfer
from .sftp import SftpTransfer
from .transfer import TransferService
from ..config import settings

rsync_transfer = RsyncTransfer(
    host=settings.rsync_host,
    remote_path=settings.rsync_remote_path,
)

sftp_transfer = SftpTransfer(
    host=settings.sftp_host,
    username=settings.sftp_username,
    remote_path=settings.sftp_remote_path,
    private_key=settings.sftp_private_key,
)

transfer_service = TransferService(
    rsync_transfer=rsync_transfer,
    sftp_transfer=sftp_transfer,
)