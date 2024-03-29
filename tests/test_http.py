import os
from typing import Generator, Iterator
from unittest import mock

import pytest
from flask.testing import FlaskClient
from flask.wrappers import Response

from meshmash.http import app
from meshmash.manager import Config

mock_config = Config(
    psk="test_psk",
    subnet="10.1.2.0/24",
    state_path="test_state.json",
)


@pytest.fixture
def client() -> "Iterator[FlaskClient]":
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

    for statefile in ("test_state.json", "test_state.json.bkup"):
        if os.path.exists(statefile):
            os.remove(statefile)


@mock.patch("meshmash.http.Config.from_env", return_value=mock_config)
def test_workflow(config: Config, client: "FlaskClient") -> None:
    """
    Test the registration workflow
    """
    resp = client.get("/allocation", headers={"Authorization": "Bearer test_psk"})
    assert resp.status_code == 200

    blob = resp.get_json()
    assert isinstance(blob, dict)
    alloc_token = blob["alloc_token"]
    node = {
        "hostname": "test_host",
        "public_key": "test_host_pubkey",
        "public_ip": "1.2.3.4",
    }
    resp = client.post(
        "/register", headers={"Authorization": f"Bearer {alloc_token}"}, data=node
    )
    assert resp.status_code == 200

    blob = resp.get_json()
    assert isinstance(blob, dict)
    assert blob["private_ip"] == "10.1.2.2"

    resp = client.get(
        "/config", headers={"Authorization": f"Bearer {node['public_key']}"}
    )
    assert resp.status_code == 200

    expected_config = (
        b"""
[Peer]
# Host: test_host
PublicKey = test_host_pubkey
AllowedIPs = 1.2.3.4/32
Endpoint = 1.2.3.4:51280
    """.strip()
        + b"\n\n"
    )
    assert resp.data == expected_config


@mock.patch("meshmash.http.Config.from_env", return_value=mock_config)
def test_no_auth(config: Config, client: "FlaskClient") -> None:
    """
    All the URLs should require authentication
    """
    urls = (
        (client.get, "/allocation"),
        (client.post, "/register"),
        (client.get, "/config"),
    )
    for method, url in urls:
        resp = method(url)
        assert resp.status_code == 403
