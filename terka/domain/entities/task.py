from typing import Type
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict
from datetime import date, datetime, timedelta
import pandas as pd

from .entity import Entity

class TaskStatus(Enum):
    DELETED = 0
    BACKLOG = 1
    TODO = 2
    IN_PROGRESS = 3
    REVIEW = 4
    DONE = 5


class TaskPriority(Enum):
    UNKNOWN = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class TaskInfo:
    name: str
    description: str
    status: str
    priority: str
    due_date: datetime


class Task(Entity):

    _next_task_id = 1

    def __init__(self,
                 name: str,
                 description: str | None = None,
                 creation_date: datetime = datetime.now(),
                 project: int | None = None,
                 assignee: int | None = None,
                 created_by: int | None = None,
                 due_date: datetime | None = None,
                 status: str = "BACKLOG",
                 priority: str = "NORMAL",
                 sync: bool = True,
                 **kwargs) -> None:
        if not name:
            raise ValueError("task name cannot be empty!")
        if not isinstance(creation_date, datetime):
            raise ValueError(
                "creation_date should be of type datetime.datetime!")
        self._task_id = Task._next_task_id
        Task._next_task_id += 1

        self.name = name
        self.creation_date = creation_date
        self.description = description
        self.project = project
        self.assignee = assignee
        self.created_by = created_by
        if due_date and due_date.date() < datetime.today().date():
            raise ValueError(
                f"Due date {due_date.date()} cannot be less than today")
        else:
            self.due_date = due_date
        self.status = self._cast_to_enum(TaskStatus, status)
        self.priority = self._cast_to_enum(TaskPriority, priority)
        self.sync = sync

    @property
    def total_time_spent(self):
        if self.time_spent:
            return sum([t.time_spent_minutes for t in self.time_spent])
        return 0

    @property
    def time_spent_today(self):
        if self.time_spent:
            return sum([
                t.time_spent_minutes for t in self.time_spent
                if t.creation_date.date() == datetime.today().date()
            ])
        return 0

    def daily_time_entries_hours(
            self,
            start_date: str | date | None = None,
            end_date: str | date | None = None,
            last_n_days: int | None = None) -> dict[str, float]:
        if last_n_days:
            start_date = (datetime.today() - timedelta(last_n_days)).date()
            end_date = datetime.today().date()
        elif isinstance(start_date, str) and isinstance(end_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        dates = [
            date.strftime("%Y-%m-%d") for date in pd.date_range(
                start_date, end_date).to_pydatetime().tolist()
        ]
        entries = dict.fromkeys(dates, 0.0)
        for entry in self.time_spent:
            creation_date = entry.creation_date.date()
            if creation_date >= start_date and creation_date <= end_date:
                day = creation_date.strftime("%Y-%m-%d")
                entries[day] += entry.time_spent_minutes / 60
        return entries

    @property
    def completion_date(self) -> datetime | None:
        for event in self.history:
            if event.new_value in ("DONE", "DELETED"):
                return event.date

    @property
    def is_stale(self):
        if self.history and self.status.name in ("TODO", "IN_PROGRESS",
                                                 "REVIEW"):
            if max([event.date for event in self.history
                    ]) < (datetime.today() - timedelta(days=5)):
                return True
        return False

    @property
    def is_overdue(self):
        if self.due_date and self.due_date <= date.today():
            return True
        return False

    def __repr__(self):
        return f"<Task {self.id}>: {self.name}, {self.status.name}, {self.creation_date}"

    def _cast_to_enum(self, enum: Type[Enum], value: str | Enum) -> Enum:
        return enum[value] if isinstance(value, str) else value

    def __hash__(self):
        return hash(
            ((self.id, self.name, self.description, self.project, self.status,
              self.priority, self.due_date, self.assignee)))

    def __eq__(self, other) -> bool:
        if not isinstance(other, Task):
            return False
        if (self.name, self.description, self.project, self.status,
                self.priority, self.due_date,
                self.assignee) != (other.name, other.description,
                                   other.project, other.status, other.priority,
                                   other.due_date, other.assignee):
            return False
        return True
