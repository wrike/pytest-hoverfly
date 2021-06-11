from __future__ import annotations

import os
from pathlib import Path


def extract_simulation_name_from_request(request):
    try:
        marker = [m for m in request.node.own_markers if m.name == "hoverfly"][0]
    except IndexError as e:
        raise RuntimeError("Test does not have Hoverfly marker") from e

    if marker.args:
        name = marker.args[0]
    else:
        name = marker.kwargs["name"]

    return name if ".json" in name else f"{name}.json"


def get_simulations_path(config) -> Path:
    path = Path(os.path.expandvars(str(config.option.hoverfly_simulation_path)))
    if path.is_absolute():
        return path

    return config.inipath.parent / path


def del_header(pair, header: str):
    try:
        del pair["request"]["headers"][header]
    except KeyError:
        pass


def del_gcloud_credentials(pair):
    if pair["request"]["destination"][0]["value"] == "oauth2.googleapis.com":
        if pair["request"]["path"][0]["value"] == "/token":
            del pair["request"]["body"]
            del_header(pair, "Content-Length")


def ensure_simulation_dir(config) -> Path:
    path = get_simulations_path(config)
    if not path.exists():
        raise ValueError(f"To use pytest-hoverfly you must specify --hoverfly-simulation-path. Current value: {path}")

    return path
