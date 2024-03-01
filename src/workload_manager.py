import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import ops
import requests

if TYPE_CHECKING:  # development (type checking)
    None
else:  # runtime
    None


logger = logging.getLogger(__name__)

class WorkloadManager:

    name: str = "reportd"
    port: int = 8080
    _container: ops.Container

    def __init__(self, container: ops.Container):
        self._container = container
        None

    def ready(self) -> bool:
        return True

    @property
    def pebble_layer(self) -> ops.pebble.Layer:
        command = " ".join(["/app/ubuntu-reportd", "-vvv"])
        environment = {"UBUNTU-REPORTD_SERVERPORT": str(self.port)}

        layer: ops.pebble.LayerDict = {
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

    @property
    def container(self) -> ops.Container:
        return self._container

    def api_url(self, path = "") -> str:
        """Omit the leading '/'. For example, path="about" gives http://localhost:8080/about."""
        return f"http://localhost:{self.port}/{path}"

    def version(self) -> str:
        if not self.container.can_connect():
            return "unavailable"

        try:
            response = requests.get(self.api_url("about"), timeout=10)
            about = About(**response.json())
            return about.version
        except ops.pebble.ConnectionError:
            return "unknown"
        except json.JSONDecodeError as e:
            logger.warning(f"Error parsing /about response: {e}")
            return "unknown"
        except TypeError as e:
            logger.warning(f"Json result valid but does not match about: {e}")
            return "unknown"

@dataclass
class About:
    version: str
