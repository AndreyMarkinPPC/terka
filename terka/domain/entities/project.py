from __future__ import annotations

from collections import defaultdict
from datetime import date
from datetime import datetime
from enum import Enum
from statistics import median

from terka.domain.entities.entity import Entity
from terka.domain.entities.task import Task


class ProjectStatus(Enum):
    DELETED = 0
    ACTIVE = 1
    ON_HOLD = 2
    COMPLETED = 3


class Project(Entity):

    def __init__(self,
                 name: str,
                 description: str | None = None,
                 created_by: str | None = None,
                 status: str = 'ACTIVE',
                 workspace: int | None = None) -> None:
        self.name = name
        self.description = description
        self.created_by = created_by
        self.status = status
        self.workspace = workspace

    @property
    def workspace_name(self) -> str:
        if workspace := self.workspace_:
            return workspace.name
        return ''

    def _validate_status(self, status: str) -> str:
        if status not in [
                s.name for s in ProjectStatus if s.name != 'DELETED'
        ]:
            raise ValueError(f'{status} is invalid status')
        else:
            return status

    @property
    def total_time_spent(self) -> int:
        total_time_spent_project = 0
        for task in self.tasks:
            total_time_spent_project += task.total_time_spent
        return total_time_spent_project

    @property
    def task_collaborators(self) -> dict[str, int]:
        collaborators = defaultdict(int)
        for task in self.tasks:
            if task_collaborators := task.collaborators:
                for collaborator in task.collaborators:
                    name = collaborator.users.name or 'me'
                    collaborators[name] += task.total_time_spent
            else:
                collaborators['me'] += task.total_time_spent
        return collaborators

    @property
    def overdue_tasks(self) -> list[Task]:
        return [
            task for task in self.open_tasks
            if task.due_date and task.due_date <= datetime.now().date()
        ]

    @property
    def stale_tasks(self) -> list[Task]:
        return [task for task in self.open_tasks if task.is_stale]

    @property
    def median_task_age(self) -> float:
        if self.open_tasks:
            return round(
                median([(datetime.now() - task.creation_date).days
                        for task in self.open_tasks]))
        return 0

    @property
    def backlog(self) -> int:
        return self._count_task_status('BACKLOG')

    @property
    def todo(self) -> int:
        return self._count_task_status('TODO')

    @property
    def in_progress(self) -> int:
        return self._count_task_status('IN_PROGRESS')

    @property
    def review(self) -> int:
        return self._count_task_status('REVIEW')

    @property
    def done(self) -> int:
        return self._count_task_status('DONE')

    @property
    def deleted(self) -> int:
        return self._count_task_status('DELETED')

    @property
    def backlog_tasks(self) -> list[Task]:
        return self._get_tasks_by_statuses(('BACKLOG'))

    @property
    def open_tasks(self) -> list[Task]:
        return self._get_tasks_by_statuses(('TODO', 'IN_PROGRESS', 'REVIEW'))

    @property
    def completed_tasks(self) -> list[Task]:
        return self._get_tasks_by_statuses(('DONE', 'DELETED'))

    @property
    def incompleted_tasks(self) -> list[Task]:
        return self._get_tasks_by_statuses(
            ('BACKLOG', 'TODO', 'IN_PROGRESS', 'REVIEW'))

    def _get_tasks_by_statuses(self, statuses: tuple[str]) -> list[Task]:
        return [task for task in self.tasks if task.status.name in statuses]

    def daily_time_entries_hours(
            self,
            start_date: str | date | None = None,
            end_date: str | date | None = None,
            last_n_days: int | None = None) -> dict[str, float]:
        entries: dict[str, float] = defaultdict(float)
        for task in self.tasks:
            task_entries = task.daily_time_entries_hours(
                start_date, end_date, last_n_days)
            for day, hours in task_entries.items():
                entries[day] += hours
        return entries

    def __str__(self) -> str:
        return f'<Project {self.id}>: {self.name} {self.tasks}'

    def _count_task_status(self, status: str) -> int:
        return [task for task in self.tasks if task.status.name == status]
