"""Adaptery BS-RoFormer, Demucs i SAM Audio Base do kontraktu orkiestratora.

Oba adaptery uruchamiają właściwą inferencję jako zadanie Slurm na WCSS. Dzięki
temu proces orkiestratora nie ładuje modeli ani CUDA na węźle logowania.
"""
from __future__ import annotations

import os
import shlex
import textwrap
from pathlib import Path
from typing import Any

from .contracts import AgentReport, AgentTask
from .slurm import Job, SlurmJobTool


class WcssSlurmAgent:
    name: str
    model: str
    supported_categories = frozenset({"A"})
    python_module = "Python/3.10.4-GCCcore-11.3.0"

    def __init__(self, job_tool: SlurmJobTool | None = None):
        self.job_tool = job_tool or SlurmJobTool()

    def _input_path(self, task: AgentTask) -> Path:
        return Path(task.user_dir) / "input" / "audio_folder" / "audio.wav"

    def _work_dir(self, task: AgentTask) -> Path:
        return Path(task.user_dir) / "work" / self.model

    def _script_body(self, task: AgentTask, input_path: Path, output_dir: Path) -> str:
        raise NotImplementedError

    def _result_dir(self, output_dir: Path) -> Path:
        return output_dir

    async def run(self, task: AgentTask) -> AgentReport:
        params = {"executor": "slurm", "model": self.model}
        if task.category not in self.supported_categories:
            return AgentReport(
                agent=self.name, status="FAILED", failure_type="UNSUPPORTED_TASK",
                details=f"{self.name} obsługuje wyłącznie klasyczne stemy", attempted_params=params,
            )
        try:
            input_path = self._input_path(task)
            if not input_path.is_file():
                raise FileNotFoundError(f"brak pliku wejściowego: {input_path}")
            work_dir = self._work_dir(task)
            output_dir = work_dir / "stems"
            jobs_dir = work_dir / "jobs"
            output_dir.mkdir(parents=True, exist_ok=True)
            jobs_dir.mkdir(parents=True, exist_ok=True)
            script_path = jobs_dir / f"attempt_{task.attempt_no}.sh"
            script_path.write_text(self._script_body(task, input_path, output_dir), encoding="utf-8")
            script_path.chmod(0o750)

            job_id = await self.job_tool.submit_job(Job(str(script_path), str(work_dir)))
            result = await self.job_tool.wait_for_job(job_id)
            if not result.success:
                return AgentReport(
                    agent=self.name, status="FAILED", job_id=result.job_id,
                    failure_type=result.failure_type or "RUNTIME_ERROR", details=result.details,
                    attempted_params=params,
                )
            result_dir = self._result_dir(output_dir)
            missing = self._missing_outputs(result_dir)
            if missing:
                raise RuntimeError(f"brak stemów po zadaniu Slurm: {', '.join(missing)}")
            return AgentReport(
                agent=self.name, status="SUCCESS", job_id=result.job_id,
                output_path=str(result_dir), details=f"{self.model} zakończony na WCSS",
                attempted_params=params,
            )
        except Exception as exc:  # noqa: BLE001
            return AgentReport(
                agent=self.name, status="FAILED", failure_type="RUNTIME_ERROR",
                details=str(exc)[:600], attempted_params=params,
            )

    def _missing_outputs(self, result_dir: Path) -> list[str]:
        return [s for s in ("vocals", "drums", "bass", "other")
                if not (result_dir / f"{s}.wav").is_file()]

    def _header(self, job_name: str, stdout: Path) -> str:
        account = os.environ.get("WCSS_SLURM_ACCOUNT", "hpc-danbor2008-1756464546")
        qos = os.environ.get("WCSS_SLURM_QOS", account)
        partition = os.environ.get("WCSS_SLURM_PARTITION", "lem-gpu-short")
        python_module = os.environ.get("WCSS_PYTHON_MODULE", self.python_module)
        return textwrap.dedent(f"""\
            #!/bin/bash -l
            #SBATCH --job-name={job_name}
            #SBATCH --account={account}
            #SBATCH --qos={qos}
            #SBATCH --nodes=1
            #SBATCH --ntasks-per-node=1
            #SBATCH --gres=gpu:hopper:1
            #SBATCH --cpus-per-task=4
            #SBATCH --mem=16G
            #SBATCH --partition={partition}
            #SBATCH --time=01:00:00
            #SBATCH --output={stdout}/slurm-%j.out
            #SBATCH --error={stdout}/slurm-%j.err

            set -euo pipefail
            source /etc/profile
            module load {python_module}
            """)


