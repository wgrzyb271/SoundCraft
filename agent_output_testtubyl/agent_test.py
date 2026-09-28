# -*- coding: utf-8 -*-

from typing import Any
from pathlib import Path

import soundfile as sf
import torch

from demucs.apply import apply_model
from demucs.pretrained import get_model

from orchestrator.contracts import AgentReport, AgentTask


# ============================================================
# CONFIG
# ============================================================

STEMS = [
    "drums",
    "bass",
    "other",
    "vocals",
]

MODEL_NAME = "htdemucs"


# ============================================================
# AUDIO
# ============================================================

def load_audio(
    path: str | Path,
    sample_rate: int,
) -> torch.Tensor:
    """
    Load audio as [channels, samples].
    """

    audio, sr = sf.read(
        str(path),
        dtype="float32",
        always_2d=True,
    )

    if sr != sample_rate:
        raise ValueError(
            f"Expected sample rate {sample_rate}, "
            f"got {sr} for {path}"
        )

    # soundfile:
    # [samples, channels]
    #
    # Demucs:
    # [channels, samples]

    audio = audio.T

    if audio.shape[0] == 1:
        audio = torch.cat(
            [audio, audio],
            dim=0,
        )

    if audio.shape[0] > 2:
        audio = audio[:2]

    if audio.shape[0] != 2:
        raise ValueError(
            f"Expected stereo audio, "
            f"got {audio.shape[0]} channels"
        )

    return torch.from_numpy(audio).float()


# ============================================================
# SAVE STEMS
# ============================================================

def save_stems(
    separated: torch.Tensor,
    output_dir: str | Path,
    sample_rate: int,
    model_sources: list[str],
) -> None:
    """
    Save Demucs stems as WAV files.
    """

    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for stem_name in STEMS:

        if stem_name not in model_sources:
            raise ValueError(
                f"Stem '{stem_name}' not found "
                f"in model sources: {model_sources}"
            )

        stem_index = model_sources.index(
            stem_name
        )

        output_path = (
            output_dir / f"{stem_name}.wav"
        )

        audio = (
            separated[stem_index]
            .cpu()
            .numpy()
            .T
        )

        sf.write(
            str(output_path),
            audio,
            sample_rate,
        )

        print(
            f"Saved: {output_path}",
            flush=True,
        )


# ============================================================
# VALIDATION
# ============================================================

def validate_output(
    output_dir: str | Path,
) -> None:
    """
    Check that all expected stems were created.
    """

    output_dir = Path(output_dir)

    for stem_name in STEMS:

        output_path = (
            output_dir / f"{stem_name}.wav"
        )

        if not output_path.exists():
            raise FileNotFoundError(
                f"Missing output stem: "
                f"{output_path}"
            )


# ============================================================
# DEMUCS INFERENCE
# ============================================================

@torch.inference_mode()
def separate_audio(
    audio: torch.Tensor,
    model,
    device: torch.device,
) -> tuple[torch.Tensor, float]:
    """
    Run Demucs htdemucs.

    Input:
        [channels, samples]

    Output:
        [sources, channels, samples]

    Returns:
        separated audio,
        inference time
    """

    model.eval()

    audio = audio.float()

    if audio.ndim != 2:
        raise ValueError(
            f"Expected audio [channels, samples], "
            f"got {audio.shape}"
        )

    channels, _ = audio.shape

    if channels != 2:
        raise ValueError(
            f"Demucs expects 2 channels "
            f"channels, got {channels}"
        )

    # Add batch dimension.
    #
    # [channels, samples]
    # ->
    # [1, channels, samples]

    mixture = (
        audio
        .unsqueeze(0)
        .to(device)
    )

    if torch.cuda.is_available():
        torch.cuda.synchronize()

    import time

    start_time = time.perf_counter()

    estimates = apply_model(
        model,
        mixture,
        device=device,
        shifts=1,
        split=True,
        overlap=0.25,
        progress=False,
    )

    if torch.cuda.is_available():
        torch.cuda.synchronize()

    inference_time = (
        time.perf_counter()
        - start_time
    )

    # Remove batch dimension.

    estimates = (
        estimates[0]
        .detach()
        .cpu()
    )

    return estimates, inference_time


# ============================================================
# DEMUCS AGENT
# ============================================================

