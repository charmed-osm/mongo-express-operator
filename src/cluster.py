# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

"""Mongo Express cluster module."""

import logging

from ops.charm import CharmEvents, RelationChangedEvent, RelationCreatedEvent
from ops.framework import EventBase, EventSource, Object

logger = logging.getLogger(__name__)


class MongoExpressClusterReadyEvent(EventBase):
    """Event triggered when the cluster relation is ready."""


class WebPasswordChangeEvent(EventBase):
    """Event triggered when the web-password is set or changed."""


class MongoExpressClusterEvents(CharmEvents):
    """Custom charm events."""

    cluster_ready = EventSource(MongoExpressClusterReadyEvent)
    web_password_changed = EventSource(WebPasswordChangeEvent)


class MongoExpressCluster(Object):
    """Mongo Express Cluster (peer) relation."""

    def __init__(self, charm):
        super().__init__(charm, "cluster")
        self.charm = charm
        event_observe_mapping = {
            self.charm.on.cluster_relation_created: self._on_cluster_relation_created,
            self.charm.on.cluster_relation_changed: self._on_cluster_relation_changed,
        }
        for event, observer in event_observe_mapping.items():
            self.framework.observe(event, observer)

    def _on_cluster_relation_created(self, _: RelationCreatedEvent):
        self.charm.on.cluster_ready.emit()

    def _on_cluster_relation_changed(self, event: RelationChangedEvent):
        if self.framework.model.app in event.relation.data:
            app_relation_data = event.relation.data[self.framework.model.app]
            if app_relation_data.get("web-password"):
                self.charm.on.web_password_changed.emit()

    def set_web_password(self, password: str):
        """Set web password."""
        self.relation.data[self.framework.model.app]["web-password"] = password
        self.charm.on.web_password_changed.emit()

    @property
    def web_password(self):
        """Return web password."""
        return self.relation.data[self.framework.model.app].get("web-password")

    @property
    def relation(self):
        """Return peer relation object."""
        return self.framework.model.get_relation("cluster")
