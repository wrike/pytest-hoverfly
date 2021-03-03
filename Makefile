PYTHON_MODULE := pytest_hoverfly
ENVIRONMENT := dev
VENV_NAME := .venv
PYTHON_BIN := python3
POETRY_VERSION := 1.0.3
POETRY_BIN := ${HOME}/.poetry/bin/poetry
MAX_LINE_LENGTH := 120

.PHONY: help test lint pyfmt prepare clean version name install_poetry
help:
	@echo "Help"
	@echo "----"
	@echo
	@echo "  prepare - create venv and install requirements"
	@echo "  tests - run pytest"
	@echo "  lint - run available linters"
	@echo "  pyfmt - run available formatters"
	@echo "  clean - clean directory from created files"
	@echo "  version - print package version"
	@echo "  name - print package name"
	@echo "  install_poetry - install poetry"


install_poetry:
	curl -sSL https://raw.githubusercontent.com/sdispater/poetry/${POETRY_VERSION}/get-poetry.py > get-poetry.py \
	&& cat get-poetry.py | sha256sum -c poetry-${POETRY_VERSION}.checksum \
	&& python get-poetry.py --version ${POETRY_VERSION} -y \
	&& rm get-poetry.py

prepare:
	${PYTHON_BIN} -m venv ${VENV_NAME} \
	&& . ${VENV_NAME}/bin/activate \
	&& (if [ "${ENVIRONMENT}" = "prod" ]; \
		then ${POETRY_BIN} install --no-dev --no-root \
		   && ${POETRY_BIN} build --format=wheel \
		   && python -m pip install dist/*.whl; \
		else ${POETRY_BIN} install; \
		fi)

test:
	python -m pytest tests/ --cov=${PYTHON_MODULE}

lint:
	flake8 --max-line-length=120 ${PYTHON_MODULE} tests
	black -l ${MAX_LINE_LENGTH} --check ${PYTHON_MODULE} tests
	isort -l ${MAX_LINE_LENGTH} --check-only --diff --jobs 4 ${PYTHON_MODULE} tests

pyfmt:
	black -l ${MAX_LINE_LENGTH} --quiet ${PYTHON_MODULE} tests
	isort -l ${MAX_LINE_LENGTH} ${PYTHON_MODULE} tests --jobs 4


clean:
	rm -rf ${VENV_NAME}
	find . -name \*.pyc -delete

version:
	@sed -n 's/.*version = "\(.*\)".*/\1/p' pyproject.toml

name:
	@sed -n 's/.*name = "\(.*\)".*/\1/p' pyproject.toml
