"""Minimalny klient Slurm współdzielony przez adaptery modeli WCSS."""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path

from .contracts import FailureType


@dataclass(frozen=True)
class Job:
    script_path: str
    work_dir: str | None = None


@dataclass(frozen=True)
class JobResult:
    job_id: str
    success: bool
    status: str
    failure_type: FailureType | None = None
    details: str = ""


class SlurmJobTool:
    def __init__(self, poll_interval_s: float = 5.0):
        self.poll_interval_s = poll_interval_s

    async def _run(self, *command: str) -> tuple[int, str, str]:
        process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return process.returncode or 0, stdout.decode().strip(), stderr.decode().strip()

    async def submit_job(self, job: Job) -> str:
        if not Path(job.script_path).is_file():
            raise FileNotFoundError(f"brak skryptu Slurm: {job.script_path}")
        command = ["sbatch"]
        if job.work_dir:
            command.extend(["--chdir", job.work_dir])
        command.append(job.script_path)
        code, stdout, stderr = await self._run(*command)
        if code:
            raise RuntimeError(f"sbatch failed ({code}): {stderr or stdout}")
        match = re.search(r"Submitted batch job (\d+)", stdout)
        if not match:
            raise RuntimeError(f"nie można odczytać job ID z: {stdout!r}")
        return match.group(1)

    async def _queue_state(self, job_id: str) -> str | None:
        code, stdout, _ = await self._run("squeue", "-h", "-j", job_id, "-o", "%T")
        return None if code else (stdout or None)

    async def _accounting(self, job_id: str) -> JobResult | None:
        code, stdout, _ = await self._run(
            "sacct", "-X", "-j", job_id, "--format=JobID,State,ExitCode", "--noheader", "--parsable2"
        )
        lines = [line for line in stdout.splitlines() if line.strip()]
        if code or not lines:
            return None
        fields = lines[0].split("|")
        if len(fields) < 3:
            return None
        state, exit_code = fields[1].strip().upper(), fields[2].strip()
        if state == "COMPLETED" and exit_code.startswith("0:"):
            return JobResult(job_id, True, state, details="Slurm job completed successfully.")
        mapping: dict[str, FailureType] = {"OUT_OF_MEMORY": "OOM", "TIMEOUT": "TIMEOUT"}
        return JobResult(
            job_id, False, state, mapping.get(state, "RUNTIME_ERROR"),
            f"Slurm job failed: state={state}, exit_code={exit_code}",
        )

    async def wait_for_job(self, job_id: str) -> JobResult:
        active = {"PENDING", "CONFIGURING", "RUNNING", "COMPLETING"}
        while True:
            state = await self._queue_state(job_id)
            if state not in active:
                result = await self._accounting(job_id)
                if result is not None:
                    return result
            await asyncio.sleep(self.poll_interval_s)
