#!/usr/bin/env python3
# Copyright 2024 Tim Holmes-Mitra <tim.holmes-mitra@canonical.com>
# See LICENSE file for licensing details.

import logging
from typing import TYPE_CHECKING

import ops
from workload_config_manager import WorkloadConfigManager

# if development bring in types via dev paths
if TYPE_CHECKING:
    None
else:  # runtime
    None


logger = logging.getLogger(__name__)


class UbuntuReportd(ops.CharmBase):

    def __init__(self, *args):
        super().__init__(*args)
        self._container = self.unit.get_container(WorkloadConfigManager.name)
        self._app_manager = WorkloadConfigManager()

        self.framework.observe(self.on[WorkloadConfigManager.name].pebble_ready, self._on_pebble_ready)

    def _on_pebble_ready(self, _: ops.PebbleReadyEvent):
        self.unit.status = ops.MaintenanceStatus("Configuring container")

        if not self._container.can_connect():
            self.unit.status = ops.WaitingStatus("Waiting for Pebble to be available")
            return

        if not self._app_manager.ready():
            self.unit.status = ops.WaitingStatus("Waiting for AppManager to be ready")
            return

        try:
            self._container.add_layer(
                WorkloadConfigManager.name, self._app_manager.pebble_layer(), combine=True
            )
            self._container.replan()
            self.unit.open_port(protocol="tcp", port=self._app_manager.port)
            self.unit.status = ops.ActiveStatus()
        except ops.pebble.ConnectionError as e:
            logger.error(f"Failed to connect to Pebble: {e}")
            self.unit.status = ops.BlockedStatus("Could not connect to container")
        except Exception as e:
            logger.error(f"Pebble replan failed: {e}")
            self.unit.status = ops.BlockedStatus("Failed to configure container")


if __name__ == "__main__":  # pragma: nocover
    ops.main(UbuntuReportd)  # type: ignore
