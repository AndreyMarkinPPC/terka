from typing import Set
from enum import Enum
import logging
from datetime import datetime
from dataclasses import dataclass

from src.domain.task import Task

logger = logging.getLogger(__name__)


class SprintStatus(Enum):
    PLANNED = 1
    ACTIVE = 2
    COMPLETED = 3


class Sprint:

    def __init__(self,
                 start_date: datetime = None,
                 end_date: datetime = None,
                 status: str = "PLANNED",
                 goal: str = None,
                 **kwargs) -> None:
        if start_date.date()  < datetime.today().date():
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
        self.tasks: Set[Task, ...] = set()
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


@dataclass
class SprintTask:
    sprint: int
    task: int
    story_points: int = 0
    #TODO: add actual_time_spent: int = 0
    is_active_link: bool = True
