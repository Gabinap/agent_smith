"""The artifact locations must not depend on the current directory.

A relative path used to mean two different files depending on whether
the caller was an agent (running from srcs/) or a script (running from
the repo root). That is what silently broke the graph.
"""

from srcs import paths

ARTIFACTS = (
    paths.CACHE,
    paths.RUNS,
    paths.RUN_LOGS,
    paths.MATRIX_LOG,
    paths.LLM_RESPONSES,
)


def test_root_points_at_the_repository():
    assert (paths.ROOT / "pyproject.toml").is_file()
    assert (paths.ROOT / "srcs").is_dir()


def test_every_location_is_absolute():
    for path in ARTIFACTS:
        assert path.is_absolute(), path


def test_every_location_sits_under_the_root():
    for path in ARTIFACTS:
        assert paths.ROOT in path.parents, path


def test_inputs_and_outputs_do_not_share_a_directory():
    """cache/ is what goes in, runs/ is what comes out."""
    assert paths.CACHE != paths.RUNS
    assert paths.RUNS not in paths.CACHE.parents
    assert paths.CACHE not in paths.RUNS.parents
