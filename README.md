[![CI](https://github.com/wrike/pytest-hoverfly/actions/workflows/main.yml/badge.svg)](https://github.com/wrike/pytest-hoverfly/actions/workflows/main.yml)


A helper for working with [Hoverfly](https://hoverfly.readthedocs.io/en/latest/) from `pytest`. Works both locally and in CI.

### Installation
`pip install pytest-hoverfly`

or

`poetry add pytest-hoverfly --dev`


### Usage
There are two use cases: to record a new test and to use recordings.

#### Prerequisites
You need to have [Docker](https://www.docker.com/) installed. `pytest-hoverfly` uses it under the hood to create Hoverfly instances.

Create a directory to store simulation files. Pass `--hoverfly-simulation-path` option
when calling `pytest`. The path may be absolute or relative to your `pytest.ini` file.
E.g. if you have a structure like this:
```
├── myproject
    ├── ...
├── pytest.ini
└── tests
    ├── conftest.py
    ├── simulations
```

Then put this in you pytest.ini:
```
[pytest]
addopts =
    --hoverfly-simulation-path=tests/simulations
```

#### Without Docker Desktop
If you're using something like [lima](https://github.com/lima-vm/lima) instead of Docker Desktop, you need to specify a path to Docker API. For lima:

`export DOCKER_HOST=unix:///Users/<YOUR-USER>/.lima/default/sock/docker.sock`

If you're using [minikube](https://github.com/kubernetes/minikube) instead of Docker Desktop, you need to specify the service host because the exposed ports are not available on localhost. For minikube you get the service IP with `minikube ip` command and then put it in the env var:

`export SERVICE_HOST=192.168.0.xxx`

#### How to record a test
```python
from pytest_hoverfly import hoverfly
import requests


@hoverfly('my-simulation-file', record=True)
def test_google_with_hoverfly():
    assert requests.get('https://google.com').status_code == 200
```

Write a test. Decorate it with `@hoverfly`, specifying a name of a file to save the simulation to.
Run the test. A Hoverfly container will be created, and  `HTTP_PROXY` and `HTTPS_PROXY` env vars
will be set to point to this container. After test finishes, the resulting simulation will
be exported from Hoverfly and saved to a file you specified. After test session ends, Hoverfly
container will be destroyed (unless `--hoverfly-reuse-container` is passed to pytest).

This will work for cases when a server always returns the same response for the same
request. If you need to work with stateful endpoints (e.g. wait for Teamcity build
to finish), use `@hoverfly('my-simulation, record=True, stateful=True)`. See
[Hoverfly docs](https://docs.hoverfly.io/en/latest/pages/tutorials/basic/capturingsequences/capturingsequences.html)
for details.

#### How to use recordings
Remove `record` parameter. That's it. When you run the test, it will create a container
with Hoverfly, upload your simulation into it, and use it instead of a real service.

```python
from pytest_hoverfly import hoverfly
import requests


@hoverfly('my-simulation-file')
def test_google_with_hoverfly():
    assert requests.get('https://google.com').status_code == 200
```

Caveat: if you're using an HTTP library other than `aiohttp` or `requests` you need to
tell it to use Hoverfly as HTTP(S) proxy and to trust Hoverfly's certificate. See
`_patch_env` fixture for details on how it's done for `aiohttp` and `requests`.

#### How to re-record a test
Add `record=True` again, and run the test. The simulation file will be overwritten.


#### Change Hoverfly version
To use a different Hoverfly version, specify `--hoverfly-image`. It must be a valid Docker image tag.

#### Start Hoverfly with custom parameters
Use `--hoverfly-args`. It is passed as is to a Hoverfly container.

### Usage in CI
CI systems like Gitlab CI or Github Actions allow you to run arbitrary services as containers. `pytest-hoverfly` can detect if a Hoverfly instance is already running by looking at certain environment variables. If it detects a running instance, `pytest-hovefly` uses it, and doesn't create a new container.

For Github Actions:

```
services:
  hoverfly:
    image: spectolabs/hoverfly:v1.3.2
    ports:
      - 8500:8500
      - 8888:8888

  env:
    HOVERFLY_HOST: localhost
    HOVERFLY_PROXY_PORT: 8500
    HOVERFLY_ADMIN_PORT: 8888
```

Mind that all three variables must be specified.
