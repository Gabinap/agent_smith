import json

from models.metrics import SolutionOutput


def save_output(output: SolutionOutput, output_file):
    """Save the Agent output in a Json file.
    Args:
        output (SolutionOutput): solution output
    """
    with (open(output_file, "w", encoding="utf-8") as file):
        file.write(output.model_dump_json(indent=2))


def save_llm_messages(messages):
    response = json.dumps(
        [
            m.model_dump() if hasattr(m, "model_dump") else m
            for m in messages
        ],
        indent=2,
        ensure_ascii=False
    )

    with open("llm_messages.json", "w", encoding="utf-8") as file:
        file.write(response)
