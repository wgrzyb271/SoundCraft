#!/usr/bin/env python3
"""Create the laptop-only SoundCraft configuration on Windows."""
from __future__ import annotations

import argparse
import secrets
from pathlib import Path

import yaml


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Configure a Windows laptop for SoundCraft + WCSS")
    parser.add_argument("--private-key", default=str(Path.home() / ".ssh" / "id_ed25519"))
    parser.add_argument("--wcss-user", default="wojgrz4918")
    parser.add_argument("--wcss-host", default="ui.wcss.pl")
    parser.add_argument("--remote-root", default="/home/wojgrz4918/backend_files")
    parser.add_argument("--callback-token", default="")
    parser.add_argument("--output", default=str(project_root / "llm_agent" / "config.local.yaml"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    private_key = Path(args.private_key).expanduser().resolve()
    if not private_key.is_file():
        parser.error(f"SSH private key does not exist: {private_key}")

    output = Path(args.output).expanduser().resolve()
    if output.exists() and not args.force:
        parser.error(f"configuration already exists: {output} (use --force to replace it)")

    callback_token = args.callback_token or secrets.token_hex(32)
    data = {
        "backend": {
            "rsync_host": f"{args.wcss_user}@{args.wcss_host}",
            "rsync_remote_path": args.remote_root,
            "sftp_host": args.wcss_host,
            "sftp_username": args.wcss_user,
            "sftp_remote_path": args.remote_root,
            "sftp_private_key": str(private_key),
            "sftp_port": 22,
            "processing_ttl": 5400,
            "callback_token": callback_token,
            "completion_wait_timeout": 5400,
        }
    }

    temporary = output.with_suffix(".yaml.tmp")
    temporary.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    temporary.replace(output)
    try:
        output.chmod(0o600)
    except OSError:
        pass

    print(f"Configuration: {output}")
    print(f"SSH key: {private_key}")
    print("\nSAVE THIS CALLBACK TOKEN AND SEND IT SECURELY TO THE WCSS OPERATOR:")
    print(callback_token)


if __name__ == "__main__":
    main()
