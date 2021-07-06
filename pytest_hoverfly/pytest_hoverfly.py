from __future__ import annotations

import json
import os
import typing as t
from pathlib import Path

import pytest
import requests
import typing_extensions as te

from .base import (
    IMAGE,
    Hoverfly,
    get_container,
)
from .helpers import (
    del_gcloud_credentials,
    del_header,
    ensure_simulation_dir,
    extract_simulation_name_from_request,
    get_simulations_path,
)


class HoverflyMarker(te.Protocol):
    def __call__(
        self,
        name: str,
        *,
        record: bool = False,
        stateful: bool = False,
    ) -> t.Callable[..., t.Any]:
        ...


hoverfly: HoverflyMarker = pytest.mark.hoverfly


def pytest_addoption(parser):
    parser.addoption(
        "--hoverfly-simulation-path",
        dest="hoverfly_simulation_path",
        help="Path to a directory with simulation files. Environment variables will be expanded.",
        type=Path,
    )

    parser.addoption(
        "--hoverfly-image",
        dest="hoverfly_image",
        default=IMAGE,
    )

    parser.addoption(
        "--hoverfly-cert",
        dest="hoverfly_cert",
        default=Path(__file__).parent / "cert.pem",
        help="Path to hoverfly SSL certificate. Needed for requests and aiohttp to trust hoverfly.",
        type=Path,
    )

    parser.addoption(
        "--hoverfly-args",
        dest="hoverfly_args",
        help="Arguments for hoverfly command. Passed as is.",
    )


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item):
    """Add test result to request to make it available to fixtures. Used to print Hoverfly logs
    (if any) when tests fail.

    Copied from
    http://pytest.org/en/latest/example/simple.html#making-test-result-information-available-in-fixtures
    """
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()

    # set a report attribute for each phase of a call, which can
    # be "setup", "call", "teardown"

    setattr(item, "rep_" + rep.when, rep)


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    config.addinivalue_line("markers", "hoverfly(simulation): run Hoverfly with the specified simulation")


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Add replay or record fixtures to the test, based on @hoverfly decorator. """
    marker = item.get_closest_marker(name="hoverfly")
    if not marker:
        return

    ensure_simulation_dir(item.config)

    stateful = marker.kwargs.pop("stateful", False)
    record = marker.kwargs.pop("record", False)

    if set(marker.kwargs) - {"name"}:
        raise RuntimeError(f"Unknown argments passed to @hoverfly: {marker.kwargs}")

    if record:
        item.fixturenames.append("_stateful_simulation_recorder" if stateful else "_simulation_recorder")
    else:
        item.fixturenames.append("_simulation_replayer")


@pytest.fixture
def _simulation_recorder(hoverfly_instance: Hoverfly, request, _patch_env):
    """Use to start Hoverfly and have it proxy-and-record all network requests.
    At the end of the test a `simulation.json` will appear in ${SIMULATIONS_DIR}.

    Don't use it with more than one test at a time, otherwise `simulation.json`
    will be overwritten.

    See README.md for details on how to use the generated file.
    """
    yield from _recorder(hoverfly_instance, request, stateful=False)


@pytest.fixture
def _stateful_simulation_recorder(hoverfly_instance: Hoverfly, request, _patch_env):
    """Use this for stateful services, where response to the same request is not
    always the same. E.g. when you poll a service waiting for some job to finish.

    See also:
        https://docs.hoverfly.io/en/latest/pages/tutorials/basic/capturingsequences/capturingsequences.html
    """
    yield from _recorder(hoverfly_instance, request, stateful=True)


@pytest.fixture(scope="session")
def hoverfly_instance(request) -> Hoverfly:
    """Returns Hoverfly's instance host and ports.

    Two modes are supported:
    1. Externally managed instance. You provide connection details via
    environment variables, and nothing is done.
    Env vars:
        ${HOVERFLY_HOST}
        ${HOVERFLY_PROXY_PORT}
        ${HOVERFLY_ADMIN_PORT}

    2. Instance managed by plugin. Container will be created and destroyed after.
    """
    yield from get_container(
        create_container_kwargs={"command": request.config.option.hoverfly_args},
        image=request.config.option.hoverfly_image,
    )


@pytest.fixture
def _simulation_replayer(hoverfly_instance: Hoverfly, request, _patch_env):
    """Upload given simulation file to Hoverfly and set it to simulate mode.
    Clean up Hoverfly state at the end. If test failed and Hoverfly's last
    log record is an error, print it. Usually that error is the reason for
    test failure.
    """
    # so that requests to hoverfly admin endpoint are not proxied :)
    session = requests.Session()
    session.trust_env = False

    filename = extract_simulation_name_from_request(request)

    # noinspection PyTypeChecker
    with open(get_simulations_path(request.config) / filename) as f:
        data = f.read()

    res = session.put(f"{hoverfly_instance.admin_endpoint}/simulation", data=data)
    res.raise_for_status()

    res = session.put(f"{hoverfly_instance.admin_endpoint}/hoverfly/mode", json={"mode": "simulate"})
    res.raise_for_status()

    yield

    # see pytest_runtest_makereport
    if request.node.rep_setup.passed and request.node.rep_call.failed:
        resp = session.get(f"{hoverfly_instance.admin_endpoint}/logs")
        resp.raise_for_status()
        logs = resp.json()["logs"]
        last_log = logs[-1]
        if "error" in last_log:
            print("----------------------------")
            print("Hoverfly's log has an error!")
            print(last_log["error"])

    r = session.delete(f"{hoverfly_instance.admin_endpoint}/simulation")
    r.raise_for_status()


@pytest.fixture
def _patch_env(request, hoverfly_instance: Hoverfly):
    os.environ["HTTP_PROXY"] = hoverfly_instance.proxy_url
    os.environ["HTTPS_PROXY"] = hoverfly_instance.proxy_url

    # So that aiohttp and requests trust hoverfly
    # Default cert is from
    # https://hoverfly.readthedocs.io/en/latest/pages/tutorials/basic/https/https.html
    path_to_cert = request.config.option.hoverfly_cert
    if not path_to_cert.exists():
        raise ValueError(f"Cert file not found: {path_to_cert}")

    os.environ["SSL_CERT_FILE"] = str(path_to_cert)
    os.environ["REQUESTS_CA_BUNDLE"] = str(path_to_cert)

    yield

    del os.environ["HTTP_PROXY"]
    del os.environ["HTTPS_PROXY"]
    del os.environ["SSL_CERT_FILE"]
    del os.environ["REQUESTS_CA_BUNDLE"]


def _recorder(hoverfly_instance: Hoverfly, request, stateful: bool):
    filename = extract_simulation_name_from_request(request)

    # so that requests to hoverfly admin endpoint are not proxied :)
    session = requests.Session()
    session.trust_env = False

    resp = session.put(
        f"{hoverfly_instance.admin_endpoint}/hoverfly/mode",
        json={
            "mode": "capture",
            # capture all headers
            "arguments": {"headersWhitelist": ["*"], "stateful": stateful},
        },
    )
    resp.raise_for_status()

    yield

    resp = session.get(f"{hoverfly_instance.admin_endpoint}/simulation")
    data = resp.json()

    # Delete common sensitive or excess data
    for pair in data["data"]["pairs"]:
        del_header(pair, "Authorization")
        del_header(pair, "User-Agent")
        del_header(pair, "X-Goog-Api-Client")
        del_header(pair, "Private-Token")
        del_gcloud_credentials(pair)

    # noinspection PyTypeChecker
    with open(get_simulations_path(request.config) / filename, "w+") as f:
        json.dump(data, f, indent=2)

    r = session.delete(f"{hoverfly_instance.admin_endpoint}/simulation")
    r.raise_for_status()
