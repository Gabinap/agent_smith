"""The registry is a fallback, not a dependency.

`images.pull` reaches Docker Hub every time, even for an image already
on the machine. That turned every container start into a network call,
and a hard failure on a restricted network — where the SWE-bench agent
needs Docker most. These run without a daemon, on purpose: the point is
that no call leaves the host.
"""

from unittest.mock import MagicMock

import docker
import pytest

from srcs.backends.docker import DockerExecBackend


@pytest.fixture
def client(monkeypatch):
    """A Docker client that answers without a daemon behind it."""
    fake = MagicMock()
    fake.containers.list.return_value = []
    monkeypatch.setattr(docker, "from_env", lambda: fake)
    return fake


def test_an_image_already_here_is_not_pulled(client):
    DockerExecBackend("alpine:latest")

    client.images.get.assert_called_once_with("alpine:latest")
    client.images.pull.assert_not_called()


def test_a_missing_image_is_pulled(client):
    client.images.get.side_effect = docker.errors.ImageNotFound("absent")

    DockerExecBackend("alpine:latest")

    client.images.pull.assert_called_once_with("alpine:latest")


def test_a_name_that_exists_nowhere_still_raises(client):
    """The old code reported a bad image name through `pull`; that
    has to survive the local-first lookup."""
    client.images.get.side_effect = docker.errors.ImageNotFound("absent")
    client.images.pull.side_effect = docker.errors.ImageNotFound("absent")

    with pytest.raises(docker.errors.ImageNotFound):
        DockerExecBackend("no-such-image:latest")
