from typing import Dict, Literal, Optional, Type
from dataclasses import dataclass, asdict


@dataclass
class Command:

    def get_only_set_attributes(self) -> dict:
        set_attributes = {}
        for key, value in asdict(self).items():
            if key == "due_date" or value:
                set_attributes[key] = value
        return set_attributes

    @classmethod
    def from_kwargs(cls, **kwargs: dict) -> Type["Command"]:
        return cls(**{
            k: v
            for k, v in kwargs.items() if k in cls.__match_args__ and v is not None
        })

    def __bool__(self) -> bool:
        return all(f for f in self.__dataclass_fields__ if f != "id")


# Base Commands
@dataclass
class Note(Command):
    id: int
    text: str


@dataclass
class Comment(Command):
    id: int
    text: str

    def __bool__(self) -> bool:
        if self.text:
            return True
        return False


@dataclass
class Complete(Command):
    id: int


@dataclass
class Delete(Command):
    id: int


@dataclass
class Tag(Command):
    id: int
    tag: int


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
    id: int


@dataclass
class Get(Command):
    ...


@dataclass
class Collaborate(Command):
    id: int
    collaborator: str


@dataclass
class Track(Command):
    ...


@dataclass
class Add(Command):
    ...


@dataclass
class Connect(Command):
    ...


@dataclass
class Report(Command):
    ...


@dataclass
class Sync(Command):
    id: int | None = None


# TASKS
@dataclass
class CreateTask(Command):
    name: str | None = None
    description: str | None = None
    project: str | None = None
    assignee: str | None = None
    due_date: str | None = None
    status: str = "BACKLOG"
    priority: str = "NORMAL"
    sync: bool = True


@dataclass
class CompleteTask(Complete):
    hours: int | None = None


@dataclass
class DeleteTask(Delete):
    hours: int | None = None
    sprint: str | None = None
    epic: str | None = None
    story: str | None = None


@dataclass
class UpdateTask(Command):
    id: int
    name: str | None = None
    description: str | None = None
    project: str | None = None
    assignee: str | None = None
    due_date: str | None = None
    status: str | None = None
    priority: str | None = None


@dataclass
class TagTask(Tag):
    ...


@dataclass
class CollaborateTask(Collaborate):
    ...


@dataclass
class AssignTask(Command):
    id: int
    user: str


@dataclass
class AddTask(Command):
    id: int
    sprint: str | None = None
    epic: str | None = None
    story: str | None = None
    story_points: float | None = None


@dataclass
class NoteTask(Note):
    ...


@dataclass
class CommentTask(Comment):
    ...


@dataclass
class TrackTask(Command):
    id: int
    hours: int | None = None

    def __bool__(self) -> bool:
        if self.hours:
            return True
        return False


@dataclass
class SyncTask(Sync):
    ...


# PROJECT
@dataclass
class CreateProject(Command):
    name: str | None = None
    description: str | None = None
    workspace: int = 1
    status: str = "ACTIVE"


@dataclass
class UpdateProject(Command):
    id: int
    name: str | None = None
    description: str | None = None
    workspace: str | None = None
    status: str | None = None


@dataclass
class CompleteProject(Complete):
    ...


@dataclass
class DeleteProject(Delete):
    ...


@dataclass
class CommentProject(Comment):
    ...


@dataclass
class TagProject(Tag):
    ...


@dataclass
class ShowProject(Show):
    ...


@dataclass
class ListProject(List):
    ...


@dataclass
class ListTask(List):
    ...


@dataclass
class SyncProject(Sync):
    ...


# SPRINT
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


@dataclass
class CompleteSprint(Complete):
    ...


@dataclass
class ListSprint(List):
    ...


# EPIC
@dataclass
class CreateEpic(Command):
    name: str | None = None
    description: str | None = None
    project: str | None = None


@dataclass
class CompleteEpic(Complete):
    ...


@dataclass
class DeleteEpic(Delete):
    ...


@dataclass
class UpdateEpic(Command):
    id: int
    name: str | None = None
    description: str | None = None
    project: str | None = None


@dataclass
class CommentEpic(Comment):
    ...


@dataclass
class AddEpic(Command):
    id: int
    sprint: int


@dataclass
class ListEpic(List):
    ...


# STORIES
@dataclass
class CreateStory(Command):
    name: str | None = None
    description: str | None = None
    project: str | None = None


@dataclass
class CompleteStory(Complete):
    ...


@dataclass
class DeleteStory(Delete):
    ...


@dataclass
class UpdateStory(Command):
    id: int
    name: str | None = None
    description: str | None = None
    project: str | None = None


@dataclass
class CommentStory(Comment):
    ...


@dataclass
class AddStory(Command):
    id: int
    sprint: int


# WORKSPACES
@dataclass
class CreateWorkspace(Command):
    name: str | None = None
    description: str | None = None


@dataclass
class DeleteWorkspace(Delete):
    ...


# TAGS
@dataclass
class ShowTag(Show):
    ...


@dataclass
class ListTag(List):
    ...


# USERS
@dataclass
class ShowUser(Show):
    ...


@dataclass
class ListUser(List):
    ...


# Notes
@dataclass
class ShowNote(Show):
    ...
