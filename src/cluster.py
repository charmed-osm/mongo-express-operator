import logging


from ops.charm import CharmEvents, RelationChangedEvent, RelationCreatedEvent
from ops.framework import EventBase, EventSource, Object, StoredState

logger = logging.getLogger(__name__)


class MongoExpressClusterReadyEvent(EventBase):
    pass


class WebPasswordSetEvent(EventBase):
    pass


class MongoExpressClusterEvents(CharmEvents):
    """Custom charm events."""

    cluster_ready = EventSource(MongoExpressClusterReadyEvent)
    web_password_set = EventSource(WebPasswordSetEvent)


class MongoExpressCluster(Object):
    def __init__(self, charm):
        super().__init__(charm, "cluster")

        self.relation = self.framework.model.get_relation("cluster")
        self.charm = charm
        event_observe_mapping = {
            self.charm.on.cluster_relation_created: self._on_cluster_relation_created,
            self.charm.on.cluster_relation_changed: self._on_cluster_relation_changed,
        }
        for event, observer in event_observe_mapping.items():
            self.framework.observe(event, observer)

    def _on_cluster_relation_created(self, event: RelationCreatedEvent):
        self.charm.on.cluster_ready.emit()

    def _on_cluster_relation_changed(self, event: RelationChangedEvent):
        if self.framework.model.app in event.relation.data:
            app_relation_data = event.relation.data[self.framework.model.app]
            if app_relation_data.get("web-password"):
                self.charm.on.web_password_set.emit()

    def set_web_password(self, password: str):
        self.relation.data[self.framework.model.app]["web-password"] = password
        self.charm.on.web_password_set.emit()

    @property
    def web_password(self):
        return self.relation.data[self.framework.model.app].get("web-password")
