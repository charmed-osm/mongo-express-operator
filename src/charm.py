#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

"""Mongo Express charm module."""

import logging
import secrets

from ops.charm import ActionEvent, CharmBase, ConfigChangedEvent, WorkloadEvent
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus

from cluster import MongoExpressCluster, MongoExpressClusterEvents
from utils import EDITOR_THEMES, PORT

logger = logging.getLogger(__name__)

REQUIRED_CONFIG = ("editor-theme", "web-username", "read-only", "enable-gridfs")


def generate_random_password():
    """Generates a random password."""
    return secrets.token_hex(16)


class ConfigError(Exception):
    """Configuration Error Exception."""

    def __init__(self, key, message) -> None:
        super().__init__()
        self._key = key
        self._message = message

    def __str__(self) -> str:
        """Return exception string."""
        return f"{self._key}: {self._message}"


class MongoExpressCharm(CharmBase):
    """Mongo Express Charm operator."""

    _stored = StoredState()
    on = MongoExpressClusterEvents()

    def __init__(self, *args):
        super().__init__(*args)
        event_observe_mapping = {
            self.on.mongo_express_pebble_ready: self._on_mongo_express_pebble_ready,
            self.on.config_changed: self._on_config_changed,
            self.on.cluster_ready: self._on_cluster_ready,
            self.on.web_password_changed: self._on_config_changed,
            self.on.get_credentials_action: self._on_get_credentials_action,
        }
        for event, observer in event_observe_mapping.items():
            self.framework.observe(event, observer)
        self.cluster = MongoExpressCluster(self)
        self._stored.set_default(mongodb_server="mongodb-k8s-0.mongodb-k8s-endpoints")

    @property
    def container(self):
        """Property to get mongo-express container."""
        return self.unit.get_container("mongo-express")

    @property
    def services(self):
        """Property to get the services in the container plan."""
        return self.container.get_plan().services

    def _on_mongo_express_pebble_ready(self, _: WorkloadEvent):
        self._restart()

    def _on_config_changed(self, event: ConfigChangedEvent):
        if self.container.can_connect():
            self._restart()
        else:
            logger.info("pebble socket not available, deferring config-changed")
            event.defer()
            self.unit.status = MaintenanceStatus("waiting for pebble to start")

    def _on_cluster_ready(self, _):
        if self.unit.is_leader() and not self.cluster.web_password:
            password = generate_random_password()
            self.cluster.set_web_password(password)

    def _on_get_credentials_action(self, event: ActionEvent):
        try:
            logger.debug("Executing action get-credentials...")
            username = self.config["web-username"]
            password = self.cluster.web_password
            if not username:
                raise Exception("username is not defined")
            if not password:
                raise Exception("password is not defined")
            event.set_results({"username": username, "password": password})
            logger.info("Action get-credentials successfully executed")
        except Exception as e:
            logger.error(f"Failed executing action get-credentials. Reason: {e}")
            event.fail(f"Failed getting the credentials: {e}")

    def _restart(self):
        try:
            self._check_configuration()
            layer = self._get_pebble_layer()
            self._set_pebble_layer(layer)
            self._restart_service()
            self.unit.status = ActiveStatus()
        except ConfigError as e:
            logger.info(f"Charm entered to BlockedStatus. Reason: {e}")
            self.unit.status = BlockedStatus(str(e))

    def _check_configuration(self):
        for config_name in REQUIRED_CONFIG:
            if config_name not in self.config:
                raise ConfigError(key=config_name, message="missing configuration.")
        if self.config["editor-theme"] not in EDITOR_THEMES:
            raise ConfigError(key="editor-theme", message="invalid value.")
        logger.info("Charm configuration: checked.")

    def _restart_service(self):
        container = self.container
        if "mongo-express" in self.services:
            container.restart("mongo-express")
            logger.info("mongo-express service has been restarted")

    def _get_pebble_layer(self):
        return {
            "summary": "mongo express layer",
            "description": "pebble config layer for httpbin",
            "services": {
                "mongo-express": {
                    "override": "replace",
                    "summary": "mongo-express service",
                    "command": "tini -s -- /docker-entrypoint.sh",
                    "startup": "enabled",
                    "environment": {
                        "ME_CONFIG_MONGODB_SERVER": self._stored.mongodb_server,
                        "ME_CONFIG_MONGODB_PORT": 27017,
                        # "ME_CONFIG_MONGODB_URL": "",
                        "ME_CONFIG_MONGODB_ENABLE_ADMIN": True,
                        # "ME_CONFIG_MONGODB_ADMINUSERNAME": "",
                        # "ME_CONFIG_MONGODB_ADMINPASSWORD": "",
                        # "ME_CONFIG_MONGODB_AUTH_DATABASE": "",
                        # "ME_CONFIG_MONGODB_AUTH_USERNAME": "",
                        # "ME_CONFIG_MONGODB_AUTH_PASSWORD": "",
                        "ME_CONFIG_SITE_BASEURL": "/",
                        "ME_CONFIG_SITE_COOKIESECRET": "cookiesecret",
                        "ME_CONFIG_SITE_SESSIONSECRET": "sessionsecret",
                        "ME_CONFIG_BASICAUTH_USERNAME": self.config["web-username"],
                        "ME_CONFIG_BASICAUTH_PASSWORD": self.cluster.web_password,
                        # "ME_CONFIG_REQUEST_SIZE": "100kb",
                        "ME_CONFIG_OPTIONS_EDITORTHEME": self.config["editor-theme"],
                        "ME_CONFIG_OPTIONS_READONLY": self.config["read-only"],
                        # "ME_CONFIG_SITE_SSL_ENABLED": False,
                        # "ME_CONFIG_MONGODB_SSLVALIDATE": True,
                        # "ME_CONFIG_SITE_SSL_CRT_PATH": "",
                        # "ME_CONFIG_SITE_SSL_KEY_PATH": "",
                        "ME_CONFIG_SITE_GRIDFS_ENABLED": self.config["enable-gridfs"],
                        # "VCAP_APP_HOST": "",
                        "VCAP_APP_PORT": PORT,
                        # "ME_CONFIG_MONGODB_CA_FILE": "",
                    },
                }
            },
        }

    def _set_pebble_layer(self, layer):
        self.container.add_layer("mongo-express", layer, combine=True)


if __name__ == "__main__":
    main(MongoExpressCharm, use_juju_for_storage=True)
