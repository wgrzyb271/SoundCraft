import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from SoundCraft_backend.app.services.rsync import RsyncTransfer
from SoundCraft_backend.app.services.transfer import ResultType, TransferService


class TransferFallbackTests(unittest.TestCase):
    def test_ssh_failure_switches_create_and_list_to_sftp(self):
        sftp = Mock()
        ssh = Mock()
        ssh.create_request.side_effect = RuntimeError("SSH unavailable")
        ssh.list_files.side_effect = RuntimeError("SSH unavailable")
        sftp.list_files.return_value = [SimpleNamespace(filename="response_1.json", st_mtime=1.0)]
        service = TransferService(ssh, sftp)

        request_id = str(uuid4())
        service.create_request(request_id)
        files = service.list_result_files(request_id, ResultType.AGENT_RESPONSE)

        sftp.create_request.assert_called_once_with(request_id)
        sftp.list_files.assert_called_once()
        self.assertEqual(files[0].filename, "response_1.json")

    def test_ssh_is_primary_transport_for_remote_operations(self):
        sftp = Mock()
        ssh = Mock()
        ssh.list_files.return_value = []
        service = TransferService(ssh, sftp)

        request_id = str(uuid4())
        service.create_request(request_id)
        service.list_result_files(request_id, ResultType.AGENT_RESPONSE)

        ssh.create_request.assert_called_once_with(request_id)
        ssh.list_files.assert_called_once()
        sftp.create_request.assert_not_called()
        sftp.list_files.assert_not_called()

    def test_rsync_transport_uses_configured_key_and_port(self):
        transfer = RsyncTransfer(
            "user@ui.wcss.pl", "/home/user/backend_files",
            private_key="/tmp/test-key", port=2222,
        )
        with tempfile.TemporaryDirectory() as temporary, patch("subprocess.run") as run:
            source = Path(temporary) / "audio.wav"
            source.write_bytes(b"RIFF")
            transfer.transfer(source, f"{uuid4()}/input/audio_folder")

        command = run.call_args.args[0]
        self.assertIn("-e", command)
        transport = command[command.index("-e") + 1]
        self.assertIn("/tmp/test-key", transport)
        self.assertIn("2222", transport)
        self.assertIn("ControlMaster=auto", transport)
        self.assertIn("ControlPersist=600", transport)


if __name__ == "__main__":
    unittest.main()
