from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path

from orchestrator.contracts import FailureType


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

    async def submit_job(self, job: Job) -> str:
        script = Path(job.script_path)

        if not script.is_file():
            raise FileNotFoundError(
                f"Slurm script does not exist: {script}"
            )

        command = ["sbatch"]

        if job.work_dir:
            command.extend(["--chdir", job.work_dir])

        command.append(str(script))

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        stdout_text = stdout.decode().strip()
        stderr_text = stderr.decode().strip()

        if process.returncode != 0:
            raise RuntimeError(
                f"sbatch failed with exit code {process.returncode}: "
                f"{stderr_text or stdout_text}"
            )

        match = re.search(
            r"Submitted batch job (\d+)",
            stdout_text,
        )

        if not match:
            raise RuntimeError(
                f"Could not parse Slurm job ID from sbatch output: "
                f"{stdout_text!r}"
            )

        return match.group(1)

    async def get_job_state(self, job_id: str) -> str | None:
        process = await asyncio.create_subprocess_exec(
            "squeue",
            "-h",
            "-j",
            job_id,
            "-o",
            "%T",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, _ = await process.communicate()

        if process.returncode != 0:
            return None

        state = stdout.decode().strip()

        return state or None

    @staticmethod
    def map_failure_type(state: str) -> FailureType:
        mapping: dict[str, FailureType] = {
            "OUT_OF_MEMORY": "OOM",
            "TIMEOUT": "TIMEOUT",
            "FAILED": "RUNTIME_ERROR",
            "CANCELLED": "RUNTIME_ERROR",
            "NODE_FAIL": "RUNTIME_ERROR",
            "PREEMPTED": "RUNTIME_ERROR",
        }

        return mapping.get(state, "RUNTIME_ERROR")

    async def get_accounting_result(
        self,
        job_id: str,
    ) -> JobResult | None:

        process = await asyncio.create_subprocess_exec(
            "sacct",
            "-X",
            "-j",
            job_id,
            "--format=JobID,State,ExitCode",
            "--noheader",
            "--parsable2",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            return None

        lines = [
            line.strip()
            for line in stdout.decode().splitlines()
            if line.strip()
        ]

        if not lines:
            return None

        fields = lines[0].split("|")

        if len(fields) < 3:
            return None

        state = fields[1].strip().upper()
        exit_code = fields[2].strip()

        if state == "COMPLETED" and exit_code.startswith("0:"):
            return JobResult(
                job_id=job_id,
                success=True,
                status="COMPLETED",
                details="Slurm job completed successfully.",
            )

        failure_type = self.map_failure_type(state)

        return JobResult(
            job_id=job_id,
            success=False,
            status=state,
            failure_type=failure_type,
            details=(
                f"Slurm job failed: "
                f"state={state}, "
                f"exit_code={exit_code}"
            ),
        )

    async def wait_for_job(self, job_id: str) -> JobResult:
        while True:
            state = await self.get_job_state(job_id)

            if state is None:
                result = await self.get_accounting_result(job_id)

                if result is not None:
                    return result

            elif state in { "PENDING", "CONFIGURING","RUNNING","COMPLETING"}:
                await asyncio.sleep(self.poll_interval_s)
                continue

            else:
                result = await self.get_accounting_result(job_id)

                if result is not None:
                    return result

            await asyncio.sleep(self.poll_interval_s)