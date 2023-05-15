from datetime import datetime
from dataclasses import dataclass


@dataclass
class AsanaTask:
    id: int
    project: int
    asana_task_id: str
    sync_date: datetime


@dataclass
class AsanaProject:
    id: int
    asana_project_id: str
    sync_date: datetime
