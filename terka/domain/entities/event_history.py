from enum import Enum, auto
from dataclasses import dataclass
from datetime import datetime


class EventType(Enum):
    STATUS = auto()
    DUE_DATE = auto()
    NAME = auto()
    PROJECT = auto()
    DESCRIPTION = auto()
    PRIORITY = auto()
    ASSIGNEE = auto()


@dataclass
class TaskEvent:
    task: int
    event_type: str
    old_value: str
    new_value: str
    date: datetime = datetime.now()

    def __post__init__(self) -> None:
        if self.event_type.upper() not in [e.name for e in EventType]:
            raise ValueError(f"{self.event_type} is invalid EventType")


@dataclass
class ProjectEvent:
    project: int
    event_type: str
    old_value: str
    new_value: str
    date: datetime = datetime.now()

    def __post__init__(self) -> None:
        if self.event_type.upper() not in [e.name for e in EventType]:
            raise ValueError(f"{self.event_type} is invalid EventType")
