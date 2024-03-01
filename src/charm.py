#!/usr/bin/env python3
# Copyright 2024 Tim Holmes-Mitra <tim.holmes-mitra@canonical.com>
# See LICENSE file for licensing details.

import logging
from typing import TYPE_CHECKING

import ops
from workload_manager import WorkloadManager

# if development bring in types via dev paths
if TYPE_CHECKING:
    None
else:  # runtime
    None


logger = logging.getLogger(__name__)


class UbuntuReportd(ops.CharmBase):
    _container: ops.Container
    _workload: WorkloadManager

    def __init__(self, *args):
        super().__init__(*args)
        self._container = self.unit.get_container(WorkloadManager.name)
        self._workload = WorkloadManager(self.container)

        self.framework.observe(self.on[WorkloadManager.name].pebble_ready, self._on_pebble_ready)

    def _on_pebble_ready(self, _: ops.PebbleReadyEvent):
        self.unit.status = ops.MaintenanceStatus("Configuring container")

        if not self.container.can_connect():
            self.unit.status = ops.WaitingStatus("Waiting for Pebble to be available")
            return

        if not self.workload.ready():
            self.unit.status = ops.WaitingStatus("Waiting for AppManager to be ready")
            return

        try:
            self.container.add_layer(
                WorkloadManager.name, self.workload.pebble_layer, combine=True
            )
            self.container.replan()
            self.unit.open_port(protocol="tcp", port=self.workload.port)

            self.unit.set_workload_version(self.workload.version())
            self.unit.status = ops.ActiveStatus()
        except ops.pebble.ConnectionError as e:
            logger.error(f"Failed to connect to Pebble: {e}")
            self.unit.status = ops.BlockedStatus("Could not connect to container")
        except Exception as e:
            logger.error(f"Pebble replan failed: {e}")
            self.unit.status = ops.BlockedStatus("Failed to configure container")

    @property
    def container(self) -> ops.Container:
        return self._container

    @property
    def workload(self) -> WorkloadManager:
        return self._workload


if __name__ == "__main__":  # pragma: nocover
    ops.main(UbuntuReportd)  # type: ignore
