"""
Migration Assessment 

Agent 1: Inventory Analyst — analyses application inventory data
Agent 2: Migration Strategist — uses the analyst to build a migration strategy
"""

import csv
from pathlib import Path

from strands import Agent, tool
from strands.models.bedrock import BedrockModel

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "sample_data"
APP_CSV = DATA_DIR / "cpg_app.csv"

# Model IDs
CLAUDE_SONNET_4_MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"
CLAUDE_OPUS_4_MODEL_ID = "us.anthropic.claude-opus-4-20250514-v1:0"

DEFAULT_MODEL_ID = CLAUDE_SONNET_4_MODEL_ID


# ---------------------------------------------------------------------------
# Helper — load CSV
# ---------------------------------------------------------------------------
def load_csv(filepath: Path) -> list[dict]:
    with open(filepath, "r") as f:
        lines = [line.strip().strip('"') for line in f if line.strip()]
    return [dict(row) for row in csv.DictReader(lines)]


# ---------------------------------------------------------------------------
# Agent 1: Inventory Analyst (wrapped as a tool)
# ---------------------------------------------------------------------------
@tool
def analyse_inventory(question: str) -> str:
    """Analyse the application inventory to answer migration-related questions.

    Args:
        question: A question about the application portfolio.
                  Examples: "Which apps are legacy?", "What databases are in use?"

    Returns:
        Analysis based on the inventory data.
    """
    apps = load_csv(APP_CSV)

    app_summary = "\n".join(
        " | ".join(f"{k}: {v}" for k, v in a.items()) for a in apps
    )

    return f"Inventory ({len(apps)} apps):\n{app_summary}\n\nQuestion: {question}"

def main():
    # Agent 1 — Inventory Analyst
    analyst = Agent(
        system_prompt=(
            "You are an application inventory analyst for a CPG company. "
            "Answer questions based on the data provided. Cite app names. Be concise."
        ),
        model=BedrockModel(model_id=DEFAULT_MODEL_ID, temperature=0.2, streaming=False),
        tools=[analyse_inventory],
        callback_handler = None
    )

    # Agent 2 — Migration Strategist (uses analyst output)
    strategist = Agent(
        system_prompt=(
            "You are a cloud migration strategist. Use the provided analysis "
            "to recommend a migration strategy with wave groupings. Reference actual app names."
        ),
        model=BedrockModel(model_id=DEFAULT_MODEL_ID, temperature=0.4, streaming=True),
        callback_handler = None
    )

    print("\n--- Migration Assessment  ---\n")

    # Step 1: Analyst gathers inventory insights
    analysis_result = analyst(
        "Identify all legacy and high-risk apps, their databases, and criticality levels."
    )

    # Step 2: Strategist uses the analysis to produce a migration plan
    message = f"""
    Based on this application inventory analysis:

    {analysis_result}

    Produce a migration strategy:
    1. Recommend a 7R migration disposition for each application
    2. Group the applications into migration waves with justification
    """

    output = strategist(message)
    print(output)

    print("\n\n--- Done ---")


if __name__ == "__main__":
    main()
