from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from terka import exceptions
from terka.domain.entities.entity import Entity
from terka.domain.entities.task import Task

logger = logging.getLogger(__name__)


class SprintStatus(Enum):
    PLANNED = 1
    ACTIVE = 2
    COMPLETED = 3
    DELETED = 4


class Sprint(Entity):

    def __init__(self,
                 start_date: datetime | None = None,
                 end_date: datetime | None = None,
                 status: str = 'PLANNED',
                 capacity: int = 40,
                 goal: str | None = None,
                 started_at: datetime | None = None,
                 **kwargs) -> None:
        if not start_date or not end_date:
            raise ValueError('Please add start and end date of the sprint')
        if start_date.date() < datetime.today().date():
            raise ValueError(f'start date cannot be less than today')
        if not start_date:
            raise ValueError(
                'Please provide start date for the sprint in YYYY-MM-DD format'
            )
        self.start_date = start_date
        if not end_date:
            raise ValueError(
                'Please provide end date for the sprint in YYYY-MM-DD format')
        self.end_date = end_date
        if end_date.date() < start_date.date():
            raise ValueError(f'Sprint end date cannot be less than start date')
        if end_date.date() < datetime.today().date():
            raise ValueError(f'Sprint end date cannot be less than today')
        self.status = self._validate_status(status)
        self.goal = goal
        if capacity < 0:
            raise exceptions.TerkaSprintInvalidCapacity(
                f'Invalid capacity {capacity}! Sprint capacity cannot 0 or less'
            )
        self.capacity = capacity
        self.started_at = started_at
        self.completed_at = None

    def _validate_status(self, status):
        if status and status not in [s.name for s in SprintStatus]:
            raise ValueError(f'{status} is invalid status')
        else:
            return status

    def complete(self, tasks) -> None:
        incompleted_tasks = list()
        for task in tasks:
            if task.tasks.status.name != 'DONE':
                incompleted_tasks.append(task)
        if incompleted_tasks:
            logging.warning("[Sprint %d]: %d tasks haven't been completed",
                            self.id, len(incompleted_tasks))

    @property
    def is_completed(self) -> bool:
        return self.status == SprintStatus.COMPLETED

    @property
    def overplanned(self) -> bool:
        return self.velocity > self.capacity

    @property
    def remaining_capacity(self) -> float:
        if not self.overplanned:
            return self.capacity - self.velocity
        return 0

    @property
    def velocity(self) -> float:
        return round(sum([float(t.story_points) for t in self.tasks]), 1)

    @property
    def utilization(self) -> float:
        if not (velocity := self.velocity) or not (total_time_spent :=
                                                   self.total_time_spent):
            return 0
        return total_time_spent / (velocity * 60)

    @property
    def time_spent_today(self):
        time_spent_today = 0
        for sprint_task in self.tasks:
            time_spent_today += sprint_task.tasks.time_spent_today
        return time_spent_today

    @property
    def total_time_spent(self):
        total_time_spent_sprint = 0
        for sprint_task in self.tasks:
            total_time_spent_sprint += sprint_task.tasks.total_time_spent
        return total_time_spent_sprint

    @property
    def unplanned_tasks(self) -> list[Task]:
        tasks = []
        for entity_task in self.tasks:
            if entity_task.unplanned:
                tasks.append(entity_task.tasks)
        return tasks

    @property
    def open_tasks(self) -> list[Task]:
        tasks = []
        for entity_task in self.tasks:
            task = entity_task.tasks
            if task.status.name not in ('DONE', 'DELETED'):
                task.story_points = entity_task.story_points
                tasks.append(task)
        return tasks

    @property
    def completed_tasks(self) -> list[Task]:
        tasks = []
        for entity_task in self.tasks:
            task = entity_task.tasks
            if task.status.name in ('DONE', 'DELETED'):
                task.story_points = entity_task.story_points
                tasks.append(task)
        return tasks

    @property
    def pct_completed(self) -> float:
        if (total_tasks := len(self.tasks)) > 0:
            return (total_tasks - len(self.open_tasks)) / total_tasks
        return 0

    @property
    def collaborators(self):
        collaborators = defaultdict(int)
        for sprint_task in self.tasks:
            if task_collaborators := sprint_task.tasks.collaborators:
                for collaborator in task_collaborators:
                    name = collaborator.users.name or 'me'
                    collaborators[name] += sprint_task.tasks.total_time_spent
            else:
                collaborators['me'] += sprint_task.tasks.total_time_spent
        return collaborators

    @property
    def collaborators_as_string(self):
        collaborators = []
        for user, story_point in sorted(self.collaborators.items(),
                                        key=lambda x: x[1],
                                        reverse=True):
            collaborators.append(f'{user} ({round(story_point, 2)})')
        return ','.join(collaborators)

    def daily_time_entries_hours(self) -> dict[str, float]:
        entries: dict[str, float] = defaultdict(float)
        for task in self.tasks:
            task_entries = task.tasks.daily_time_entries_hours(
                self.start_date, self.end_date)
            for day, hours in task_entries.items():
                entries[day] += hours
        return entries


@dataclass
class SprintTask:
    sprint: int
    task: int
    story_points: int = 0
    #TODO: add actual_time_spent: int = 0
    is_active_link: bool = True
    unplanned: bool = False
