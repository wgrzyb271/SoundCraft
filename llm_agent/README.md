# SoundCraft orchestrator on WCSS

Production flow:

```text
backend request directory -> llm_agent -> BS-RoFormer or Demucs (Slurm)
-> mixAgent -> PostProcessing/stitch_stems -> PASSED + changed_audio_*.wav
```

On `FAILED`, only `response_*.json` is written. A final audio file is published
atomically only after post-processing succeeds.

## Local demo without GPU

Run all commands from the repository root:

```bash
python3 -m venv .venv-demo
source .venv-demo/bin/activate
python -m pip install -r llm_agent/requirements.txt
python -m llm_agent.orchestrator.demo
```

If the virtual environment was created before this dependency list was updated,
run the `pip install -r` command again before starting the demo.

The demo runs the real LangGraph orchestration, `mixAgent`, Pedalboard and
`PostProcessing/stitch_stems`. GPU separation is simulated with generated WAV
stems. The result is written to `soundcraft_demo_result.wav`.

Use your own WAV and prompt:

```bash
python -m llm_agent.orchestrator.demo \
  --audio /path/to/input.wav \
  --prompt "wyciągnij wokal" \
  --output /tmp/vocals.wav
```

Demonstrate model fallback after a simulated BS-RoFormer OOM:

```bash
python -m llm_agent.orchestrator.demo --fallback
```

The JSON printed on success contains `"execution_code": "PASSED"` and the
result path. This demo deliberately avoids effect prompts such as “make vocals
louder”, because those require `DEEPSEEK_API_KEY`.

## Backend and frontend

Backend prerequisites: Python, FFmpeg/FFprobe, rsync and an SSH key accepted by
WCSS. Point it at the same private YAML used by the worker:

```bash
cd SoundCraft_backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install fastapi uvicorn pydantic-settings python-multipart paramiko PyYAML
export SOUNDCRAFT_CONFIG="$(cd .. && pwd)/llm_agent/config.local.yaml"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

In another terminal:

```bash
cd SoundCraft_frontend
cp .env_template .env.local
npm install
npm run dev
```

Open `http://localhost:5173`, upload audio, enter a prompt and submit it. The
frontend polls `/result/{request_id}/agent_response`. It downloads the result
audio only when the response contains `execution_code=PASSED`.

## Start the WCSS worker

First create the private configuration file containing all model paths and
tokens:

```bash
cp llm_agent/config.yaml llm_agent/config.local.yaml
chmod 600 llm_agent/config.local.yaml
```

Edit these sections in `config.local.yaml`:

- `api_keys`: DeepSeek and Hugging Face tokens;
- `paths.request_root`: shared backend/worker request directory;
- `wcss`: Slurm account, QoS and partition;
- `agents.bs_roformer`: agent, config, checkpoint, model repository and Python;
- `agents.demucs`: Python environment, agent script and orchestrator path;
- `agents.sam_audio`: Python environment, agent path and checkpoint ID;
- `backend`: rsync/SFTP host, shared path, SSH key and request TTL.

Environment variables still have priority over YAML values. The local file is
ignored by Git so secrets are not committed.

From the repository root, in an environment containing dependencies from
`llm_agent/requirements.txt`:

```bash
python -m llm_agent.orchestrator.wcss_worker \
  --config llm_agent/config.local.yaml
```

The backend's `backend.sftp_remote_path` and `paths.request_root` must point to
the same directory. Keep the worker running before sending a request from the
UI.

For a scheduler/cron invocation use `--once`. To process one request directly:

```bash
python -m llm_agent.orchestrator.wcss_request \
  /home/wojgrz4918/backend_files/REQUEST_UUID \
  --config llm_agent/config.local.yaml
```

The worker expects `input/audio_folder/audio.wav` and a JSON file containing
`prompt` in `input/prompt_folder/`.

## WCSS environment

The defaults match paths already present in the agents. Override them when the
checkout or model files live elsewhere:

- `WCSS_SLURM_ACCOUNT`, `WCSS_SLURM_QOS`, `WCSS_SLURM_PARTITION`
- `BS_ROFORMER_AGENT_ROOT`, `BS_ROFORMER_CONFIG`, `BS_ROFORMER_CHECKPOINT`,
  `BS_ROFORMER_REPO`, `BS_ROFORMER_PYTHON`
- `DEMUCS_PYTHON`, `DEMUCS_AGENT_SCRIPT`, `ORCHESTRATOR_ROOT`
- `SAM_AUDIO_PYTHON`, `SAM_AUDIO_AGENT_ROOT`, `SAM_AUDIO_MODEL`
- `DEEPSEEK_API_KEY` (classification of ambiguous prompts and mix decisions)

`models.yaml` registers BS-RoFormer and Demucs for classic stems, plus
`sam-audio-base` for open text-prompted separation. BS-RoFormer is first for
vocals/drums/other, while Demucs is first for bass. SAM Audio is intentionally
not used after a classic-stem failure because its benchmark results are weaker
for that path; it handles sounds outside the four-stem taxonomy.

SAM Audio uses a gated checkpoint. Request access to
`facebook/sam-audio-base`, authenticate WCSS with `HF_TOKEN`, install the
official SAM Audio project in Python 3.11+, and configure `SAM_AUDIO_PYTHON`
and `SAM_AUDIO_AGENT_ROOT`. Exact setup commands are in
`agent_sam_audio/README.md`.

## Result contract

Success:

```json
{"execution_code": "PASSED", "output_path": ".../changed_audio_001.wav"}
```

Failure:

```json
{"execution_code": "FAILED", "output_path": null, "error_code": "..."}
```
