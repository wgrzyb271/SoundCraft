# SAM Audio Base agent

This agent is the WCSS executor for open text-prompted source separation. It
uses the gated `facebook/sam-audio-base` checkpoint and is intentionally not
used for classic vocals/drums/bass/other stems.

On WCSS, create a Python 3.11+ environment and install the official project:

```bash
git clone https://github.com/facebookresearch/sam-audio.git
python3.11 -m venv /home/USER/venvs/sam-audio
source /home/USER/venvs/sam-audio/bin/activate
python -m pip install ./sam-audio
huggingface-cli login
```

The Hugging Face account must first be granted access to
`facebook/sam-audio-base`. Configure the orchestrator with:

```bash
export SAM_AUDIO_PYTHON=/home/USER/venvs/sam-audio/bin/python
export SAM_AUDIO_AGENT_ROOT=/path/to/SoundCraft/agent_sam_audio
export SAM_AUDIO_MODEL=facebook/sam-audio-base
export HF_TOKEN=hf_...
```
