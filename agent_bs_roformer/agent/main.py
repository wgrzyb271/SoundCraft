import argparse
from pathlib import Path

from .agent import BSRoformerAgent
from .model import load_model


def build_agent(config_path: str | Path,checkpoint_path: str |
 Path,repo_path: str | Path,output_root: str | Path = "agent_output",) -> BSRoformerAgent:

    model, device, config = load_model(config_path=config_path,checkpoint_path=checkpoint_path,repo_path=repo_path,)

    sample_rate = config["audio"]["sample_rate"]
    chunk_size = config["audio"]["chunk_size"]

    return BSRoformerAgent(
        model=model,
        device=device,
        sample_rate=sample_rate,
        chunk_size=chunk_size,
        overlap=0.5,
        output_root=output_root,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="BS-Roformer agent"
    )

    parser.add_argument(
        "--config",
        required=True,
        help="Path to BS-Roformer YAML config",
    )

    parser.add_argument(
        "--checkpoint",
        required=True,
        help="Path to BS-Roformer checkpoint",
    )

    parser.add_argument(
        "--repo",
        required=True,
        help="Path to BS-Roformer repository",
    )

    parser.add_argument(
        "--output-root",
        default="agent_output",
        help="Root directory for agent outputs",
    )

    args = parser.parse_args()

    agent = build_agent(
        config_path=args.config,
        checkpoint_path=args.checkpoint,
        repo_path=args.repo,
        output_root=args.output_root,
    )

    print(f"Agent initialized: {agent.name}")
    print(f"Device: {agent.device}")
    print(f"Sample rate: {agent.sample_rate}")
    print(f"Chunk size: {agent.chunk_size}")
    print(f"Overlap: {agent.overlap}")


if __name__ == "__main__":
    main()
