import json
import pathlib
from collections import defaultdict

from paths import MATRIX_LOG, RUNS
from termgraph import Args, BarChart, Data


class LLMBenchmarkGraph:
    def __init__(self, runs_dir: pathlib.Path = RUNS):
        """
        Create the graph for the benchmark
        Args:
            runs_dir: Path = directory holding one solution per run
        """
        self.runs_dir = runs_dir
        self.raw_data = self._load_data()

    def _load_data(self) -> list[dict]:
        """
        Get data from every solution file produced by a run.

        The solution files are the only source: the model, the outcome
        and the task are already in each one, so there is no second
        file to keep in sync with them.

        Returns:
            List of llm results
        """
        if not self.runs_dir.is_dir():
            raise FileNotFoundError(f"No run directory {self.runs_dir}")

        results = []
        for path in sorted(self.runs_dir.glob("*.json")):
            if path.name == MATRIX_LOG.name:
                continue
            try:
                run = json.loads(path.read_text(encoding="utf-8"))
                results.append({
                    "model": run["steps"][0]["model_name"],
                    "success": run["success"],
                    "task_id": run["task_id"],
                })
            except json.JSONDecodeError:
                raise ValueError(f"Invalid file {path}")
            except (KeyError, IndexError):
                # A run that never completed a step records no model,
                # so there is nothing to attribute its outcome to.
                print(f"Skipping {path.name}: no step to read a model from")
        return results

    def _validate_and_process_data(self) -> tuple[dict[str, int], int]:
        """
        Validate and process data
        Returns:
            tuple with model_successes and total_tasks done
        """
        model_tasks: defaultdict[str, set[str]] = defaultdict(set)
        model_successes: defaultdict[str, int] = defaultdict(int)

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

    def build_graph(self) -> None:
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
    graph = LLMBenchmarkGraph()
    graph.build_graph()
