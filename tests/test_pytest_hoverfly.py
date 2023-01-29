from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import requests


CURDIR = Path(__file__).parent
os.environ["__XXX_HOVERFLY_SIMULATION_PATH_XXX__"] = str(CURDIR / "simulations")


@pytest.mark.parametrize(
    "simulation_path",
    (
        str(Path(__file__).parent / "simulations"),
        # test that we handle the env vars expanding correctly
        "${__XXX_HOVERFLY_SIMULATION_PATH_XXX__}",
    ),
)
def test_hoverfly_decorator(testdir, simulation_path):
    # create a temporary pytest test file
    testdir.makepyfile(
        """
import requests
from pytest_hoverfly import hoverfly


@hoverfly('archive_org_simulation')
def test_simulation_replayer():
    resp = requests.get(
        'https://archive.org/metadata/SPD-SLRSY-1867/created',
        headers={'Accept': 'application/json'},
    )

    assert resp.json() == {"result": 1674991955}

    # Hoverfly adds Hoverfly: Was-Here header
    assert 'Hoverfly' in resp.headers
    """
    )

    # run all tests with pytest
    result = testdir.runpytest_subprocess("--hoverfly-simulation-path", simulation_path, "-vv")

    result.assert_outcomes(passed=1)


def test_hoverfly_decorator_name_kwarg(testdir):
    """Simulation name may be passed as a keyword argument."""
    # create a temporary pytest test file
    testdir.makepyfile(
        """
import requests
from pytest_hoverfly import hoverfly


@hoverfly(name='archive_org_simulation')
def test_simulation_replayer():
    resp = requests.get(
        'https://archive.org/metadata/SPD-SLRSY-1867/created',
        headers={'Accept': 'application/json'},
    )

    assert resp.json() == {"result": 1674991955}

    # Hoverfly adds Hoverfly: Was-Here header
    assert 'Hoverfly' in resp.headers
    """
    )

    # run all tests with pytest
    result = testdir.runpytest_subprocess("--hoverfly-simulation-path", str(CURDIR / "simulations"), "-vv")

    result.assert_outcomes(passed=1)


def test_hoverfly_decorator_unknown_argument(testdir):
    """Unknown arguments must raise an error."""
    # create a temporary pytest test file
    testdir.makepyfile(
        """
from pytest_hoverfly import hoverfly


@hoverfly(name='archive_org_simulation', doge='doge')
def test_simulation_replayer():
    ...
    """
    )

    # run all tests with pytest
    result = testdir.runpytest_subprocess("--hoverfly-simulation-path", str(CURDIR / "simulations"), "-vv")

    result.assert_outcomes(errors=1)


def test_hoverfly_decorator_recorder(testdir, tmpdir):
    """This test hits a network!"""
    # create a temporary pytest test file
    testdir.makepyfile(
        """
import requests
from pytest_hoverfly import hoverfly

@hoverfly('archive_org_simulation', record=True)
def test_stateful_simulation_recorder():
    resp = requests.get(
        'https://archive.org/metadata/SPD-SLRSY-1867/created',
        headers={
            'Accept': 'application/json',
            # If we do not add it, hoverlfy would save encoded body, which is harder to verify.
            'Accept-Encoding': 'identity'
        },
    )

    assert resp.json() == {"result": 1674991955}
    """
    )

    # run all tests with pytest
    result = testdir.runpytest_subprocess("--hoverfly-simulation-path", tmpdir, "-vv")

    result.assert_outcomes(passed=1)

    with open(tmpdir / "archive_org_simulation.json") as f:
        simulation = json.load(f)

    assert len(simulation["data"]["pairs"]) == 1
    assert "1674991955" in simulation["data"]["pairs"][0]["response"]["body"]


def test_hoverfly_decorator_stateful_recorder(testdir, tmpdir):
    """This test hits a network!"""
    # create a temporary pytest test file
    testdir.makepyfile(
        """
import requests
from pytest_hoverfly import hoverfly

@hoverfly('archive_org_simulation', record=True, stateful=True)
def test_stateful_simulation_recorder():
    requests.get(
        'https://archive.org/metadata/SPD-SLRSY-1867/created',
        headers={'Accept': 'application/json'},

    )

    resp = requests.get(
        'https://archive.org/metadata/SPD-SLRSY-1867/created',
        headers={'Accept': 'application/json'},
    )

    assert resp.json() == {"result": 1674991955}
    """
    )

    # run all tests with pytest
    result = testdir.runpytest_subprocess("--hoverfly-simulation-path", tmpdir, "-vv")

    result.assert_outcomes(passed=1)

    with open(Path(tmpdir) / "archive_org_simulation.json") as f:
        simulation = json.load(f)

    assert len(simulation["data"]["pairs"]) == 2


def test_(_patch_env):
    """It's only purpose to invoke _patch_env fixture so that the following
    test may check whether there are unintended side effects.
    """


def test_lack_of_unintended_side_effects():
    """If no hoverfly fixtures are used, requests should not use proxy.
    This test must be run after at least one hoverfly-using test has
    been run, so that session-scoped fixtures with potential side-effects
    are initialized.

    This test hits a network!
    """
    resp = requests.get("https://archive.org/metadata/SPD-SLRSY-1867/created", headers={"Accept": "application/json"})

    try:
        assert resp.json() == {"result": 1674991955}, resp.text
    except json.decoder.JSONDecodeError:
        pytest.fail(resp.text + "\n\n(Request went to Hoverfly insted of archive.org)")

    # Hoverfly adds Hoverfly: Was-Here header
    assert "Hoverfly" not in resp.headers

    assert "HTTP_PROXY" not in os.environ
    assert "HTTPS_PROXY" not in os.environ
    assert "SSL_CERT_FILE" not in os.environ
    assert "REQUESTS_CA_BUNDLE" not in os.environ


def test_timeout_option(testdir):
    """Test timeout option is parsed correctly."""
    testdir.makepyfile(
        """
import requests
from pytest_hoverfly import hoverfly


@hoverfly(name='archive_org_simulation')
def test_timeout_parsing(request):
    resp = requests.get(
        'https://archive.org/metadata/SPD-SLRSY-1867/created',
        headers={'Accept': 'application/json'},
    )

    assert resp.json() == {"result": 1674991955}

    # Hoverfly adds Hoverfly: Was-Here header
    assert 'Hoverfly' in resp.headers

    assert request.config.option.hoverfly_start_timeout == 55.0
    """
    )

    # run all tests with pytest
    result = testdir.runpytest_subprocess(
        "--hoverfly-simulation-path", str(CURDIR / "simulations"), "--hoverfly-start-timeout", "55", "-vv"
    )

    result.assert_outcomes(passed=1)
