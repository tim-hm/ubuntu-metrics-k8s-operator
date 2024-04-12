#!/usr/bin/env python3
# Copyright 2024 Tim Holmes-Mitra <tim.holmes-mitra@canonical.com>
# See LICENSE file for licensing details.

import logging
from typing import TYPE_CHECKING

import ops
from utils import get_or_fail, stringify
from workload import WorkloadAgentBuilder, WorkloadAgentBuilderState

if TYPE_CHECKING:  # development import paths for type checking
    from lib.charms.data_platform_libs.v0.data_interfaces import DatabaseRequires
    from lib.charms.grafana_k8s.v0.grafana_dashboard import GrafanaDashboardProvider
    from lib.charms.loki_k8s.v0.loki_push_api import LogProxyConsumer
    from lib.charms.prometheus_k8s.v0.prometheus_scrape import MetricsEndpointProvider
    from lib.charms.traefik_route_k8s.v0.traefik_route import TraefikRouteRequirer

else:  # runtime import paths
    from charms.data_platform_libs.v0.data_interfaces import DatabaseRequires  # noqa: F401, I001
    from charms.grafana_k8s.v0.grafana_dashboard import GrafanaDashboardProvider  # noqa: F401, I001
    from charms.loki_k8s.v0.loki_push_api import LogProxyConsumer  # noqa: F401, I001
    from charms.prometheus_k8s.v0.prometheus_scrape import MetricsEndpointProvider  # noqa: F401, I001
    from charms.traefik_route_k8s.v0.traefik_route import TraefikRouteRequirer  # noqa: F401, I001

logger = logging.getLogger(__name__)


class UbuntuMetrics(ops.CharmBase):
    def __init__(self, *args) -> None:
        super().__init__(*args)

        builder = WorkloadAgentBuilder()
        builder.load_config_values(self.config)

        self._builder = builder
        self._container: ops.Container = self.unit.get_container("workload")

        # Inspired from https://github.com/canonical/grafana-k8s-operator/blob/main/src/charm.py#L177
        self._ingress = TraefikRouteRequirer(
            self,
            self.model.get_relation(builder.ingress_relation_name),  # type: ignore
            builder.ingress_relation_name,
        )

        self._db = DatabaseRequires(
            self,
            relation_name=get_or_fail(builder.db_relation_name),
            database_name=get_or_fail(builder.db_name),
        )

        self._configure_observability()
        self._register_events()

    def _configure_observability(self) -> None:
        """Observability is non-blocking."""
        builder = self._builder
        port = builder.port

        self._prometheus_scraping = MetricsEndpointProvider(
            self,
            relation_name=builder.metrics_relation_name,
            jobs=[{"static_configs": [{"targets": [f"*:{port}"]}]}],
            refresh_event=self.on.config_changed,
        )

        self._logging = LogProxyConsumer(
            self,
            relation_name=builder.log_relation_name,
            log_files=[builder.log_file],
        )

        self._grafana_dashboards = GrafanaDashboardProvider(
            self, relation_name=builder.grafana_relation_name
        )

    def _register_events(self) -> None:
        observe = self.framework.observe

        observe(self.on.config_changed, self._on_config_changed)

        observe(self.on.workload_pebble_ready, self._try_start)

        observe(self._db.on.database_created, self._try_start)
        observe(self._db.on.endpoints_changed, self._try_start)
        observe(self.on.database_relation_broken, self._on_db_relation_broken)

        observe(self.on.ingress_relation_joined, self._try_start)
        observe(self._ingress.on.ready, self._try_start)
        observe(self.on.leader_elected, self._try_start)
        observe(self.on.config_changed, self._try_start)

    def _on_config_changed(self, event: ops.ConfigChangedEvent):
        env = self.config.get("env")

        if not env:
            self.unit.status = ops.BlockedStatus("Charm's env unset. Must be prod, stg, or local")
            return

        logger.info(f"Environment set to: {env}")
        self._builder.set_env(env)
        self._try_start(event)

    def _try_start(self, event: ops.EventBase) -> None:
        self.unit.status = ops.WaitingStatus("Trying to start workload")

        if not self._container.can_connect():
            self.unit.status = ops.WaitingStatus("Cannot connect to container")
            return

        self._try_fetch_db_relation()
        self._try_configure_ingress(event)

        builder = self._builder
        builder_state = builder.get_state()

        if not builder_state == WorkloadAgentBuilderState.Ready:
            self.unit.status = ops.WaitingStatus(builder_state.name)
            logger.debug(stringify(builder))
            return

        workload_agent = builder.build()

        try:
            ingress_config = workload_agent.create_ingress_config
            self._ingress.submit_to_traefik(ingress_config)

            layer = workload_agent.create_pebble_layer
            self._container.add_layer(workload_agent.name, layer, combine=True)
            self._container.replan()
            self.unit.open_port(protocol="tcp", port=workload_agent.port)

            version = workload_agent.fetch_version()
            self.unit.set_workload_version(version)

            self.unit.status = ops.ActiveStatus("🚀")

        except ops.pebble.ConnectionError as e:
            logger.error(f"Failed to connect to Pebble: {e}")
            self.unit.status = ops.BlockedStatus("Could not connect to container")

        except Exception as e:
            logger.error(f"Pebble replan failed: {e}")
            self.unit.status = ops.BlockedStatus("Failed to configure container")

    def _try_configure_ingress(self, event: ops.EventBase) -> None:
        if not self.unit.is_leader():
            return

        # When self._ingress._relation is first set in __init__ it too early in
        # the charm's life. So, when we capture the relation from the event.
        if (
            isinstance(event, ops.RelationJoinedEvent)
            and event.relation.name == self._builder.ingress_relation_name
        ):
            self._ingress._relation = event.relation

        self._builder.set_ingress_ready(self._ingress.is_ready())

    def _try_fetch_db_relation(self) -> None:
        relations = self._db.fetch_relation_data()

        for data in relations.values():
            if not data:
                continue

            host, port = data["endpoints"].split(":")
            (
                self._builder.set_db_host(host)
                .set_db_port(int(port))
                .set_db_username(data["username"])
                .set_db_password(data["password"])
            )

    def _on_db_relation_broken(self, _: ops.EventBase | None = None) -> None:
        self.unit.status = ops.WaitingStatus("Db relation broken")


if __name__ == "__main__":  # pragma: nocover
    ops.main(UbuntuMetrics)  # type: ignore
