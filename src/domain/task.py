from enum import Enum
from datetime import datetime

from .project import Project
from .user import User


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


class Task:

    _next_task_id = 1
    def __init__(self, name: str,
                 description: str = None,
                 creation_date: datetime = datetime.now(),
                 project_id: Project = None,
                 assignee: User = None,
                 created_by: User = None,
                 due_date: datetime = None,
                 status: str = "BACKLOG",
                 priority: str = "NORMAL",
                 **kwargs
                 ):
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
        self.project_id = project_id
        self.assignee = assignee
        self.created_by = created_by
        if due_date and due_date.date() < datetime.today().date():
            raise ValueError(f"Due date {due_date.date()} cannot be less than today")
        else:
            self.due_date = due_date
        self.status = self._validate_status(status)
        if priority and priority not in [p.name for p in TaskPriority]:
            raise ValueError(f"{priority} is invalid priority")
        else:
            self.priority = priority

    def _validate_status(self, status):
        if status and status not in [s.name for s in TaskStatus if s.name != "DELETED"]:
            raise ValueError(f"{status} is invalid status")
        else:
            return status

    def __repr__(self):
        return f"<Task {self.id}>: {self.name}, {self.status.name}, {self.creation_date}"
