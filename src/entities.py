from dataclasses import dataclass
from enum import Enum
from typing import Optional


@dataclass
class About:
    version: str


class WorkloadEnv(Enum):
    Prod = "prod"
    Stg = "stg"
    Local = "local"

    @classmethod
    def try_from_string(cls, value: str) -> Optional["WorkloadEnv"]:
        value = value.lower()

        for member in cls:
            if member.value == value:
                return member

        return None


class LogLevel(Enum):
    Debug = "debug"
    Info = "info"

    @classmethod
    def try_from_string(cls, value: str) -> "LogLevel":
        value = value.lower()

        for member in cls:
            if member.value == value:
                return member

        return LogLevel.Info