class WcssBSRoformerAgent(WcssSlurmAgent):
    name = "agent_bs_roformer"
    model = "bs_roformer"

    def _script_body(self, task: AgentTask, input_path: Path, output_dir: Path) -> str:
        project = Path(os.environ.get("BS_ROFORMER_AGENT_ROOT", "/home/wojgrz4918/agent_bs_roformer"))
        config = os.environ.get(
            "BS_ROFORMER_CONFIG",
            "/home/wojgrz4918/bs_roformer/model_files/config_bs_roformer_384_8_2_485100.yaml",
        )
        checkpoint = os.environ.get(
            "BS_ROFORMER_CHECKPOINT",
            "/home/wojgrz4918/bs_roformer/model_files/model_bs_roformer_ep_17_sdr_9.6568.ckpt",
        )
        model_repo = os.environ.get(
            "BS_ROFORMER_REPO", "/home/wojgrz4918/bs_roformer/Music-Source-Separation-Training"
        )
        python = os.environ.get("BS_ROFORMER_PYTHON", "python")
        command = " ".join(shlex.quote(v) for v in (
            python, "-m", "agent.worker", "--input", str(input_path), "--output", str(output_dir),
            "--config", config, "--checkpoint", checkpoint, "--repo", model_repo,
        ))
        return self._header("soundcraft_bs", output_dir) + textwrap.dedent(f"""\
            export PYTHONPATH={shlex.quote(str(project))}:{shlex.quote(str(project.parent / 'llm_agent'))}:${{PYTHONPATH:-}}
            cd {shlex.quote(str(project))}
            {command}
            """)

    def _result_dir(self, output_dir: Path) -> Path:
        return output_dir / "audio"


class WcssDemucsAgent(WcssSlurmAgent):
    name = "agent_demucs"
    model = "demucs"
    python_module = "Python/3.11.5-GCCcore-13.2.0"

    def _script_body(self, task: AgentTask, input_path: Path, output_dir: Path) -> str:
        python = os.environ.get("DEMUCS_PYTHON", "/home/wojgrz4918/finger/projekt/venv/bin/python")
        agent_script = os.environ.get("DEMUCS_AGENT_SCRIPT", "/home/wojgrz4918/demucs/agent.py")
        orchestrator_root = os.environ.get("ORCHESTRATOR_ROOT", "/home/wojgrz4918/llm_agent")
        command = " ".join(shlex.quote(v) for v in (
            python, agent_script, "--input", str(input_path), "--output", str(output_dir),
        ))
        return self._header("soundcraft_demucs", output_dir) + textwrap.dedent(f"""\
            mkdir -p {shlex.quote(str(output_dir))}
            export PYTHONPATH={shlex.quote(orchestrator_root)}:${{PYTHONPATH:-}}
            {command}
            """)


class WcssSAMAudioAgent(WcssSlurmAgent):
    name = "agent_sam_audio"
    model = "sam_audio_base"
    supported_categories = frozenset({"B"})
    python_module = "Python/3.11.5-GCCcore-13.2.0"

    def _script_body(self, task: AgentTask, input_path: Path, output_dir: Path) -> str:
        python = os.environ.get("SAM_AUDIO_PYTHON", "/home/wojgrz4918/venvs/sam-audio/bin/python")
        agent_root = Path(os.environ.get("SAM_AUDIO_AGENT_ROOT", "/home/wojgrz4918/agent_sam_audio"))
        model_id = os.environ.get("SAM_AUDIO_MODEL", "facebook/sam-audio-base")
        prompt_file = output_dir.parent / "prompt.txt"
        prompt_file.write_text(task.prompt_text, encoding="utf-8")
        command = " ".join(shlex.quote(v) for v in (
            python, "-m", "worker", "--input", str(input_path), "--prompt-file", str(prompt_file),
            "--output", str(output_dir / "target.wav"), "--model", model_id,
        ))
        return self._header("soundcraft_sam_audio", output_dir) + textwrap.dedent(f"""\
            export PYTHONPATH={shlex.quote(str(agent_root))}:${{PYTHONPATH:-}}
            cd {shlex.quote(str(agent_root))}
            {command}
            """)

    def _missing_outputs(self, result_dir: Path) -> list[str]:
        target = result_dir / "target.wav"
        return [] if target.is_file() and target.stat().st_size > 0 else ["target"]


def build_wcss_agents() -> dict[str, WcssSlurmAgent]:
    """Rejestr produkcyjny przekazywany bezpośrednio do llm_agent."""

    agents: list[WcssSlurmAgent] = [WcssBSRoformerAgent(), WcssDemucsAgent(), WcssSAMAudioAgent()]
    return {agent.name: agent for agent in agents}
