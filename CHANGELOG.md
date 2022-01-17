# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [5.0.0] - 2022-01-17
### Changed
- Allow specifying Docker API host via `DOCKER_HOST` env var
- Remove the dependency on six
- Bump minimal `docker` version to 5.0.3
### Fixed
- Fix the situation when Hoverfly proxy wasn't ready to be used

## [4.0.2] - 2021-07-06
### Fixed
- Fix specifying a different Hoverfly image
### Changed
- Bumped default Hoverfly image to 1.3.2

## [4.0.2] - 2021-06-11
### Fixed
- Wait until container's ports are available before considering it created
- Fix installation by explicitly including six as a dependency

## [4.0.0] - 2021-03-03
### Changed
- Remove dependency on Wrike's internal library
- Rework fixture creation for simulation; no longer parse all simulation directory on startup

## [3.0.0] - 2021-02-14
### Changed
- `hoverfly` fixture renamed to `hoverfly_instance`
- Added `@hoverfly` decorator to specify a simulation to use. It replaces `simulation_recorder`s
and directly specifying simulations as fixtures. See the updated readme for instructions.

## [2.1.0] - 2021-02-14
### Changed
- `--hoverfly-simulation-path` can now be specified as a path relative to `pytest.ini` file

## [2.0.3] - 2020-12-30
### Fixed
- Fix a bug when container wouldn't start because the host port we wanted to map onto was already in use

## [2.0.2] - 2020-09-14
### Fixed
- This is a technical release to publish to PyPI

## [2.0.1] - 2020-09-14
### Added
- Added ependency on wrike-pytest-containers

### Fixed
- Fix working with docker>=4.3.1 by using wrike-pytest-containers

## [2.0.0] - 2020-05-30
### Changed
- Use `docker` instead of `docker-py`. This is a breaking change, since it requires you
to recreate venv (uninstalling docker-py and installing docker won't work).
- Reuse code from wrike-pytest-containers

## [1.0.6] - 2020-04-22
### Changed
- Updated README.md and docstrings

## [1.0.5] - 2020-03-29
### Changed
- Bumped hoverfly to 1.1.5 to fix openssl issues on debian buster

## [1.0.4] - 2020-03-02
### Added
- Added classifiers to pyproject.toml

## [1.0.3] - 2020-02-24
### Fixed
- Fixed `simulation_recorder`s when path to simulations dir contains environment variables.

## [1.0.2] - 2020-02-24
### Changed
- Add value of `hoverfly_simulation_path` option to error text if directory doesn't exist.

## [1.0.1] - 2020-02-11
### Fixed
- Made test work by fiddling with openssl config in .gitlab-ci.yml

## [1.0.0] - 2020-02-11
### Added
- Initial version.
