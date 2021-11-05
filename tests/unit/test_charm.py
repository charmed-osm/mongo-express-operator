# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus
from ops.testing import Harness
from pytest_mock import MockerFixture

from charm import MongoExpressCharm


@pytest.fixture
def harness(mocker: MockerFixture):
    mocker.patch("charm.MongoExpressCluster")
    mongo_harness = Harness(MongoExpressCharm)
    mongo_harness.begin()
    yield mongo_harness
    mongo_harness.cleanup()


def test_mongo_express_pebble_ready(mocker: MockerFixture, harness: Harness):
    spy = mocker.spy(harness.charm, "_restart")
    harness.charm.on.mongo_express_pebble_ready.emit("mongo-express")
    assert harness.charm.unit.status == ActiveStatus()
    assert spy.call_count == 1


def test_config_changed_can_connect(mocker: MockerFixture, harness: Harness):
    spy = mocker.spy(harness.charm, "_restart")
    harness.charm.on.config_changed.emit()
    assert harness.charm.unit.status == ActiveStatus()
    assert spy.call_count == 1


def test_config_changed_cannot_connect(mocker: MockerFixture, harness: Harness):
    spy = mocker.spy(harness.charm, "_restart")
    container_mock = mocker.Mock()
    container_mock.can_connect.return_value = False
    mocker.patch(
        "charm.MongoExpressCharm.container",
        return_value=container_mock,
        new_callable=mocker.PropertyMock,
    )
    harness.charm.on.config_changed.emit()
    assert harness.charm.unit.status == MaintenanceStatus("waiting for pebble to start")
    assert spy.call_count == 0


def test_cluster_ready_leader_no_password(mocker: MockerFixture, harness: Harness):
    harness.set_leader(True)
    harness.charm.cluster.web_password = None
    harness.charm.on.cluster_ready.emit()
    assert harness.charm.cluster.set_web_password.call_count == 1


def test_cluster_ready_leader_password_already_set(mocker: MockerFixture, harness: Harness):
    harness.set_leader(True)
    harness.charm.cluster.web_password = "password"
    harness.charm.on.cluster_ready.emit()
    assert harness.charm.cluster.set_web_password.call_count == 0


def test_cluster_ready_non_leader(mocker: MockerFixture, harness: Harness):
    harness.charm.on.cluster_ready.emit()
    assert harness.charm.cluster.set_web_password.call_count == 0


def test_web_password_changed(mocker: MockerFixture, harness: Harness):
    spy = mocker.spy(harness.charm, "_restart")
    harness.charm.on.web_password_changed.emit()
    assert spy.call_count == 1


def test_get_credentials_action_success(mocker: MockerFixture, harness: Harness):
    harness.charm.cluster.web_password = "pass"
    mock_event = mocker.Mock()
    harness.charm._on_get_credentials_action(mock_event)
    mock_event.set_results.assert_called_once_with({"username": "admin", "password": "pass"})


def test_get_credentials_action_failed(mocker: MockerFixture, harness: Harness):
    # Test missing username
    harness.update_config({"web-username": ""})
    mock_event = mocker.Mock()
    harness.charm._on_get_credentials_action(mock_event)
    mock_event.set_results.assert_not_called()
    mock_event.fail.assert_called_with("Failed getting the credentials: username is not defined")
    # Test missing password
    harness.update_config({"web-username": "admin"})
    harness.charm.cluster.web_password = None
    harness.charm._on_get_credentials_action(mock_event)
    mock_event.set_results.assert_not_called()
    mock_event.fail.assert_called_with("Failed getting the credentials: password is not defined")


def test_missing_read_only_configuration(mocker: MockerFixture, harness: Harness):
    harness._backend._config = {}
    harness.update_config(
        {"web-username": "admin", "enable-gridfs": False, "editor-theme": "default"}
    )
    assert harness.charm.unit.status == BlockedStatus("read-only: missing configuration.")


def test_missing_web_username_configuration(mocker: MockerFixture, harness: Harness):
    harness._backend._config = {}
    harness.update_config({"read-only": True, "enable-gridfs": False, "editor-theme": "default"})
    assert harness.charm.unit.status == BlockedStatus("web-username: missing configuration.")


def test_missing_enable_gridfs_configuration(mocker: MockerFixture, harness: Harness):
    harness._backend._config = {}
    harness.update_config({"read-only": True, "web-username": "admin", "editor-theme": "default"})
    assert harness.charm.unit.status == BlockedStatus("enable-gridfs: missing configuration.")


def test_missing_editor_theme_configuration(mocker: MockerFixture, harness: Harness):
    harness._backend._config = {}
    harness.update_config({"read-only": True, "web-username": "admin", "enable-gridfs": False})
    assert harness.charm.unit.status == BlockedStatus("editor-theme: missing configuration.")


def test_editor_theme_wrong_value(mocker: MockerFixture, harness: Harness):
    harness.update_config({"editor-theme": "wrong value"})
    assert harness.charm.unit.status == BlockedStatus("editor-theme: invalid value.")


def test_restart_service_service_not_exists(mocker: MockerFixture, harness: Harness):
    container_mock = mocker.Mock()
    mocker.patch(
        "charm.MongoExpressCharm.container",
        return_value=container_mock,
        new_callable=mocker.PropertyMock,
    )
    mocker.patch(
        "charm.MongoExpressCharm.services", return_value={}, new_callable=mocker.PropertyMock
    )
    harness.charm._restart_service()
    container_mock.restart.assert_not_called()
