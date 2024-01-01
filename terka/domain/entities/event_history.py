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
    ADDED_TO_SPRINT = auto()
    REMOVED_FROM_SPRINT = auto()
    ADDED_TO_EPIC = auto()
    REMOVED_FROM_EPIC = auto()
    ADDED_TO_STORY = auto()
    REMOVED_FROM_STORY = auto()


@dataclass
class TaskEvent:
    task: int
    type: str
    old_value: str
    new_value: str
    date: datetime = datetime.now()

    def __post_init__(self) -> None:
        try:
            EventType[self.type]
        except KeyError as e:
            raise ValueError(
                f"{self.type} is invalid EventType for Task") from None
        # TODO: Select better name
        self.syncable = self.type in ("STATUS", "DUE_DATE", "NAME",
                                        "PROJECT", "DESCRIPTION", "PRIORITY")


@dataclass
class ProjectEvent:
    project: int
    event_type: str
    old_value: str
    new_value: str
    date: datetime = datetime.now()

    def __post_init__(self) -> None:
        if self.event_type.upper() not in [e.name for e in EventType]:
            raise ValueError(f"{self.event_type} is invalid EventType")