class DemucsAgent:

    name = "agent_demucs"

    def __init__(
        self,
        model,
        device: torch.device,
        sample_rate: int,
        output_root: str | Path = "agent_output",
    ):

        self.model = model
        self.device = device
        self.sample_rate = sample_rate
        self.output_root = Path(output_root)

    # --------------------------------------------------------
    # INPUT
    # --------------------------------------------------------

    def get_input_path(
        self,
        task: AgentTask,
    ) -> Path:

        return (
            Path(task.user_dir)
            / "input"
            / "audio_folder"
            / "audio.wav"
        )

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    def get_output_dir(
        self,
        task: AgentTask,
    ) -> Path:

        request_id = Path(
            task.user_dir
        ).name

        return (
            self.output_root
            / request_id
        )

    # --------------------------------------------------------
    # RUN
    # --------------------------------------------------------

    async def run(
        self,
        task: AgentTask,
    ) -> AgentReport | dict[str, Any]:

        attempted_params = {
            "model": MODEL_NAME,
            "sample_rate": self.sample_rate,
            "shifts": 1,
            "split": True,
            "overlap": 0.25,
        }

        try:

            # ----------------------------------------------
            # Paths
            # ----------------------------------------------

            input_path = (
                self.get_input_path(task)
            )

            output_dir = (
                self.get_output_dir(task)
            )

            print(
                f"Input: {input_path}",
                flush=True,
            )

            print(
                f"Output: {output_dir}",
                flush=True,
            )

            # ----------------------------------------------
            # Check input
            # ----------------------------------------------

            if not input_path.exists():
                raise FileNotFoundError(
                    f"Input audio not found: "
                    f"{input_path}"
                )

            # ----------------------------------------------
            # Load audio
            # ----------------------------------------------

            audio = load_audio(
                input_path,
                sample_rate=self.sample_rate,
            )

            # ----------------------------------------------
            # Demucs
            # ----------------------------------------------

            separated, inference_time = (
                separate_audio(
                    audio=audio,
                    model=self.model,
                    device=self.device,
                )
            )

            print(
                f"Inference time: "
                f"{inference_time:.3f} sec",
                flush=True,
            )

            # ----------------------------------------------
            # Save stems
            # ----------------------------------------------

            save_stems(
                separated=separated,
                output_dir=output_dir,
                sample_rate=self.sample_rate,
                model_sources=self.model.sources,
            )

            # ----------------------------------------------
            # Validate
            # ----------------------------------------------

            validate_output(
                output_dir
            )

            # ----------------------------------------------
            # SUCCESS
            # ----------------------------------------------

            return AgentReport(
                agent=self.name,
                status="SUCCESS",
                job_id=None,
                output_path=str(
                    output_dir
                ),
                failure_type=None,
                details=(
                    "Demucs htdemucs separation "
                    "completed successfully. "
                    f"Inference time: "
                    f"{inference_time:.3f} sec."
                ),
                attempted_params=attempted_params,
            )

        except torch.cuda.OutOfMemoryError:

            return AgentReport(
                agent=self.name,
                status="FAILED",
                job_id=None,
                output_path=None,
                failure_type="OOM",
                details=(
                    "CUDA out of memory."
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


# ============================================================
# MODEL / AGENT CREATION
# ============================================================

def build_agent(
    output_root: str | Path = "agent_output",
) -> DemucsAgent:

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    print(
        "PyTorch:",
        torch.__version__,
        flush=True,
    )

    print(
        "CUDA available:",
        torch.cuda.is_available(),
        flush=True,
    )

    print(
        "Device:",
        device,
        flush=True,
    )

    if torch.cuda.is_available():

        print(
            "GPU:",
            torch.cuda.get_device_name(0),
            flush=True,
        )

    # ----------------------------------------------
    # Load the same model as benchmark
    # ----------------------------------------------

    print(
        f"Loading Demucs model: {MODEL_NAME}",
        flush=True,
    )

    model = get_model(
        MODEL_NAME
    )

    model = model.to(device)

    model.eval()

    sample_rate = model.samplerate

    print(
        "Model:",
        MODEL_NAME,
        flush=True,
    )

    print(
        "Sample rate:",
        sample_rate,
        flush=True,
    )

    print(
        "Sources:",
        model.sources,
        flush=True,
    )

    return DemucsAgent(
        model=model,
        device=device,
        sample_rate=sample_rate,
        output_root=output_root,
    )
async def main():
    request_id = "2f1c9f47-fba1-4ad7-a314-10a3751aed8f"

    user_dir = Path(
        "/home/wojgrz4918/backend_files"
    ) / request_id

    agent = build_agent(
        output_root="agent_output"
    )

    task = AgentTask(
        agent="agent_demucs",
        model="htdemucs",
        user_dir=str(user_dir),
        prompt_text="Separate the input audio into stems.",
        category="A",
        stems=["drums", "bass", "other", "vocals"],
        attempt_no=1,
        history=[],
    )

    print("=== Running Demucs Agent ===")
    print(f"Input: {user_dir / 'input/audio_folder/audio.wav'}")

    report = await agent.run(task)

    print("=== AgentReport ===")
    print(report.model_dump_json(indent=2))

    if report.status != "SUCCESS":
        raise RuntimeError(
            f"Agent failed: {report.failure_type}: {report.details}"
        )

    print("=== SUCCESS ===")
    print(f"Output: {report.output_path}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
