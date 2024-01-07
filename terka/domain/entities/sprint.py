from typing import Set
from collections import defaultdict
from enum import Enum
import logging
from datetime import datetime, date
from dataclasses import dataclass

from .entity import Entity
from .task import Task

logger = logging.getLogger(__name__)


class SprintStatus(Enum):
    PLANNED = 1
    ACTIVE = 2
    COMPLETED = 3
    DELETED = 4


class Sprint(Entity):

    def __init__(self,
                 start_date: datetime = None,
                 end_date: datetime = None,
                 status: str = "PLANNED",
                 goal: str = None,
                 **kwargs) -> None:
        if not start_date and not end_date:
            raise ValueError("Please add start and end date of the sprint")
        if start_date.date() < datetime.today().date():
            raise ValueError(f"start date cannot be less than today")
        if not start_date:
            raise ValueError(
                "Please provide start date for the sprint in YYYY-MM-DD format"
            )
        self.start_date = start_date
        if not end_date:
            raise ValueError(
                "Please provide end date for the sprint in YYYY-MM-DD format")
        self.end_date = end_date
        if end_date.date() < start_date.date():
            raise ValueError(f"Sprint end date cannot be less than start date")
        if end_date.date() < datetime.today().date():
            raise ValueError(f"Sprint end date cannot be less than today")
        self.status = self._validate_status(status)
        self.goal = goal
        self.is_completed = False

    def _validate_status(self, status):
        if status and status not in [s.name for s in SprintStatus]:
            raise ValueError(f"{status} is invalid status")
        else:
            return status

    def complete(self, tasks) -> None:
        incompleted_tasks = list()
        for task in tasks:
            if task.tasks.status.name != "DONE":
                incompleted_tasks.append(task)
        if incompleted_tasks:
            logging.warning("[Sprint %d]: %d tasks haven't been completed",
                            self.id, len(incompleted_tasks))
        self.is_completed = True

    @property
    def velocity(self) -> float:
        return round(sum([t.story_points for t in self.tasks]), 1)

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
    def open_tasks(self):
        return [
            task for task in self.tasks
            if task.tasks.status.name not in ("DONE", "DELETED")
        ]

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
                    name = collaborator.users.name or "me"
                    collaborators[name] += sprint_task.tasks.total_time_spent
            else:
                collaborators["me"] += sprint_task.tasks.total_time_spent
        return collaborators

    @property
    def collaborators_as_string(self):
        collaborators = []
        for user, story_point in sorted(self.collaborators.items(),
                                        key=lambda x: x[1],
                                        reverse=True):
            collaborators.append(f"{user} ({round(story_point, 2)})")
        return ",".join(collaborators)

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
