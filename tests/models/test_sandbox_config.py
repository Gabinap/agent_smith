"""Loading a sandbox policy template must never widen the sandbox.

A template is read at startup from a file on disk. Whatever is wrong
with that file, the fallback has to be the built-in policy, which is
restrictive — never an empty, permissive one.
"""

from srcs.models.sandbox import SandboxConfig

DEFAULTS = SandboxConfig()


def test_reads_a_valid_template(tmp_path):
    path = tmp_path / "policy.json"
    path.write_text(
        '{"authorized_imports": ["math"], "allowed_directories": [],'
        ' "max_execution_time_seconds": 5, "max_memory_mb": 256}')

    config = SandboxConfig.from_file(path)

    assert config.authorized_imports == ["math"]
    assert config.allowed_directories == []
    assert config.max_execution_time_seconds == 5


def test_a_missing_template_falls_back_to_the_defaults(tmp_path):
    config = SandboxConfig.from_file(tmp_path / "absent.json")

    assert config == DEFAULTS


def test_a_malformed_template_falls_back_to_the_defaults(tmp_path):
    path = tmp_path / "half.json"
    path.write_text('{"authorized_imports": [')

    assert SandboxConfig.from_file(path) == DEFAULTS


def test_a_wrongly_typed_template_falls_back_to_the_defaults(tmp_path):
    path = tmp_path / "wrong.json"
    path.write_text('{"max_memory_mb": "beaucoup"}')

    assert SandboxConfig.from_file(path) == DEFAULTS


def test_the_fallback_is_restrictive_not_empty(tmp_path):
    """The point of falling back: os stays blocked, paths stay closed."""
    config = SandboxConfig.from_file(tmp_path / "absent.json")

    assert "os" not in config.authorized_imports
    assert "/" not in config.allowed_directories
    assert config.max_memory_mb > 0
