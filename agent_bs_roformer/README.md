# BS-Roformer Agent

Agent for running **BS-Roformer audio source separation** on the WCSS Slurm cluster.

## Installation

Requirements:

* Python 3.10+
* Slurm (`sbatch`, `squeue`, `sacct`)
* Access to a WCSS GPU partition
* BS-Roformer model files
* Dependencies from `requirements-agent.txt`

Install dependencies:

```bash
pip install -r requirements-agent.txt
```

The agent requires paths to the BS-Roformer configuration, checkpoint, and repository.

## Usage

Build the agent using `build_agent()`:

```python
from agent.main  import build_agent

CONFIG_PATH = Path("/home/wojgrz4918/bs_roformer/model_files/config_bs_roformer_384_8_2_485100.yaml")
CHECKPOINT_PATH = Path("/home/wojgrz4918/bs_roformer/model_files/model_bs_roformer_ep_17_sdr_9.6568.ckpt")
REPO_PATH = Path("/home/wojgrz4918/bs_roformer/Music-Source-Separation-Training")

agent = build_agent(
    config_path=CONFIG_PATH,
    checkpoint_path=CHECKPOINT_PATH,
    repo_path=REPO_PATH,
    output_root="agent_output",
)
```

### AgentTask

The orchestrator passes an `AgentTask` to the agent:

```python
from orchestrator.contracts import AgentTask

task = AgentTask(
    agent="agent_bs_roformer",
    model="bs_roformer",
    user_dir="/path/to/request",
    prompt_text="Separate the audio into stems.",
    category="A",
    stems=["vocals", "drums", "bass", "other"],
    attempt_no=1,
    history=[],
)
```

Important fields:

| Field         | Description                            |
| ------------- | -------------------------------------- |
| `agent`       | Agent identifier                       |
| `model`       | Model requested by the orchestrator    |
| `user_dir`    | Request directory containing the input |
| `prompt_text` | Original task prompt                   |
| `category`    | Task category (`A` or `B`)             |
| `stems`       | Requested audio stems                  |
| `attempt_no`  | Current attempt number                 |
| `history`     | Previous attempt results               |

The input audio is expected at:

```text
<user_dir>/input/audio_folder/audio.wav
```

Run the agent:

```python
report = await agent.run(task)
```

The agent submits a Slurm job, waits for completion, validates the output, and returns an `AgentReport`.

## Architecture

```text
AgentTask
    │
    ▼
BSRoformerAgent.run()
    │
    ├── create_slurm_script()
    │
    ▼
SlurmJobTool
    │
    ├── sbatch
    └── wait_for_job()
            │
            ▼
       WCSS GPU node
            │
            ├── create temporary venv
            ├── install dependencies
            └── run BS-Roformer
            │
            ▼
       validate_output()
            │
            ▼
       AgentReport
```

The actual inference runs inside the Slurm job. The agent waits for the job to finish before returning the result.

The temporary virtual environment is created under `$TMPDIR` and removed when the job exits.

## Testing

Run the Slurm integration test:

```bash
python tests/test_slurm_job.py
```

The test verifies that the agent can:

* build the BS-Roformer agent,
* create and submit a Slurm job,
* run inference on a GPU,
* generate the expected output,
* return an `AgentReport`.

Inspect a submitted job:

```bash
sacct -j <JOB_ID> --format=JobID,State,ExitCode,Elapsed,MaxRSS
```

Slurm logs are stored in:

```text
agent_output/<request_id>/slurm-<JOB_ID>.out
agent_output/<request_id>/slurm-<JOB_ID>.err
```
