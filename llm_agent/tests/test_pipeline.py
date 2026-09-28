from __future__ import annotations

import asyncio
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from llm_agent.orchestrator.agents import DummyAgent
from llm_agent.orchestrator.config import Settings
from llm_agent.orchestrator.contracts import AgentReport
from llm_agent.orchestrator.main import run_orchestrator
from llm_agent.orchestrator.mcp_session import NullMcpSession
from llm_agent.orchestrator.postprocessing import SoundCraftPostProcessor
from llm_agent.orchestrator.slurm import JobResult
from llm_agent.orchestrator.wcss_agents import WcssBSRoformerAgent, WcssDemucsAgent, WcssSAMAudioAgent


def fake_process(input_path: str, _prompt: str, output_path: str, _stem: str, **_kwargs):
    shutil.copyfile(input_path, output_path)
    return {"mixed_output_path": output_path, "effects_used": {}}


def fake_stitch(stems: dict[str, str], output_path: str):
    shutil.copyfile(next(iter(stems.values())), output_path)
    return {"status": "SUCCESS", "output_path": output_path}


class StemAgent(DummyAgent):
    async def run(self, task):
        self.calls.append(task)
        output = Path(task.user_dir) / "work" / self.name / "stems"
        output.mkdir(parents=True, exist_ok=True)
        for stem in ("vocals", "drums", "bass", "other"):
            (output / f"{stem}.wav").write_bytes(b"RIFF-test-audio")
        return AgentReport(agent=self.name, status="SUCCESS", output_path=str(output))


class FakeSlurm:
    def __init__(self, result_dir: Path):
        self.result_dir = result_dir
        self.job = None

    async def submit_job(self, job):
        self.job = job
        self.result_dir.mkdir(parents=True, exist_ok=True)
        for stem in ("vocals", "drums", "bass", "other"):
            (self.result_dir / f"{stem}.wav").write_bytes(b"RIFF")
        return "123"

    async def wait_for_job(self, _job_id):
        return JobResult("123", True, "COMPLETED")


