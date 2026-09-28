from pathlib import Path
from agent.main import build_agent


REPO_PATH = Path("/home/wojgrz4918/bs_roformer")
CONFIG_PATH = REPO_PATH / "model_files/config_bs_roformer_384_8_2_485100.yaml"
CHECKPOINT_PATH = REPO_PATH / "model_files/model_bs_roformer_ep_17_sdr_9.6568.ckpt"


def test_build_agent():
    agent = build_agent(
        config_path=CONFIG_PATH,
        checkpoint_path=CHECKPOINT_PATH,
        repo_path=REPO_PATH,
    )

    assert agent.name == "agent_bs_roformer"
    assert agent.sample_rate == 44100
    assert agent.chunk_size == 485100
    assert agent.overlap == 0.5
