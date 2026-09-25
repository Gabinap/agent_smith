"""Docker implementation of ExecBackend — no host involved."""

from __future__ import annotations

import atexit
import io
import posixpath
import tarfile
import time

from typing import Any

import docker

from srcs.models import CommandResult


class DockerExecBackend:
    """Run commands and read/write files inside a Docker container."""

    def __init__(self, image_name: str, root: str = "/") -> None:
        """Prepare the Docker backend for a fresh run.

        Resolves `image_name`, purges orphaned containers from a
        previous run, and starts a fresh container to work in.
        """
        client = docker.from_env()  # connect to the Docker daemon
        for c in client.containers.list(
                all=True, filters={"label": "agent-smith"}):
            c.remove(force=True)
        self.root = root
        try:
            client.images.get(image_name)
        except docker.errors.ImageNotFound:
            client.images.pull(image_name)

        self.container = client.containers.run(
            image_name,
            command="sleep infinity",
            detach=True,
            labels={"agent-smith": "true"},
        )
        atexit.register(self._cleanup)
        self._clean = False

    def __enter__(self) -> DockerExecBackend:
        """Return self.

        Allows this backend to be used as a context manager:
        `with DockerExecBackend(...) as backend:`.
        """
        return self

    def __exit__(self, _: Any, __: Any, ___: Any) -> None:
        """Stop and remove the container when the `with` block ends."""
        self._cleanup()

    def _cleanup(self) -> None:
        """Stop and remove the container.

        Safe to call more than once from both `__exit__` and the
        `atexit` fallback.
        """
        if self._clean:
            return
        self._clean = True
        self.container.stop(timeout=1)
        self.container.remove()

    def _resolve(self, path: str) -> str:
        """Resolve `path` (absolute or relative to `root`) and validate it.

        Refuses anything that escapes `root`. Purely textual — this
        is the container's filesystem, not the host's, so pathlib's
        `resolve()` (which touches the host disk) can't be used.
        """
        root = self.root.rstrip("/")
        if not path.startswith("/"):
            path = f"{root}/{path}" if root else f"/{path}"
        normalized = posixpath.normpath(path)
        if root and normalized != root \
                and not normalized.startswith(f"{root}/"):
            raise PermissionError(
                f"path escapes backend root {self.root}: {path}"
            )
        return normalized

    def run(self, cmd: str, workdir: str, timeout: int,
            bash: bool = False) -> CommandResult:
        """Run a shell command inside the container and return its result."""
        resolved_workdir = self._resolve(workdir)
        self.container.exec_run(["mkdir", "-p", resolved_workdir])
        start = time.monotonic()
        if bash:
            exec_cmd = ["bash", "-c", cmd]
        else:
            exec_cmd = ["sh", "-c", cmd]
        try:
            result = self.container.exec_run(
                exec_cmd,
                workdir=resolved_workdir, demux=True, timeout=timeout
            )
            timed_out = False
        except Exception:
            result = type('obj', (object,), {
                'exit_code': -1,
                'output': (b'', b'Command timed out'),
            })()
            timed_out = True

        elapsed = time.monotonic() - start
        stdout, stderr = result.output
        return CommandResult(
            stdout=stdout.decode() if stdout else "",
            stderr=stderr.decode() if stderr else "",
            exit_code=result.exit_code,
            timed_out=timed_out or elapsed >= timeout,
        )

    def read_file(self, path: str) -> str:
        """Return the raw text content of a file inside the container."""
        resolved = self._resolve(path)
        result = self.container.exec_run(["cat", resolved], demux=True)
        stdout, stderr = result.output
        if result.exit_code != 0:
            raise OSError(f"cat {resolved} failed: {stderr.decode()}")
        content: str = stdout.decode()
        return content

    def write_file(self, path: str, content: str) -> None:
        """Overwrite a file inside the container with `content`.

        Packs it into a tar stream, which is what put_archive expects.
        """
        resolved = self._resolve(path)
        dest_dir = posixpath.dirname(resolved) or "/"
        self.container.exec_run(["mkdir", "-p", dest_dir])
        data = content.encode()
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            info = tarfile.TarInfo(name=posixpath.basename(resolved))
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        created = self.container.put_archive(dest_dir, buf.getvalue())
        if not created:
            raise OSError(f"Failed to write {resolved} in container")
