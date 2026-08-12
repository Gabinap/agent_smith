from srcs.models.tasks import MBPPTaskInput


class Task():
    def __init__(self, input_file: str):
        """Initialiaze the task from the json file.

        Args:
            input_file (str): task json file
        """
        self.input = self.read_task(input_file)

    def read_task(self, input_file: str) -> MBPPTaskInput:
        """Read the Json file

        Args:
            input_file (str): task json file
        Returns:
            MBPPTaskInput: task input modele
        """
        with (open(input_file, "r") as file):
            json = file.read()
            return MBPPTaskInput.model_validate_json(json)
