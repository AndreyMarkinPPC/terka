from dataclasses import dataclass


@dataclass
class AsanaTask:
    id: int
    project: int
    asana_task_id: str


@dataclass
class AsanaProject:
    id: int
    asana_project_id: str
