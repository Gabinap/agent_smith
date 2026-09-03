"""Load an MBPP task definition from a JSON file."""

from models.tasks import MBPPTaskInput


class Task:
    """Hold the MBPP task loaded from a JSON file."""

    def __init__(self, input_file: str) -> None:
        """Load the task from `input_file`."""
        self.input = self.read_task(input_file)

    def read_task(self, input_file: str) -> MBPPTaskInput:
        """Read and parse `input_file` into an MBPPTaskInput."""
        with (open(input_file, "r") as file):
            json = file.read()
            return MBPPTaskInput.model_validate_json(json)
