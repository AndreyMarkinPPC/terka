from collections import defaultdict
from datetime import date
from enum import Enum


class ProjectStatus(Enum):
    DELETED = 0
    ACTIVE = 1
    ON_HOLD = 2
    COMPLETED = 3


class Project:

    _next_project_id = 1

    def __init__(self,
                 name: str,
                 description: str | None = None,
                 created_by: str | None = None,
                 status: str = "ACTIVE",
                 workspace: int | None  = None,
                 **kwargs) -> None:
        self._project_id = Project._next_project_id
        Project._next_project_id += 1
        self.name = name
        self.description = description
        self.created_by = created_by
        self.status = status
        self.workspace = workspace

    def _validate_status(self, status):
        if status not in [
                s.name for s in ProjectStatus if s.name != "DELETED"
        ]:
            raise ValueError(f"{status} is invalid status")
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
                    name = collaborator.users.name or "me"
                    collaborators[name] += task.total_time_spent
            else:
                collaborators["me"] += task.total_time_spent
        return collaborators

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

    def __str__(self):
        return f"<Project {self.id}>: {self.name} {self.tasks}"
