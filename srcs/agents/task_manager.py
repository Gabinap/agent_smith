from srcs.models.task import MBPPTaskInput


class Task():
    """Task Handler
    """
    def __init__(self, input_file: str):
        """Initialiaze the task from the json file.

        Args:
            input_file (str): task json file
        """
        self.input = self.read_task(input_file)

    def read_task(self, input_file: str):
        """Read the Json file

        Args:
            input_file (str): _description_
        """
        with (open(input_file, "r") as file):
            json = file.read()
            self.task = MBPPTaskInput.model_validate_json(json)
