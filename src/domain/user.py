from datetime import datetime

from .project import Project


class User:

    def __init__(self, name: str, **kwargs):
        self.name = name

    def __repr__(self):
        return f"<User {self.name}>"

    def __eq__(self, other):
       if not isinstance(other, User):
           return False
       return other.name == self.name

    def create_task(self, name: str, project_id: int = None) -> 'Task':
        from .task import Task
        task = Task(name)
        task.created_by = self.name
        if project_id:
            task.project = project_id
        return task

    def create_project(self, project_name: str) -> Project:
        return Project(project_name)

    def set_task_due_date(self, task: 'Task', due_date: datetime) -> None:
        task.due_date = due_date
