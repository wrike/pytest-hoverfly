from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import requests


CURDIR = Path(__file__).parent
os.environ['__XXX_HOVERFLY_SIMULATION_PATH_XXX__'] = str(CURDIR / 'simulations')


@pytest.mark.parametrize('simulation_path', (
    str(Path(__file__).parent / 'simulations'),
    # test that we handle the env vars expanding correctly
    '${__XXX_HOVERFLY_SIMULATION_PATH_XXX__}',
))
def test_hoverfly_decorator(testdir, simulation_path):
    # create a temporary pytest test file
    testdir.makepyfile(
        """
        import pytest
        import requests
        from pytest_hoverfly import hoverfly


        @hoverfly('foaas_version_simulation')
        def test_simulation_replayer():
            resp = requests.get(
                'https://foaas.com/version',
                headers={'Accept': 'application/json'},
            )

            assert resp.json() == {'message': 'Version 2.1.1', 'subtitle': 'FOAAS'}

            # Hoverfly adds Hoverfly: Was-Here header
            assert 'Hoverfly' in resp.headers
    """
    )

    # run all tests with pytest
    result = testdir.runpytest_subprocess('--hoverfly-simulation-path', simulation_path, '-vv')

    result.assert_outcomes(passed=1)


def test_hoverfly_decorator_name_kwarg(testdir):
    """Simulation name may be passed as a keyword argument. """
    # create a temporary pytest test file
    testdir.makepyfile(
        """
        import pytest
        import requests
        from pytest_hoverfly import hoverfly


        @hoverfly(name='foaas_version_simulation')
        def test_simulation_replayer():
            resp = requests.get(
                'https://foaas.com/version',
                headers={'Accept': 'application/json'},
            )

            assert resp.json() == {'message': 'Version 2.1.1', 'subtitle': 'FOAAS'}

            # Hoverfly adds Hoverfly: Was-Here header
            assert 'Hoverfly' in resp.headers
    """
    )

    # run all tests with pytest
    result = testdir.runpytest_subprocess('--hoverfly-simulation-path', str(CURDIR / 'simulations'), '-vv')

    result.assert_outcomes(passed=1)


def test_hoverfly_decorator_unknown_argument(testdir):
    """Unknown arguments must raise an error. """
    # create a temporary pytest test file
    testdir.makepyfile(
        """
        import pytest
        import requests
        from pytest_hoverfly import hoverfly


        @hoverfly(name='foaas_version_simulation', doge='doge')
        def test_simulation_replayer():
            ...
    """
    )

    # run all tests with pytest
    result = testdir.runpytest_subprocess('--hoverfly-simulation-path', str(CURDIR / 'simulations'), '-vv')

    result.assert_outcomes(errors=1)


def test_hoverfly_decorator_recorder(testdir, tmpdir):
    # create a temporary pytest test file
    testdir.makepyfile(
        """
        import pytest
        import requests
        from pytest_hoverfly import hoverfly

        @hoverfly('foaas_version_simulation', record=True)
        def test_stateful_simulation_recorder():
            resp = requests.get(
                'https://foaas.com/version',
                headers={'Accept': 'application/json'},

            )

            assert resp.json() == {'message': 'Version 2.1.1', 'subtitle': 'FOAAS'}
    """
    )

    # run all tests with pytest
    result = testdir.runpytest_subprocess('--hoverfly-simulation-path', tmpdir, '-vv')

    result.assert_outcomes(passed=1)

    with open(tmpdir / 'foaas_version_simulation.json') as f:
        simulation = json.load(f)

    assert len(simulation['data']['pairs']) == 1
    assert simulation['data']['pairs'][0]['response']['body'] == \
           '{"message":"Version 2.1.1","subtitle":"FOAAS"}'


def test_hoverfly_decorator_stateful_recorder(testdir, tmpdir):
    # create a temporary pytest test file
    testdir.makepyfile(
        """
        import pytest
        import requests
        from pytest_hoverfly import hoverfly

        @hoverfly('foaas_version_simulation', record=True, stateful=True)
        def test_stateful_simulation_recorder():
            requests.get(
                'https://foaas.com/version',
                headers={'Accept': 'application/json'},

            )

            resp = requests.get(
                'https://foaas.com/version',
                headers={'Accept': 'application/json'},
            )

            assert resp.json() == {'message': 'Version 2.1.1', 'subtitle': 'FOAAS'}
    """
    )

    # run all tests with pytest
    result = testdir.runpytest_subprocess('--hoverfly-simulation-path', tmpdir, '-vv')

    result.assert_outcomes(passed=1)

    with open(Path(tmpdir) / 'foaas_version_simulation.json') as f:
        simulation = json.load(f)

    assert len(simulation['data']['pairs']) == 2


def test_(_patch_env):
    """It's only purpose to invoke _patch_env fixture so that the following
    test may check whether there are unintended side effects.
    """


def test_lack_of_unintended_side_effects():
    """If no hoverfly fixtures are used, requests should not use proxy.
    This test must be run after at least one hoverfly-using test has
    been run, so that session-scoped fixtures with potential side-effects
    are initialized.
    """
    resp = requests.get('https://foaas.com/version', headers={'Accept': 'application/json'})

    try:
        assert resp.json() == {'message': 'Version 2.1.1', 'subtitle': 'FOAAS'}, resp.text
    except json.decoder.JSONDecodeError:
        pytest.fail(resp.text + '\n\n(Request went to Hoverfly insted of foaas.com)')

    # Hoverfly adds Hoverfly: Was-Here header
    assert 'Hoverfly' not in resp.headers

    assert 'HTTP_PROXY' not in os.environ
    assert 'HTTPS_PROXY' not in os.environ
    assert 'SSL_CERT_FILE' not in os.environ
    assert 'REQUESTS_CA_BUNDLE' not in os.environ
