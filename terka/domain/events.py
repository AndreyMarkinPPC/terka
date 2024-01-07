from typing import Any
from datetime import datetime
from dataclasses import dataclass, asdict
from terka.domain.entities.task import TaskInfo


@dataclass
class Event:
    ...


# Base
@dataclass
class Created(Event):
    id: int


@dataclass
class Completed(Event):
    id: int
    comment: str | None = None


@dataclass
class Deleted(Event):
    id: int


@dataclass
class Updated(Event):
    id: int


@dataclass
class Commented(Event):
    id: int
    text: str


# TASKS
@dataclass
class TaskEvent(Event):
    ...


@dataclass
class SprintEvent(Event):
    ...


@dataclass
class ProjectEvent(Event):
    ...


@dataclass
class TaskCreated(TaskEvent):
    id: int


@dataclass
class TaskCompleted(Completed):
    hours: int | None = None


@dataclass
class TaskDeleted(Deleted):
    ...


@dataclass
class UpdateMask:
    name: str | None = None
    description: str | None = None
    project: str | None = None
    assignee: str | None = None
    due_date: str | None = None
    status: str = "BACKLOG"
    priority: str = "NORMAL"

    def get_only_set_attributes(self) -> dict:
        return {key: value for key, value in asdict(self).items() if value}


@dataclass
class TaskUpdated(TaskEvent):
    task: int
    type: str
    old_value: Any
    new_value: Any


@dataclass
class TaskCommentAdded(TaskEvent):
    id: int
    text: str


@dataclass
class TaskHoursSubmitted(TaskEvent):
    id: int
    hours: int


@dataclass
class TaskCollaboratorAdded(TaskEvent):
    id: int
    collaborator: str


@dataclass
class TaskTagAdded(TaskEvent):
    id: int
    tag: str


@dataclass
class TaskAddedToSprint(TaskEvent):
    id: int
    sprint_id: int


@dataclass
class TaskAddedToEpic(TaskEvent):
    id: int
    epic_id: int


@dataclass
class TaskAddedToStory(TaskEvent):
    id: int
    story_id: int


@dataclass
class TaskSynced(TaskEvent):
    id: int
    project: int
    asana_task_id: str
    sync_date: datetime


# PROJECTS
@dataclass
class ProjectCreated(Created):
    ...


@dataclass
class ProjectCompleted(Completed):
    ...


@dataclass
class ProjectDeleted(Deleted):
    ...


@dataclass
class ProjectCommented(Commented):
    ...


@dataclass
class ProjectSynced(ProjectEvent):
    id: int
    asana_project_id: str
    sync_date: datetime


@dataclass
class SprintTaskStoryPointAssigned(SprintEvent):
    id: int
    story_points: float


# EPICS
@dataclass
class EpicCreated(Created):
    ...


@dataclass
class EpicCompleted(Completed):
    ...


@dataclass
class EpicDeleted(Deleted):
    ...


@dataclass
class EpicUpdated(Updated):
    ...


@dataclass
class EpicCommented(Commented):
    ...


# STORIES
@dataclass
class StoryCreated(Created):
    ...


@dataclass
class StoryCompleted(Completed):
    ...


@dataclass
class StoryDeleted(Deleted):
    ...


@dataclass
class StoryUpdated(Updated):
    ...


@dataclass
class StoryCommented(Commented):
    ...


# SPRINTS
@dataclass
class SprintCompleted(Completed):
    ...

@dataclass
class SprintDeleted(Deleted):
    ...
