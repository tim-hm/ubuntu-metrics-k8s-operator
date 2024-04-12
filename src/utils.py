from typing import Any, Optional, TypeVar

T = TypeVar("T")


def get_or_fail(value: Optional[T], name: str = "unknown") -> T:
    if value is None:
        raise ValueError(f"{name} was None")
    return value


def get_or_default(value: Optional[T], default: T) -> T:
    if value is None:
        return default
    return value


def stringify(instance: Any) -> str:
    class_name = instance.__class__.__name__
    properties_str = ", ".join(f"{attr}={value}" for attr, value in instance.__dict__.items())
    return f"{class_name}{{{properties_str}}}"
