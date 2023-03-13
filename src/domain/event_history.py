from enum import Enum, auto
from datetime import datetime


class EventType(Enum):
    STATUS = auto()
    DUE_DATE = auto()
    NAME = auto()
    PROJECT = auto()
    DESCRIPTION = auto()
    PRIORITY = auto()
    ASSIGNEE = auto()


class BaseEvent:

    def __init__(self,
                 event_type: str,
                 old_value: str,
                 new_value: str,
                 date: datetime = datetime.now()) -> None:
        if event_type.upper() not in [e.name for e in EventType]:
            raise ValueError(f"{event_type} is invalid EventType")
        self.type = event_type.upper()
        self.old_value = old_value
        self.new_value = new_value
        self.date = date


class TaskEvent(BaseEvent):

    def __init__(self, task_id: int, event_type: str, old_value: str,
                 new_value: str, date: datetime) -> None:
        self.task = task_id
        super().__init__(event_type=event_type,
                         old_value=old_value,
                         new_value=new_value,
                         date=date)


class ProjectEvent(BaseEvent):

    def __init__(self, project_id: int, event_type: str, old_value: str,
                 new_value: str, date: datetime) -> None:
        self.project = project_id
        super().__init__(event_type=event_type,
                         old_value=old_value,
                         new_value=new_value,
                         date=date)