class FakeSAMSlurm(FakeSlurm):
    async def submit_job(self, job):
        self.job = job
        self.result_dir.mkdir(parents=True, exist_ok=True)
        (self.result_dir / "target.wav").write_bytes(b"RIFF")
        return "456"

    async def wait_for_job(self, _job_id):
        return JobResult("456", True, "COMPLETED")


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "request-1"
        self.audio = self.root / "input" / "audio_folder" / "audio.wav"
        self.audio.parent.mkdir(parents=True)
        self.audio.write_bytes(b"RIFF-input")
        self.settings = Settings(
            classifier_mode="rules",
            models_yaml_path=Path(__file__).parents[1] / "models.yaml",
            user_root=self.temp.name,
        )
        self.processor = SoundCraftPostProcessor(stem_processor=fake_process, stitcher=fake_stitch)

    def tearDown(self):
        self.temp.cleanup()

    def session(self):
        async def deploy(_username: str, _audio: str, _prompt: str) -> str:
            return str(self.root)

        return NullMcpSession(deploy=deploy)

    def test_prompt_to_model_to_postprocessing_returns_passed_audio(self):
        agents = {
            "agent_bs_roformer": StemAgent("agent_bs_roformer", verbose=False),
            "agent_demucs": StemAgent("agent_demucs", verbose=False),
        }
        summary = asyncio.run(run_orchestrator(
            "request-1", str(self.audio), "wyciągnij wokal", agents=agents,
            settings=self.settings, mcp_factory=self.session, postprocess=self.processor, show=False,
        ))
        self.assertEqual(summary.execution_code, "PASSED")
        self.assertEqual(summary.model, "bs_roformer")
        self.assertTrue(Path(summary.output_path or "").is_file())
        self.assertIn("audio_folder", summary.output_path or "")

    def test_model_failure_escalates_to_demucs(self):
        failed = DummyAgent("agent_bs_roformer", verbose=False)
        failed.script = [failed.failure("OOM")]
        agents = {
            "agent_bs_roformer": failed,
            "agent_demucs": StemAgent("agent_demucs", verbose=False),
        }
        summary = asyncio.run(run_orchestrator(
            "request-1", str(self.audio), "wyciągnij wokal", agents=agents,
            settings=self.settings, mcp_factory=self.session, postprocess=self.processor, show=False,
        ))
        self.assertEqual(summary.execution_code, "PASSED")
        self.assertEqual(summary.model, "demucs")
        self.assertEqual([a.status for a in summary.attempts], ["FAILED", "SUCCESS"])

    def test_postprocessing_failure_returns_no_audio(self):
        async def failed_postprocess(_task, _report):
            return {"status": "FAILED", "failure_type": "RUNTIME_ERROR", "details": "mix failed"}

        agents = {"agent_bs_roformer": StemAgent("agent_bs_roformer", verbose=False)}
        summary = asyncio.run(run_orchestrator(
            "request-1", str(self.audio), "wyciągnij wokal", agents=agents,
            settings=self.settings, mcp_factory=self.session, postprocess=failed_postprocess, show=False,
        ))
        self.assertEqual(summary.execution_code, "FAILED")
        self.assertEqual(summary.error_code, "POST_PROCESSING_ERROR")
        self.assertIsNone(summary.output_path)

    def test_real_mixagent_and_stitch_stems_create_valid_wav(self):
        import numpy as np
        import soundfile as sf

        stems_dir = self.root / "work" / "real" / "stems"
        stems_dir.mkdir(parents=True)
        samples = np.zeros((4410, 2), dtype=np.float32)
        samples[:, 0] = 0.1
        samples[:, 1] = -0.1
        for stem in ("vocals", "drums", "bass", "other"):
            sf.write(stems_dir / f"{stem}.wav", samples, 44100)
        task_agent = StemAgent("agent_bs_roformer", verbose=False)
        task = asyncio.run(self._task_for(task_agent))
        report = AgentReport(agent=task.agent, status="SUCCESS", output_path=str(stems_dir))
        result = asyncio.run(SoundCraftPostProcessor()(task, report))
        self.assertEqual(result.status, "SUCCESS")
        info = sf.info(result.output_path or "")
        self.assertEqual(info.samplerate, 44100)
        self.assertEqual(info.channels, 2)

    def test_wcss_agents_generate_slurm_jobs_and_return_contract(self):
        from llm_agent.orchestrator.contracts import AgentTask

        cases = (
            (WcssBSRoformerAgent, "agent_bs_roformer", "bs_roformer", Path("audio")),
            (WcssDemucsAgent, "agent_demucs", "demucs", Path()),
        )
        for agent_type, name, model, suffix in cases:
            with self.subTest(model=model):
                result_dir = self.root / "work" / model / "stems" / suffix
                slurm = FakeSlurm(result_dir)
                agent = agent_type(job_tool=slurm)
                task = AgentTask(
                    agent=name, model=model, user_dir=str(self.root), prompt_text="wyciągnij wokal",
                    category="A", stems=["vocals"],
                )
                report = asyncio.run(agent.run(task))
                self.assertEqual(report.status, "SUCCESS")
                self.assertEqual(report.job_id, "123")
                self.assertIsNotNone(slurm.job)
                script = Path(slurm.job.script_path).read_text(encoding="utf-8")
                self.assertIn("#SBATCH --partition=lem-gpu-short", script)
                subprocess.run(["bash", "-n", slurm.job.script_path], check=True)

    def test_sam_audio_base_handles_open_tasks(self):
        from llm_agent.orchestrator.contracts import AgentTask

        result_dir = self.root / "work" / "sam_audio_base" / "stems"
        slurm = FakeSAMSlurm(result_dir)
        agent = WcssSAMAudioAgent(job_tool=slurm)
        task = AgentTask(
            agent="agent_sam_audio", model="sam_audio_base", user_dir=str(self.root),
            prompt_text="wyodrębnij dźwięk gitary", category="B", stems=[],
        )
        report = asyncio.run(agent.run(task))
        self.assertEqual(report.status, "SUCCESS")
        self.assertEqual(report.job_id, "456")
        script = Path(slurm.job.script_path).read_text(encoding="utf-8")
        self.assertIn("facebook/sam-audio-base", script)
        subprocess.run(["bash", "-n", slurm.job.script_path], check=True)

    def test_sam_audio_is_not_a_classic_stem_fallback(self):
        from llm_agent.orchestrator.registry import candidates_for, list_available_models

        snapshot = list_available_models(self.settings.models_yaml_path)
        self.assertEqual(candidates_for(snapshot, "B", []), ["sam_audio_base"])
        self.assertNotIn("sam_audio_base", candidates_for(snapshot, "A", ["vocals"]))

    def test_single_config_maps_all_wcss_agent_paths(self):
        config = Path(self.temp.name) / "pipeline.yaml"
        config.write_text(
            """
api_keys:
  deepseek: test-deepseek
  huggingface: test-hf
paths:
  models_yaml: /models.yaml
  request_root: /shared/requests
wcss:
  slurm_account: account-1
  slurm_qos: qos-1
  slurm_partition: gpu-test
agents:
  bs_roformer:
    root: /agents/bs
    python: /venvs/bs/bin/python
    config: /models/bs.yaml
    checkpoint: /models/bs.ckpt
    model_repo: /models/bs-repo
  demucs:
    python: /venvs/demucs/bin/python
    script: /agents/demucs/agent.py
    orchestrator_root: /soundcraft/llm_agent
  sam_audio:
    python: /venvs/sam/bin/python
    root: /agents/sam
    model: facebook/sam-audio-base
""",
            encoding="utf-8",
        )
        config.chmod(0o600)
        settings = Settings.load(config)
        self.assertEqual(settings.request_root, "/shared/requests")
        self.assertEqual(settings.huggingface_token, "test-hf")
        self.assertEqual(settings.extra_env["WCSS_SLURM_PARTITION"], "gpu-test")
        self.assertEqual(settings.extra_env["BS_ROFORMER_CHECKPOINT"], "/models/bs.ckpt")
        self.assertEqual(settings.extra_env["DEMUCS_AGENT_SCRIPT"], "/agents/demucs/agent.py")
        self.assertEqual(settings.extra_env["SAM_AUDIO_MODEL"], "facebook/sam-audio-base")

    async def _task_for(self, agent: StemAgent):
        from llm_agent.orchestrator.contracts import AgentTask

        return AgentTask(
            agent=agent.name, model="bs_roformer", user_dir=str(self.root),
            prompt_text="wyciągnij wokal", category="A", stems=["vocals"],
        )


if __name__ == "__main__":
    unittest.main()
