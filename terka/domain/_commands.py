from typing import Dict, Literal, Optional, Type
from dataclasses import dataclass, asdict


@dataclass
class Command:

    def get_only_set_attributes(self) -> dict:
        return {key: value for key, value in asdict(self).items() if value}

    @classmethod
    def from_kwargs(cls, **kwargs: dict) -> Type["Command"]:
        return cls(**{
            k: v
            for k, v in kwargs.items() if k in cls.__match_args__ and v
        })


@dataclass
class Edit(Command):
    ...


@dataclass
class Create(Command):
    ...


@dataclass
class Update(Command):
    ...


@dataclass
class CreateTask(Command):
    name: str | None = None
    description: str | None = None
    project: str | None = None
    tags: str | None = None
    collaborators: str | None = None
    assignee: str | None = None
    due_date: str | None = None
    status: str = "BACKLOG"
    priority: str = "NORMAL"
    sprint_id: str | None = None
    epic_id: str | None = None
    story_id: str | None = None


@dataclass
class CompleteTask(Command):
    id: int
    comment: str | None = None
    hours: int | None = None


@dataclass
class DeleteTask(Command):
    id: int
    comment: str | None = None
    hours: int | None = None
    entity_type: Literal["sprint", "epic", "story"] | None = None
    entity_id: int | None = None


@dataclass
class UpdateTask(Command):
    id: int
    name: str | None = None
    description: str | None = None
    project: str | None = None
    tags: str | None = None
    collaborators: str | None = None
    assignee: str | None = None
    due_date: str | None = None
    status: str | None= None 
    priority: str | None = None 
    sprint_id: str | None = None
    epic_id: str | None = None
    story_id: str | None = None


    def __bool__(self) -> bool:
        return False


@dataclass
class TagTask(Command):
    id: int
    tag: int


@dataclass
class CollaborateTask(Command):
    id: int
    collaborator: str


@dataclass
class AssignTask(Command):
    id: int
    user: str


@dataclass
class AddTask(Command):
    id: int
    entity_type: Literal["sprint", "epic", "story"]
    entity_id: int


@dataclass
class NoteTask(Command):
    id: int
    text: str


@dataclass
class CommentTask(Command):
    id: int
    text: str


@dataclass
class Start(Command):
    ...


@dataclass
class Create(Command):
    ...


@dataclass
class List(Command):
    ...


@dataclass
class Show(Command):
    ...


@dataclass
class Get(Command):
    ...


@dataclass
class Collaborate(Command):
    ...


@dataclass
class Track(Command):
    ...


@dataclass
class Tag(Command):
    ...


@dataclass
class Add(Command):
    ...


@dataclass
class Note(Command):
    ...


@dataclass
class Comment(Command):
    ...


@dataclass
class Delete(Command):
    ...


@dataclass
class Connect(Command):
    ...


@dataclass
class Report(Command):
    ...


@dataclass
class CreateProject(Command):
    name: str | None = None
    description: str | None = None
    workspace: int = 1
    status: str = "ACTIVE"


@dataclass
class ShowProject(Command):
    id: int
    print_options: dict


@dataclass
class CreateSprint(Command):
    goal: str | None = None
    start_date: str | None = None
    end_date: str | None = None

    def __bool__(self) -> bool:
        if self.start_date and self.end_date:
            return True
        return False


@dataclass
class StartSprint(Command):
    id: int
