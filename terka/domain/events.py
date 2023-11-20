from dataclasses import dataclass, asdict
from terka.domain.task import TaskInfo


@dataclass
class Event:
    ...


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
class TaskCompleted(TaskEvent):
    id: int
    comment: str | None = None
    hours: int | None = None


@dataclass
class TaskDeleted(TaskCompleted):
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
    id: int
    update_mask: UpdateMask


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
class ProjectCreated(ProjectEvent):
    id: int


@dataclass
class SprintTaskStoryPointAssigned(SprintEvent):
    id: int
    story_points: float
