# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest
from ops.testing import Harness
from pytest_mock import MockerFixture

from charm import MongoExpressCharm


@pytest.fixture
def harness():
    mongo_harness = Harness(MongoExpressCharm)
    mongo_harness.begin()
    yield mongo_harness
    mongo_harness.cleanup()


def test_cluster_relation(mocker: MockerFixture, harness: Harness):
    harness.set_leader(True)
    peer_rel_id = harness.add_relation("cluster", "test-charm")
    harness.add_relation_unit(peer_rel_id, "test-charm/1")
    harness.update_relation_data(peer_rel_id, "test-charm", {})
    harness.charm.cluster.set_web_password("password")
    assert harness.charm.cluster.web_password == "password"
