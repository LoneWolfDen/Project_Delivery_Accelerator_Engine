from pathlib import Path

from strands import Agent
from strands.models.bedrock import BedrockModel
from strands_tools import image_reader

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "sample_data"
IMAGE_PATH = str(DATA_DIR / "anycompany_onprem_architecture.png")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("\n--- Architecture Review  ---\n")

    # Agent 1 — Architecture Analyst (reads and describes the image)
    analyst = Agent(
        system_prompt=(
            "You are an infrastructure architect. Analyse the provided architecture "
            "diagram and describe all components, their relationships, data flows, "
            "and any legacy or outdated technologies you observe. Be thorough."
        ),
        model=BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0", temperature=0.2, streaming=True),
        tools=[image_reader],
        callback_handler=None,
    )

    analysis_message = f"Read and analyse this on-premises architecture diagram: {IMAGE_PATH}"
    analysis_result = analyst(analysis_message)

    print("--- Analysis Complete ---\n")
    print(analysis_result)
    

    print("\n\n--- Done ---")


if __name__ == "__main__":
    main()
