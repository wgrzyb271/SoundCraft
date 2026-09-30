import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_ui
from SoundCraft_backend.app.config import settings


class WindowsRuntimeTests(unittest.TestCase):
    def test_default_request_root_uses_platform_temp_directory(self):
        self.assertEqual(
            Path(settings.local_request_root),
            Path(tempfile.gettempdir()) / "soundcraft-agent-requests",
        )

    def test_launcher_resolves_npm_cmd_on_windows(self):
        def which(command: str):
            return r"C:\Program Files\nodejs\npm.cmd" if command == "npm.cmd" else None

        with patch.object(run_ui.os, "name", "nt"), patch.object(run_ui.shutil, "which", side_effect=which):
            resolved = run_ui._resolve_command("npm")

        self.assertEqual(resolved, r"C:\Program Files\nodejs\npm.cmd")


if __name__ == "__main__":
    unittest.main()
