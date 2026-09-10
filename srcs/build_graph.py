import json
from collections import defaultdict

from termgraph import Args, BarChart, Data


class LLMBenchmarkGraph:
    def __init__(self, input_file: str = "srcs/llm_responses.json"):
        """
        Create the graph for the benchmark
        Args:
            input_file: str = data file where llm results are stored
        """
        self.input_file = input_file
        self.raw_data = self._load_data()

    def _load_data(self) -> list[dict]:
        """
        Get data from the input file
        Returns:
            List of llm results
        """
        try:
            with open(self.input_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found {self.input_file}")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid file {self.input_file}")

    def _validate_and_process_data(self) -> tuple[dict[str, int], int]:
        """
        Validate and process data
        Returns:
            tuple with model_successes and total_tasks done
        """
        model_tasks = defaultdict(set)
        model_successes = defaultdict(int)

        for entry in self.raw_data:
            model = entry["model"]
            task_id = entry["task_id"]
            is_success = entry["success"]

            model_tasks[model].add(task_id)
            if is_success:
                model_successes[model] += 1

        models = list(model_tasks.keys())
        if not models:
            raise ValueError("No data found !")

        reference_tasks = model_tasks[models[0]]
        total_tasks = len(reference_tasks)

        for model in models[1:]:
            current_tasks = model_tasks[model]
            if len(current_tasks) != total_tasks:
                raise ValueError(
                    f"Invalid test : {models[0]} -> {total_tasks} tasks "
                    f"but {model} -> {len(current_tasks)}."
                )

            if current_tasks != reference_tasks:
                missing = reference_tasks ^ current_tasks
                raise ValueError(
                    f"Tasks arn't the same: {models[0]} and {model}. "
                    f"Missing task: {missing}"
                )
        return model_successes, total_tasks

    def build_graph(self):
        """
        Display the graph in the terminal
        """
        success_counts, total_tasks = self._validate_and_process_data()
        labels = list(success_counts.keys())
        data_values = [[count] for count in success_counts.values()]

        data = Data(data_values, labels)
        args = Args(
            title="LLM Benchmark",
            width=10,
            format="{:.0f}",
            suffix=f"/{total_tasks}"
        )

        chart = BarChart(data, args)
        chart.draw()


if __name__ == "__main__":
    graph = LLMBenchmarkGraph("srcs/llm_results.json")
    graph.build_graph()


"""
[
  {"model": "Gemma", "success": true, "task_id": "11116s"},
  {"model": "Gemma", "success": true, "task_id": "11115s"},
  {"model": "Qwen", "success": true, "task_id": "11113s"},
  {"model": "Gemma", "success": false, "task_id": "11114s"},
  {"model": "Gemma", "success": true, "task_id": "11113s"},
  {"model": "Gemma", "success": true, "task_id": "11112s"},
  {"model": "Qwen", "success": false, "task_id": "11116s"},
  {"model": "Qwen", "success": true, "task_id": "11115s"},
  {"model": "Qwen", "success": false, "task_id": "11114s"},
  {"model": "Qwen", "success": false, "task_id": "11112s"}
]

"""
