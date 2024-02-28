import logging
from typing import TYPE_CHECKING

import ops

if TYPE_CHECKING:  # development (type checking)
    None
else:  # runtime
    None


logger = logging.getLogger(__name__)

class WorkloadConfigManager:

    name = "reportd"
    port = 8080

    def __init__(self):
        None

    def ready(self) -> bool:
        return True

    def pebble_layer(self) -> ops.pebble.LayerDict:
        command = " ".join(["/app/ubuntu-reportd", "-vvv"])
        environment = {"UBUNTU-REPORTD_SERVERPORT": self.port}

        layer = {
            "summary": "reportd base layer definition",
            "services": {
                self.name: {
                    "override": "replace",
                    "summary": f"{self.name} pebble config layer",
                    "startup": "enabled",
                    "command": command,
                    "environment": environment,
                }
            },
        }
        return ops.pebble.Layer(layer)
