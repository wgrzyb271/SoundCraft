from typing import Any
from .audio import load_audio,save_stems
from .inference import separate_audio
from .validation import validate_output
from .resources import ResourceChecker
from  orchestrator.contracts import AgentReport, AgentTask
from .slurm import Job, SlurmJobTool
from pathlib import Path
import torch
import textwrap

class BSRoformerAgent:
    name = "agent_bs_roformer"
    def __init__(self, model, device, sample_rate:int, chunk_size:int, overlap:float = 0.5, output_root: str|Path="agent_output"):
        self.model = model
        self.device = device
        self.sample_rate=sample_rate
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.resource_checker = ResourceChecker()
        self.output_root = Path(output_root)
        self.job_tool = SlurmJobTool()

    def get_input_path(self, task:AgentTask)->Path:
        return Path(task.user_dir) / "input" / "audio_folder" / "audio.wav"

    def get_output_dir(self, task:AgentTask)->Path:
        request_id = Path(task.user_dir).name
        return self.output_root/request_id

    def create_slurm_script(self,task: AgentTask, input_path: str, output_dir: str) -> str:
        script_dir = Path(output_dir) / ".bs_roformer_jobs"
        script_dir.mkdir(parents=True, exist_ok=True)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        script_path = ( script_dir / f"bs_roformer_attempt_{task.attempt_no}.sh" )

        script = textwrap.dedent(f"""\
        #!/bin/bash -l
        #SBATCH --job-name=bs_roformer_{task.attempt_no}
        #SBATCH --account=hpc-danbor2008-1756464546
        #SBATCH --qos=hpc-danbor2008-1756464546
        #SBATCH --nodes=1
        #SBATCH --ntasks-per-node=1
        #SBATCH --gres=gpu:hopper:1
        #SBATCH --cpus-per-task=2
        #SBATCH --mem=4G
        #SBATCH --partition=lem-gpu-short
        #SBATCH --time=00:30:00
        #SBATCH --output={output_dir}/slurm-%j.out
        #SBATCH --error={output_dir}/slurm-%j.err

        source /etc/profile
        set -euo pipefail

        module load Python/3.10.4-GCCcore-11.3.0
        PROJECT_ROOT="/home/wojgrz4918/agent_bs_roformer"
        ORCHESTRATOR_ROOT="/home/wojgrz4918/llm_agent"
        VENV_BASE="${{TMPDIR:-/tmp}}"
        VENV_DIR="$VENV_BASE/bs_roformer_venv_${{SLURM_JOB_ID}}"
        cd "$PROJECT_ROOT"
        export PYTHONPATH="$PROJECT_ROOT:$ORCHESTRATOR_ROOT:${{PYTHONPATH:-}}"

        cleanup() {{ 
            rm -rf "$VENV_DIR" 
            }} 
        trap cleanup EXIT

        echo "=== BS-Roformer Slurm job ==="
        echo "Job ID: $SLURM_JOB_ID"
        echo "Host: $(hostname)"
        echo "TMPDIR=${{TMPDIR:-<not-set>}}"
        echo "VENV_DIR=$VENV_DIR"

        echo "=== Creating venv ==="
        python -m venv "$VENV_DIR"
        source "$VENV_DIR/bin/activate"

        echo "=== Installing dependencies ==="
        python -m pip install --no-cache-dir \\
            -r "$PROJECT_ROOT/requirements-agent.txt"

        echo "=== Python ==="
        python --version

        echo "=== Installed packages ==="
        python -m pip list --format=freeze

        echo "=== PyTorch ==="
        python - <<'PY'
        import torch

        print("torch:", torch.__version__)
        print("CUDA available:", torch.cuda.is_available())

        if torch.cuda.is_available():
            print("GPU:", torch.cuda.get_device_name(0))
            print("CUDA:", torch.version.cuda)
        PY

        echo "=== Running BS-Roformer ==="

        python -m agent.worker \\
            --input "{input_path}" \\
            --output "{output_dir}" \\
            --config "/home/wojgrz4918/bs_roformer/model_files/config_bs_roformer_384_8_2_485100.yaml" \\
            --checkpoint "/home/wojgrz4918/bs_roformer/model_files/model_bs_roformer_ep_17_sdr_9.6568.ckpt" \\
            --repo "/home/wojgrz4918/bs_roformer/Music-Source-Separation-Training"

        echo "=== Job completed ==="
        """)

        script_path.write_text(script)
        script_path.chmod(0o750)

        return str(script_path)

    async def run(self,task: AgentTask) -> AgentReport | dict[str, Any]:

        attempted_params = {
            "overlap": self.overlap,
            "chunk_size": self.chunk_size,
            "sample_rate": self.sample_rate}

        if not self.resource_checker.check():

            return AgentReport(
                agent=self.name,
                status="FAILED",
                job_id=None,
                output_path=None,
                failure_type="NO_RESOURCES",
                details="No GPU resources available.",
                attempted_params=attempted_params,
            )

        try:

            input_path = self.get_input_path(task)
            output_dir = self.get_output_dir(task)

            script_path = self.create_slurm_script(task=task, input_path=str(input_path), output_dir = str(output_dir))
            job = Job(script_path=script_path, work_dir = str(output_dir))
            job_id = await self.job_tool.submit_job(job)
            result = await self.job_tool.wait_for_job(job_id)

            if not result.success:
                return AgentReport(
                    agent=self.name,
                    status="FAILED",
                    job_id=result.job_id,
                    output_path=None,
                    failure_type=result.failure_type,
                    details=result.details,
                    attempted_params=attempted_params,
                )
            
            validate_output(output_dir)

            return AgentReport(
                agent=self.name,
                status="SUCCESS",
                job_id=result.job_id,
                output_path=str(output_dir),
                details=(
                    "BS-Roformer separation "
                    "completed successfully."
                ),
                attempted_params=attempted_params,
            )

        except Exception as e:

            return AgentReport(
                agent=self.name,
                status="FAILED",
                job_id=None,
                output_path=None,
                failure_type="RUNTIME_ERROR",
                details=str(e),
                attempted_params=attempted_params,
            )