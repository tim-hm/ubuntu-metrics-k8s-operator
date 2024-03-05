import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import requests
from utils import get_or_fail

logger = logging.getLogger(__name__)


@dataclass
class About:
    version: str


@dataclass
class Workload:
    name: str
    port: int
    db_name: str
    db_relation_name: str
    db_host: str
    db_port: int
    db_username: str
    db_password: str

    def api_url(self, path="") -> str:
        return f"http://localhost:{self.port}/{path}"

    def fetch_version(self) -> str:
        try:
            response = requests.get(self.api_url("about"), timeout=10)
            about = About(**response.json())
            return about.version
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse response: {e}")
            return "unknown"
        except TypeError as e:
            logger.warning(f"Failed to construct About: {e}")
            return "unknown"


class WorkloadState(Enum):
    Ready = 1
    ContainerNotReady = 2
    DbNotReady = 3


class WorkloadBuilder:
    def __init__(self) -> None:
        self.name: Optional[str] = None
        self.port: Optional[int] = None
        self.db_name: Optional[str] = None
        self.db_relation_name: Optional[str] = None
        self.db_host: Optional[str] = None
        self.db_port: Optional[int] = None
        self.db_username: Optional[str] = None
        self.db_password: Optional[str] = None

    def set_name(self, value: str) -> "WorkloadBuilder":
        self.name = value
        return self

    def set_port(self, value: int) -> "WorkloadBuilder":
        self.port = value
        return self

    def set_db_name(self, value: str) -> "WorkloadBuilder":
        self.db_name = value
        return self

    def set_db_relation_name(self, value: str) -> "WorkloadBuilder":
        self.db_relation_name = value
        return self

    def set_db_host(self, value: str) -> "WorkloadBuilder":
        self.db_host = value
        return self

    def set_db_port(self, value: int) -> "WorkloadBuilder":
        self.db_port = value
        return self

    def set_db_username(self, value: str) -> "WorkloadBuilder":
        self.db_username = value
        return self

    def set_db_password(self, value: str) -> "WorkloadBuilder":
        self.db_password = value
        return self

    def check_is_ready(self) -> bool:
        return all(
            value is not None
            for value in [
                self.name,
                self.port,
                self.db_name,
                self.db_relation_name,
                self.db_host,
                self.db_port,
                self.db_username,
                self.db_password,
            ]
        )

    def build(self) -> Workload:
        return Workload(
            name=get_or_fail(self.name, "name"),
            port=get_or_fail(self.port, "port"),
            db_name=get_or_fail(self.db_name, "db_name"),
            db_relation_name=get_or_fail(self.db_relation_name, "db_relation_name"),
            db_host=get_or_fail(self.db_host, "db_host"),
            db_port=get_or_fail(self.db_port, "db_port"),
            db_username=get_or_fail(self.db_username, "db_username"),
            db_password=get_or_fail(self.db_password, "db_password"),
        )
