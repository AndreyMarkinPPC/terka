from enum import Enum

class ProjectStatus(Enum):
    DELETED = 0
    ACTIVE = 1
    ON_HOLD = 2


class Project:

    _next_project_id = 1
    def __init__(self, name: str, description: str = None, created_by: str = None, status: str = "ACTIVE"):
        self._project_id = Project._next_project_id
        Project._next_project_id += 1
        self.name = name
        self.description = description
        self.created_by = created_by
        self.status = status
        # self.tasks = set()

    def _validate_status(self, status):
        if status not in [s.name for s in ProjectStatus if s.name != "DELETED"]:
            raise ValueError(f"{status} is invalid status")
        else:
            return status


    def __str__(self):
        return f"<Project {self.id}>: {self.name} {self.tasks}"
