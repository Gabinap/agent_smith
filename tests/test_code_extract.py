"""Recovering the Python a model meant to send.

Q7 asks for two things at once when a block is malformed: interpret it
anyway, and explain how it was interpreted. A repair the model is not
told about teaches it nothing, and it repeats the mistake.
"""

from srcs.code_extract import NO_CODE, extract_python, truncate_output

CODE = "def f():\n    return 1"


# --- the canonical block needs no repair ---

def test_a_well_formed_block_comes_back_untouched():
    code, repair = extract_python(f"```python\n{CODE}\n```")

    assert code.strip() == CODE
    assert repair == ""


def test_prose_around_the_block_is_dropped():
    code, _ = extract_python(f"Here you go:\n```python\n{CODE}\n```\nDone.")

    assert code.strip() == CODE


# --- malformed, but recoverable ---

def test_a_block_tagged_py_is_run_and_the_tag_is_named():
    code, repair = extract_python(f"```py\n{CODE}\n```")

    assert code.strip() == CODE
    assert "`py`" in repair and "```python" in repair


def test_a_block_with_no_language_tag_is_run():
    code, repair = extract_python(f"```\n{CODE}\n```")

    assert code.strip() == CODE
    assert repair


def test_a_capitalised_tag_is_run():
    code, repair = extract_python(f"```Python\n{CODE}\n```")

    assert code.strip() == CODE
    assert "`Python`" in repair


def test_an_unclosed_block_is_run_and_says_so():
    code, repair = extract_python(f"```python\n{CODE}")

    assert code.strip() == CODE
    assert "never closed" in repair


def test_bare_code_with_no_fence_at_all_is_run():
    code, repair = extract_python(CODE)

    assert code.strip() == CODE
    assert "no code fence" in repair


# --- nothing to recover ---

def test_prose_alone_yields_nothing():
    code, repair = extract_python("I think the answer is 42, but I am "
                                  "not going to write it down.")

    assert (code, repair) == ("", "")


def test_a_fence_wrapping_something_that_is_not_python_is_refused():
    """A shell block must not be run as if it were Python."""
    code, _ = extract_python("```bash\necho hello && ls -la\n```")

    assert code == ""


def test_an_empty_answer_yields_nothing():
    assert extract_python("") == ("", "")
    assert extract_python(None) == ("", "")


def test_the_message_for_the_model_names_the_expected_shape():
    assert "```python" in NO_CODE


# --- truncation ---

def test_a_short_output_is_left_alone():
    assert truncate_output("one\ntwo\n", max_lines=30) == "one\ntwo\n"


def test_a_long_output_is_cut_and_says_how_much_is_missing():
    result = truncate_output("\n".join(str(i) for i in range(50)), 30)

    assert "Remaining Lines" in result
    assert result.count("\n") <= 31
