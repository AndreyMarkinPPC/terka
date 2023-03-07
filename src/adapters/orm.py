from sqlalchemy import (
    Table,
    MetaData,
    Column,
    Integer,
    String,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    event,
)
from sqlalchemy.orm import mapper, registry, relationship, validates, declarative_base

from src.domain.task import Task, TaskStatus, TaskPriority
from src.domain.user import User
from src.domain.project import Project, ProjectStatus
from src.domain.event_history import TaskEvent, ProjectEvent, EventType
from src.domain.commentary import TaskCommentary, ProjectCommentary
from src.domain.tag import BaseTag, TaskTag, ProjectTag
from src.domain.collaborators import TaskCollaborator, ProjectCollaborator

metadata = MetaData()

tasks = Table("tasks", metadata,
              Column("id", Integer, primary_key=True, autoincrement=True),
              Column("name", String(255)),
              Column("creation_date", DateTime, nullable=True),
              Column("description", String(1000), nullable=True),
              Column("project", ForeignKey("projects.id"), nullable=True),
              Column("assignee", ForeignKey("users.id"), nullable=True),
              Column("created_by", ForeignKey("users.id"), nullable=True),
              Column("due_date", Date, nullable=True),
              Column("status", Enum(TaskStatus)),
              Column("priority", Enum(TaskPriority)))

projects = Table("projects", metadata,
                 Column("id", Integer, primary_key=True, autoincrement=True),
                 Column("name", String(255)), Column("description",
                                                     String(255)),
                 Column("status", Enum(ProjectStatus)))

task_events = Table(
    "task_events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("task", ForeignKey("tasks.id"), nullable=True),
    Column("date", DateTime, nullable=False),
    Column("type", Enum(EventType)),
    Column("old_value", String(225)),
    Column("new_value", String(225)),
)

project_events = Table(
    "project_events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project", ForeignKey("projects.id"), nullable=True),
    Column("date", DateTime, nullable=False),
    Column("type", Enum(EventType)),
    Column("old_value", String(225)),
    Column("new_value", String(225)),
)

commentaries = Table(
    "commentaries",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("source", String(50)),
    Column("task", ForeignKey("tasks.id"), nullable=True),
    Column("element_id", Integer),
    Column("date", DateTime, nullable=False),
    Column("text", String(225)),
)

task_commentaries = Table(
    "task_commentaries",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("task", ForeignKey("tasks.id"), nullable=True),
    Column("date", DateTime, nullable=False),
    Column("text", String(225)),
)

project_commentaries = Table(
    "project_commentaries",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project", ForeignKey("projects.id"), nullable=True),
    Column("date", DateTime, nullable=False),
    Column("text", String(225)),
)

users = Table("users", metadata,
              Column("id", Integer, primary_key=True, autoincrement=True),
              Column("name", String(50)))

tags = Table("tags", metadata,
              Column("id", Integer, primary_key=True, autoincrement=True),
              Column("text", String(50)))

task_tags = Table("task_tags", metadata,
             Column("id", Integer, primary_key=True, autoincrement=True),
             Column("task", ForeignKey("tasks.id"), nullable=True),
             Column("tag", ForeignKey("tags.id"), nullable=True))

project_tags = Table("project_tags", metadata,
             Column("id", Integer, primary_key=True, autoincrement=True),
             Column("project", ForeignKey("projects.id"), nullable=True),
             Column("tag", ForeignKey("tags.id"), nullable=True))

task_collaborators = Table("task_collaborators", metadata,
             Column("id", Integer, primary_key=True, autoincrement=True),
             Column("task", ForeignKey("tasks.id"), nullable=True),
             Column("collaborator", ForeignKey("users.id"), nullable=True))

project_collaborators = Table("project_collaborators", metadata,
             Column("id", Integer, primary_key=True, autoincrement=True),
             Column("project", ForeignKey("projects.id"), nullable=True),
             Column("collaborator", ForeignKey("users.id"), nullable=True))

def start_mappers():
    task_commentary_mapper = mapper(TaskCommentary, task_commentaries)
    project_commentary_mapper = mapper(ProjectCommentary, project_commentaries)
    task_event_mapper = mapper(TaskEvent, task_events)
    project_event_mapper = mapper(ProjectEvent, project_events)
    user_mapper = mapper(User, users)
    tag_mapper = mapper(BaseTag, tags)
    task_tag_mapper = mapper(TaskTag, task_tags)
    project_tag_mapper = mapper(ProjectTag, project_tags)
    task_collaborator_mapper = mapper(TaskCollaborator, task_collaborators)
    project_collaborator_mapper = mapper(ProjectCollaborator, project_collaborators)
    task_mapper = mapper(Task,
                         tasks,
                         properties={
                             "collaborators":
                             relationship(task_collaborator_mapper,
                                          collection_class=set,
                                          cascade="all, delete-orphan"),
                             "tags":
                             relationship(task_tag_mapper,
                                          collection_class=set,
                                          cascade="all, delete-orphan"),
                             "commentaries":
                             relationship(task_commentary_mapper,
                                          collection_class=list,
                                          cascade="all, delete-orphan"),
                             "history":
                             relationship(task_event_mapper,
                                          collection_class=list,
                                          cascade="all, delete-orphan"),
                         })
    project_mapper = mapper(Project,
                            projects,
                            properties={
                                 "collaborators":
                                 relationship(project_collaborator_mapper,
                                              collection_class=set,
                                              cascade="all, delete-orphan"),
                                "tasks":
                                relationship(task_mapper,
                                             collection_class=set),
                                 "tags":
                                 relationship(project_tag_mapper,
                                              collection_class=set,
                                              cascade="all, delete-orphan"),
                                "commentaries":
                                relationship(project_commentary_mapper,
                                             collection_class=list,
                                             cascade="all, delete-orphan"),
                                "history":
                                relationship(project_event_mapper,
                                             collection_class=list)
                            })
