#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.


import base64
import logging
import urllib.request
from pathlib import Path
from typing import Tuple

import pytest
import yaml
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test: OpsTest):
    """Build the charm-under-test and deploy it together with related charms.

    Assert on the unit status before any relations/configurations take place.
    """
    await ops_test.model.set_config({"update-status-hook-interval": "10s"})
    await ops_test.model.deploy("mongodb-k8s")
    await ops_test.model.wait_for_idle(timeout=1000)
    # build and deploy charm from local source folder
    charm = await ops_test.build_charm(".")
    resources = {
        "mongo-express-image": METADATA["resources"]["mongo-express-image"]["upstream-source"],
    }
    await ops_test.model.deploy(
        charm, resources=resources, application_name="mongo-express", trust=True
    )
    await ops_test.model.wait_for_idle(apps=["mongo-express"], status="active", timeout=1000)
    assert ops_test.model.applications["mongo-express"].units[0].workload_status == "active"

    await ops_test.model.set_config({"update-status-hook-interval": "60m"})


@pytest.mark.abort_on_fail
async def test_mongo_express_is_up(ops_test: OpsTest):
    username, password = await get_credentials_action(ops_test)
    assert username == "admin"
    await authenticate(ops_test, username, password)


@pytest.mark.abort_on_fail
async def test_mongo_express_change_password(ops_test: OpsTest):
    username, password_1 = await get_credentials_action(ops_test)
    new_password = await change_password_action(ops_test)
    username_2, password_2 = await get_credentials_action(ops_test)
    assert username == username_2
    assert password_1 != new_password
    assert new_password == password_2
    await authenticate(ops_test, username, new_password)


async def get_credentials_action(ops_test: OpsTest) -> Tuple[str, str]:
    """Execute get-credentials action and return (username, password)."""
    action = (
        await ops_test.model.applications["mongo-express"].units[0].run_action("get-credentials")
    )
    output = await ops_test.model.wait_for_action(action.entity_id)
    assert output.status == "completed"
    assert "username" in output.results
    assert "password" in output.results
    return output.results["username"], output.results["password"]


async def change_password_action(ops_test: OpsTest) -> str:
    """Execute change-password action and return new-password."""
    action = (
        await ops_test.model.applications["mongo-express"].units[0].run_action("change-password")
    )
    output = await ops_test.model.wait_for_action(action.entity_id)
    assert output.status == "completed"
    assert "new-password" in output.results
    return output.results["new-password"]


async def authenticate(ops_test: OpsTest, username: str, password: str) -> None:
    """Authenticate using username and password."""
    status = await ops_test.model.get_status()
    address = status["applications"]["mongo-express"]["units"]["mongo-express/0"]["address"]
    url = f"http://{address}:8081"
    logger.info("mongo-express public address: http://%s", url)
    token = base64_encode(f"{username}:{password}")
    request = urllib.request.Request(url, headers={"Authorization": f"Basic {token}"})
    response = urllib.request.urlopen(request)
    assert response.code == 200


def base64_encode(phrase: str) -> str:
    return base64.b64encode(phrase.encode("utf-8")).decode("utf-8")
