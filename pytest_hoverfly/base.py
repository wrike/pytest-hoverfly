from __future__ import annotations

import dataclasses as dc
import os
import time
import typing as t
import urllib.error
import urllib.request
import uuid
from http.client import RemoteDisconnected

from docker import DockerClient
from docker.errors import ImageNotFound
from docker.models.containers import Container


IMAGE = "spectolabs/hoverfly:v1.3.2"
CONTAINER_BASENAME = "test-hoverfly"


@dc.dataclass(frozen=True)
class Hoverfly:
    host: str
    admin_port: int
    proxy_port: int

    @property
    def admin_endpoint(self) -> str:
        return f"http://{self.host}:{self.admin_port}/api/v2"

    @property
    def proxy_url(self) -> str:
        return f"http://{self.host}:{self.proxy_port}"

    @classmethod
    def from_container(cls, container: Container) -> Hoverfly:
        return Hoverfly(
            host="localhost",
            admin_port=int(container.ports["8888/tcp"][0]["HostPort"]),
            proxy_port=int(container.ports["8500/tcp"][0]["HostPort"]),
        )

    @classmethod
    def try_from_env(cls, env: t.Mapping[str, str]) -> t.Optional[Hoverfly]:
        hoverfly_host = env.get("HOVERFLY_HOST")
        proxy_port = env.get("HOVERFLY_PROXY_PORT")
        admin_port = env.get("HOVERFLY_ADMIN_PORT")

        if hoverfly_host and proxy_port and admin_port:
            return Hoverfly(hoverfly_host, int(admin_port), int(proxy_port))

    def is_ready(self) -> bool:
        try:
            urllib.request.urlopen(f"{self.admin_endpoint}/state")
            return True
        except (urllib.error.URLError, RemoteDisconnected):
            return False


def get_container(
    container_name: t.Optional[str] = None,
    ports: t.Optional[t.Dict[str, t.Optional[t.List[t.Dict[str, int]]]]] = None,
    image: str = IMAGE,
    timeout: float = 3.0,
    docker_factory: t.Callable[[], DockerClient] = DockerClient,
    create_container_kwargs: t.Optional[t.Mapping[str, t.Any]] = None,
):
    external_service = Hoverfly.try_from_env(os.environ)
    if external_service:
        yield external_service
        return

    if not ports:
        ports = {"8500/tcp": None, "8888/tcp": None}

    if not container_name:
        container_name = f"{CONTAINER_BASENAME}-{uuid.uuid4().hex}"

    # DockerClient goes to docker API to fetch version during initialization
    # we instantiate it only here to avoid network calls if we don't need the client
    docker = docker_factory()

    try:
        docker.images.get(image)
    except ImageNotFound:
        docker.images.pull(image)

    raw_container = docker.containers.create(
        image=image,
        name=container_name,
        detach=True,
        ports=ports,
        **(create_container_kwargs or {}),
    )

    raw_container.start()
    _wait_until_ports_are_ready(raw_container, ports, timeout)

    container = Hoverfly.from_container(raw_container)

    try:
        _wait_until_ready(container, timeout)
        yield container
    finally:
        # we don't care about gracefull exit
        raw_container.kill(signal=9)
        raw_container.remove(v=True, force=True)


def _wait_until_ready(container: Hoverfly, timeout: float) -> None:
    now = time.monotonic()
    delay = 0.001

    while (time.monotonic() - now) < timeout:
        if container.is_ready():
            break
        else:
            time.sleep(delay)
            delay *= 2
    else:
        raise TimeoutError(f"Container for Hoverfly did not start in {timeout}s")


def _wait_until_ports_are_ready(raw_container: Container, ports: t.Dict[str, t.Any], timeout: float) -> None:
    """Docker takes some time to allocate ports so they may not be immediately available."""
    now = time.monotonic()
    delay = 0.001

    while (time.monotonic() - now) < timeout:
        raw_container.reload()
        # value of a port is either a None or an empty list when it's not ready
        ready = {k: v for k, v in raw_container.ports.items() if v}
        if set(ports).issubset(ready):
            break
        else:
            time.sleep(delay)
            delay *= 2
    else:
        raise TimeoutError(f"Docker failed to expose ports in {timeout}s")
