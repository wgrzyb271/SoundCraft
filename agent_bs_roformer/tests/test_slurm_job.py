import asyncio
from pathlib import Path

from agent.main import build_agent
from orchestrator.contracts import AgentTask


CONFIG_PATH = Path("/home/wojgrz4918/bs_roformer/model_files/config_bs_roformer_384_8_2_485100.yaml")
CHECKPOINT_PATH = Path("/home/wojgrz4918/bs_roformer/model_files/model_bs_roformer_ep_17_sdr_9.6568.ckpt")
REPO_PATH = Path("/home/wojgrz4918/bs_roformer/Music-Source-Separation-Training")
USER_DIR = Path("/home/wojgrz4918/backend_files/2f1c9f47-fba1-4ad7-a314-10a3751aed8f")
OUTPUT_ROOT = Path("/home/wojgrz4918/agent_bs_roformer/agent_output")
async def main():
    agent = build_agent(
        config_path=CONFIG_PATH,
        checkpoint_path=CHECKPOINT_PATH,
        repo_path=REPO_PATH,
        output_root=OUTPUT_ROOT,
    )

    task = AgentTask(
        agent="agent_bs_roformer",
        model="bs_roformer",
        user_dir=str(USER_DIR),
        prompt_text="Separate the input audio into stems.",
        category="A",
        stems=["drums", "bass", "other", "vocals"],
        attempt_no=1,
        history=[],
    )

    print("=== Running BSRoformerAgent.run() ===")

    result = await agent.run(task)

    print("=== AgentReport ===")
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())