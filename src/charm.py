#!/usr/bin/env python3
# Copyright 2024 Tim Holmes-Mitra <tim.holmes-mitra@canonical.com>
# See LICENSE file for licensing details.

import logging
from typing import TYPE_CHECKING

import ops
from entities import WorkloadBuilder
from utils import get_or_fail, stringify

# in development types via dev paths
if TYPE_CHECKING:
    from lib.charms.data_platform_libs.v0.data_interfaces import DatabaseRequires
else:  # runtime
    from charms.data_platform_libs.v0.data_interfaces import DatabaseRequires  # noqa: F401, I001


logger = logging.getLogger(__name__)


class UbuntuReportd(ops.CharmBase):
    name = "reportd"

    def __init__(self, *args) -> None:
        super().__init__(*args)

        self._builder = (
            WorkloadBuilder()
            .set_name(UbuntuReportd.name)
            .set_port(8080)
            .set_db_relation_name("database")
            .set_db_name(UbuntuReportd.name)
        )

        self._container: ops.Container = self.unit.get_container(UbuntuReportd.name)

        self._db = DatabaseRequires(
            self,
            relation_name=get_or_fail(self._builder.db_relation_name),
            database_name=get_or_fail(self._builder.db_name),
        )

        self._register_events()

    def _register_events(self) -> None:
        self.framework.observe(self.on.reportd_pebble_ready, self._try_start)
        self.framework.observe(self._db.on.database_created, self._try_start)
        self.framework.observe(self._db.on.endpoints_changed, self._try_start)
        self.framework.observe(self.on.database_relation_broken, self._on_db_relation_broken)

    def _try_start(self, _: ops.EventBase) -> None:
        self.unit.status = ops.WaitingStatus("Checking preconditions ...")

        self._try_fetch_db_relation()

        if not self._builder.check_is_ready():
            self.unit.status = ops.WaitingStatus("Preconditions unsatisfied")
            logger.debug(stringify(self._builder))
            return

        workload = self._builder.build()

        try:
            name = workload.name
            port = workload.port

            command = " ".join(["/app/ubuntu-reportd", "-vvv"])
            environment: dict[str, str] = {
                "UBUNTU-REPORTD_SERVERPORT": str(port),
                "DB_HOST": workload.db_host,
                "DB_PORT": str(workload.db_port),
                "DB_USERNAME": workload.db_username,
                "DB_PASSWORD": workload.db_password,
            }

            layer = ops.pebble.Layer(
                {
                    "summary": "reportd base layer definition",
                    "services": {
                        name: {
                            "override": "replace",
                            "summary": f"{name} pebble config layer",
                            "startup": "enabled",
                            "command": command,
                            "environment": environment,
                        }
                    },
                }
            )

            self._container.add_layer(name, layer, combine=True)
            self._container.replan()

            self.unit.open_port(protocol="tcp", port=port)
            self.unit.status = ops.ActiveStatus("🚀")

        except ops.pebble.ConnectionError as e:
            logger.error(f"Failed to connect to Pebble: {e}")
            self.unit.status = ops.BlockedStatus("Could not connect to container")

        except Exception as e:
            logger.error(f"Pebble replan failed: {e}")
            self.unit.status = ops.BlockedStatus("Failed to configure container")

    def _try_fetch_db_relation(self) -> None:
        self.unit.status = ops.WaitingStatus("Fetch db relation")
        relations = self._db.fetch_relation_data()
        logger.error(f"Got database relation data: {relations}")

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
    ops.main(UbuntuReportd)  # type: ignore
