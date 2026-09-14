"""A failed run must still produce a SolutionOutput, never a crash.

A benchmark needs its failures: every cell of the matrix has to leave a
solution.json behind, including the ones where the agent gave up.
"""

from types import SimpleNamespace

from srcs.agent_mbpp.agent import Mbpp
from srcs.agent_swebench.agent import SWEBench


def _mbpp(sandbox_data, error=None, stop_reason="solved"):
    agent = Mbpp.__new__(Mbpp)
    agent.task = SimpleNamespace(task_id=602)
    agent.steps = []
    agent.total_requests = 0
    agent.sandbox_data = sandbox_data
    agent.prompt = "prompt"
    agent.error = error
    agent.elapsed_seconds = 12.5
    agent.stop_reason = stop_reason
    return agent


def _swebench(sandbox_data, error=None, stop_reason="solved"):
    agent = SWEBench.__new__(SWEBench)
    agent.task = SimpleNamespace(instance_id="django__django-11099")
    agent.steps = []
    agent.total_requests = 0
    agent.sandbox_data = sandbox_data
    agent.prompt = "prompt"
    agent.error = error
    agent.elapsed_seconds = 900.0
    agent.stop_reason = stop_reason
    return agent


# --- the run never reached final_answer ---

def test_mbpp_reports_failure_when_the_sandbox_never_ran():
    output = _mbpp(sandbox_data=None).get_solution_output()

    assert output.success is False
    assert output.solution == ""


def test_swebench_reports_failure_without_a_final_answer():
    agent = _swebench(SimpleNamespace(final_answer=None))

    output = agent.get_solution_output()

    assert output.success is False
    assert output.solution == ""


def test_swebench_turns_the_loop_exception_into_text():
    agent = _swebench(SimpleNamespace(final_answer=None),
                      error=RuntimeError("boom"))

    output = agent.get_solution_output()

    assert output.error == "boom"  # the field is a str, not an Exception


# --- the run succeeded ---

def test_mbpp_reports_success_with_its_answer():
    agent = _mbpp(SimpleNamespace(final_answer="def f(): return 1"))

    output = agent.get_solution_output()

    assert output.success is True
    assert output.solution == "def f(): return 1"


def test_the_stop_reason_reaches_the_file():
    """The agent's reason must win over the model's default.

    The field defaults to "solved", so forgetting to pass it produces a
    solution.json that claims every run succeeded.
    """
    agent = _mbpp(sandbox_data=None, stop_reason="Time limit reached")

    assert agent.get_solution_output().stop_reason == "Time limit reached"


def test_wall_time_is_the_measured_run_time():
    output = _mbpp(SimpleNamespace(final_answer="x")).get_solution_output()

    # not the sum of API latencies: the whole run, sandbox included
    assert output.total_time_seconds == 12.5
