"""Recover the Python a model meant to send, and say what was repaired.

A model that forgets the closing fence, tags its block ```py, or drops
the tag altogether has still written usable code. Throwing it away
costs an iteration and teaches the model nothing. The subject asks for
the opposite: interpret the malformed block, and explain how it was
interpreted, so the next answer comes back well formed.

Every repair is checked with ast.parse before being accepted, which
tells us the text is Python without running a line of it.
"""

import ast
import re

CANONICAL = re.compile(r"```python\s*(.*?)```", re.DOTALL)
TAGGED = re.compile(r"```([a-zA-Z]*)\s*(.*?)```", re.DOTALL)
UNCLOSED = re.compile(r"```[a-zA-Z]*\s*(.*)", re.DOTALL)

NO_CODE = ("No python code found in your answer. Reply with a single "
           "```python ... ``` block containing one step.")

EMPTY_ANSWER = ("Your final answer was empty, so nothing was submitted. "
                "Do the work first, then call final_answer with the "
                "result.")


def is_python(code: str) -> bool:
    """True when `code` is non-blank and parses as Python."""
    if not code.strip():
        return False
    try:
        ast.parse(code)
    except SyntaxError:
        return False
    return True


def extract_python(text: str | None) -> tuple[str, str]:
    """Return the code found, and a note on what had to be repaired.

    The note is empty when the block was well formed, and is meant to
    be handed back to the model otherwise. An empty code means nothing
    could be recovered: the caller should then send `NO_CODE`.
    """
    if not text:
        return "", ""

    canonical = CANONICAL.search(text)
    if canonical:
        return canonical.group(1), ""

    tagged = TAGGED.search(text)
    if tagged and is_python(tagged.group(2)):
        tag = tagged.group(1) or "nothing"
        return tagged.group(2), (
            f"Note: your code block was tagged `{tag}` instead of "
            "`python`. It was run anyway. Use ```python next time."
        )

    unclosed = UNCLOSED.search(text)
    if unclosed and is_python(unclosed.group(1)):
        return unclosed.group(1), (
            "Note: your code block was never closed. Everything after "
            "the opening fence was run. Close it with ``` next time."
        )

    if is_python(text):
        return text, (
            "Note: your answer had no code fence, so the whole message "
            "was run as Python. Wrap your code in ```python next time."
        )

    return "", ""


def truncate_output(result: str, max_lines: int) -> str:
    """Cut `result` to `max_lines`, saying how much was left out.

    Silence would be worse than the cut: a model that cannot tell a
    short output from a truncated one stops trusting what it reads.
    """
    new_lines = [i for i, c in enumerate(result) if c == "\n"]
    if len(new_lines) > max_lines:
        result = result[:new_lines[max_lines]]
        result += f"\n({len(new_lines) - max_lines} Remaining Lines...)"
    return result


def observation(error: str | None, output: str, repair: str = "") -> str:
    """The turn the environment sends back, and nothing more.

    The model's own code is already in the conversation as its own
    message: repeating it back costs a second copy of every turn, on
    every later call, since the whole history is resent each time. On
    the measured MBPP runs that duplication was 88% of the feedback.

    What the model cannot know is what happened, so that is all this
    carries — the error if there was one, what was printed, and
    explicitly that nothing was printed when that is the case, which
    is otherwise indistinguishable from a silent failure.
    """
    parts = []
    if repair:
        parts.append(repair)
    if error:
        parts.append(f"Error: {error}")
    if output.strip():
        parts.append(f"Output:\n{output.rstrip()}")
    elif not error:
        parts.append("Ran with no error and printed nothing.")
    return "\n".join(parts)


TEST_VERDICT = re.compile(
    r"^(?:Ran \d+ tests?|OK\b|FAILED\b).*", re.MULTILINE)
TEST_FAILURE = re.compile(r"^(?:FAIL|ERROR): .*", re.MULTILINE)


def summarise_tests(output: str, max_failures: int = 10) -> str:
    """Keep the verdict and what failed, drop the build noise.

    A Django suite prints locale generation, git status and teardown
    around a two-line summary: 393 lines measured, of which 2 matter.
    Sending the whole log would swamp the conversation, and sending
    only "Test Failed" leaves the model without the one thing it needs
    — which test failed.
    """
    failures = TEST_FAILURE.findall(output)
    verdicts = TEST_VERDICT.findall(output)

    lines = failures[:max_failures]
    if len(failures) > max_failures:
        lines.append(f"({len(failures) - max_failures} more failures...)")
    lines.extend(verdicts[-2:])
    return "\n".join(lines) if lines else output
