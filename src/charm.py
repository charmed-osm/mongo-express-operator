#!/usr/bin/env python3
# Copyright 2021 David Garcia
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk


import logging
import secrets

from ops.charm import (
    ActionEvent,
    CharmBase,
    ConfigChangedEvent,
    WorkloadEvent,
)
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus
from ops.pebble import ConnectionError

from cluster import MongoExpressCluster, MongoExpressClusterEvents

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    pass


class MongoExpressCharm(CharmBase):
    """Charm the service."""

    _stored = StoredState()
    on = MongoExpressClusterEvents()

    def __init__(self, *args):
        super().__init__(*args)
        event_observe_mapping = {
            self.on.mongo_express_pebble_ready: self._on_mongo_express_pebble_ready,
            self.on.cluster_ready: self._on_cluster_ready,
            self.on.web_password_set: self._on_config_changed,
            self.on.config_changed: self._on_config_changed,
            self.on.get_credentials_action: self._on_get_credentials_action,
        }
        for event, observer in event_observe_mapping.items():
            self.framework.observe(event, observer)
        self.cluster = MongoExpressCluster(self)
        self._stored.set_default(mongodb_server="mongodb-0.mongodb-endpoints")

    def _on_mongo_express_pebble_ready(self, event: WorkloadEvent):
        self._restart()

    def _on_config_changed(self, event: ConfigChangedEvent):
        try:
            self._restart()
        except ConnectionError:
            logger.info("pebble socket not available, deferring config-changed")
            event.defer()

    def _on_cluster_ready(self, event):
        if not self.cluster.web_password and self.unit.is_leader():
            password = generate_random_password()
            self.cluster.set_web_password(password)

    def _on_get_credentials_action(self, event: ActionEvent):
        try:
            username = self.config["web-username"]
            password = self.cluster.web_password
            if not username:
                raise Exception("username is not defined")
            if not password:
                raise Exception("password is not defined")
            event.set_results({"username": username, "password": password})
        except Exception as e:
            event.fail(f"Failed getting the credentials: {event}")

    def _restart(self):
        try:
            self._check_configuration()
            layer = self._get_pebble_layer()
            self._set_pebble_layer(layer)
            self._restart_service()
            self.unit.status = ActiveStatus()
        except ConfigurationError as e:
            self.unit.status = BlockedStatus(str(e))

    def _check_configuration(self):
        if self.config.get("editor-theme") not in EDITOR_THEMES:
            raise ConfigurationError("invalid value of config `editor-theme`")
        if not self._stored.mongodb_server:
            raise ConfigurationError("need mongodb relation or config")
        if not self.cluster.web_password:
            raise ConfigurationError("cluster web-password has not been set yet")

    def _restart_service(self):
        container = self.unit.get_container("mongo-express")
        if "mongo-express" in container.get_plan().services:
            service = container.get_service("mongo-express")
            if service.is_running():
                container.stop("mongo-express")
            container.start("mongo-express")

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
                        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                        "NODE_VERSION": "12.22.7",
                        "YARN_VERSION": "1.22.15",
                        "MONGO_EXPRESS": "0.54.0",
                        "ME_CONFIG_EDITORTHEME": self.config["editor-theme"],
                        "ME_CONFIG_MONGODB_SERVER": self._stored.mongodb_server,
                        "ME_CONFIG_MONGODB_ENABLE_ADMIN": "true",
                        "ME_CONFIG_BASICAUTH_USERNAME": self.config["web-username"],
                        "ME_CONFIG_BASICAUTH_PASSWORD": self.cluster.web_password,
                        "VCAP_APP_HOST": "0.0.0.0",
                    },
                }
            },
        }

    def _set_pebble_layer(self, layer):
        container = self.unit.get_container("mongo-express")
        container.add_layer("mongo-express", layer, combine=True)


def generate_random_password():
    return secrets.token_hex(16)


EDITOR_THEMES = (
    "default",
    "3024-day",
    "3024-night",
    "abbott",
    "abcdef",
    "ambiance",
    "ayu-dark",
    "ayu-mirage",
    "base16-dark",
    "base16-light",
    "bespin",
    "blackboard",
    "cobalt",
    "colorforth",
    "darcula",
    "dracula",
    "duotone-dark",
    "duotone-light",
    "eclipse",
    "elegant",
    "erlang-dark",
    "gruvbox-dark",
    "hopscotch",
    "icecoder",
    "idea",
    "isotope",
    "juejin",
    "lesser-dark",
    "liquibyte",
    "lucario",
    "material",
    "material-darker",
    "material-palenight",
    "material-ocean",
    "mbo",
    "mdn-like",
    "midnight",
    "monokai",
    "moxer",
    "neat",
    "neo",
    "night",
    "nord",
    "oceanic-next",
    "panda-syntax",
    "paraiso-dark",
    "paraiso-light",
    "pastel-on-dark",
    "railscasts",
    "rubyblue",
    "seti",
    "shadowfox",
    "solarized dark",
    "solarized light",
    "the-matrix",
    "tomorrow-night-bright",
    "tomorrow-night-eighties",
    "ttcn",
    "twilight",
    "vibrant-ink",
    "xq-dark",
    "xq-light",
    "yeti",
    "yonce",
    "zenburn",
)
if __name__ == "__main__":
    main(MongoExpressCharm, use_juju_for_storage=True)
