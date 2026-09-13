from models.metrics import SolutionOutput


def save_output(output: SolutionOutput, output_file):
    """Save the Agent output in a Json file.
    Args:
        output (SolutionOutput): solution output
    """
    with (open(output_file, "w", encoding="utf-8") as file):
        file.write(output.model_dump_json(indent=2))
