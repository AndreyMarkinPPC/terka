from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from enum import Enum

from .entity import Entity
from .task import Task


class CompositeStatus(Enum):
    ACTIVE = 1
    COMPLETED = 2
    DELETED = 3


class Composite(Entity):

    def __init__(self,
                 name: str,
                 description: str = None,
                 creation_date: datetime = datetime.now(),
                 project: int = None,
                 assignee: int = None,
                 status: str = 'ACTIVE',
                 created_by: int = None,
                 **kwargs) -> None:
        if not name:
            raise ValueError('task name cannot be empty!')
        if not isinstance(creation_date, datetime):
            raise ValueError(
                'creation_date should be of type datetime.datetime!')
        self.name = name
        self.creation_date = creation_date
        self.description = description
        self.project = project
        self.assignee = assignee
        self.created_by = created_by
        self.status = status
        self.is_completed = False

    @property
    def project_name(self) -> str:
        if project := self.project_:
            return project.name
        return ''

    @property
    def backlog_tasks(self) -> list[Task]:
        tasks = []
        for entity_task in self.tasks:
            task = entity_task.tasks
            if task.status.name == 'BACKLOG':
                tasks.append(task)
        return tasks

    @property
    def open_tasks(self) -> list[Task]:
        tasks = []
        for entity_task in self.tasks:
            task = entity_task.tasks
            if task.status.name not in ('DONE', 'DELETED'):
                tasks.append(task)
        return tasks

    @property
    def completed_tasks(self) -> list[Task]:
        tasks = []
        for entity_task in self.tasks:
            task = entity_task.tasks
            if task.status.name in ('DONE', 'DELETED'):
                tasks.append(task)
        return tasks

    def complete(self, tasks) -> None:
        incompleted_tasks = list()
        for task in tasks:
            if task.tasks.status.name != 'DONE':
                incompleted_tasks.append(task)
        if incompleted_tasks:
            logging.warning("[composite %d]: %d tasks haven't been completed",
                            self.id, len(incompleted_tasks))
        self.is_completed = True

    def daily_time_entries_hours(self,
                                 last_n_days: int = 14) -> dict[str, float]:
        entries: dict[str, float] = defaultdict(float)
        for task in self.tasks:
            task_entries = task.tasks.daily_time_entries_hours(
                last_n_days=last_n_days)
            for day, hours in task_entries.items():
                entries[day] += hours
        return entries

    @property
    def total_time_spent(self):
        total_time_spent = 0
        for task in self.tasks:
            total_time_spent += task.tasks.total_time_spent
        return total_time_spent
