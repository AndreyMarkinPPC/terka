from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import (
    Table,
    MetaData,
    Column,
    Integer,
    String,
    Date,
    DateTime,
    Boolean,
    Enum,
    ForeignKey,
    event,
)
from sqlalchemy.orm import mapper, registry, relationship, validates, declarative_base

from terka.domain.task import Task, TaskStatus, TaskPriority
from terka.domain.user import User
from terka.domain.project import Project, ProjectStatus
from terka.domain.event_history import TaskEvent, ProjectEvent, EventType
from terka.domain.commentary import TaskCommentary, ProjectCommentary, EpicCommentary, StoryCommentary, SprintCommentary
from terka.domain.tag import BaseTag, TaskTag, ProjectTag
from terka.domain.collaborators import TaskCollaborator, ProjectCollaborator
from terka.domain.sprint import Sprint, SprintStatus, SprintTask
from terka.domain.time_tracker import TimeTrackerEntry
from terka.domain.epic import Epic, EpicTask, EpicStatus
from terka.domain.story import Story, StoryTask, StoryStatus

from terka.domain.external_connectors.asana import AsanaTask, AsanaProject

Base = declarative_base()
metadata = MetaData()

tasks = Table("tasks", metadata,
              Column("id", Integer, primary_key=True, autoincrement=True),
              Column("name", String(255)),
              Column("creation_date", DateTime, nullable=True),
              Column("modification_date", DateTime, nullable=True),
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

epic_commentaries = Table(
    "epic_commentaries",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("epic", ForeignKey("epics.id"), nullable=True),
    Column("date", DateTime, nullable=False),
    Column("text", String(225)),
)

story_commentaries = Table(
    "story_commentaries",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("story", ForeignKey("stories.id"), nullable=True),
    Column("date", DateTime, nullable=False),
    Column("text", String(225)),
)

sprint_commentaries = Table(
    "sprint_commentaries",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("sprint", ForeignKey("sprints.id"), nullable=True),
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

project_tags = Table(
    "project_tags", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project", ForeignKey("projects.id"), nullable=True),
    Column("tag", ForeignKey("tags.id"), nullable=True))

task_collaborators = Table(
    "task_collaborators", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("task", ForeignKey("tasks.id"), nullable=True),
    Column("collaborator", ForeignKey("users.id"), nullable=True))

project_collaborators = Table(
    "project_collaborators", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project", ForeignKey("projects.id"), nullable=True),
    Column("collaborator", ForeignKey("users.id"), nullable=True))

sprints = Table("sprints", metadata,
                Column("id", Integer, primary_key=True, autoincrement=True),
                Column("start_date", Date, nullable=False),
                Column("end_date", Date, nullable=False),
                Column("status", Enum(SprintStatus)),
                Column("goal", String(225), nullable=True))

sprint_tasks = Table(
    "sprint_tasks",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("task", ForeignKey("tasks.id"), nullable=False),
    Column("sprint", ForeignKey("sprints.id"), nullable=False),
    Column("story_points", Integer, nullable=False),
    Column("is_active_link", Boolean, nullable=False),
)

time_tracker_entries = Table(
    "time_tracker_entries",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("creation_date", DateTime, nullable=True),
    Column("task", ForeignKey("tasks.id"), nullable=False),
    Column("time_spent_minutes", Integer, nullable=False),
)

epics = Table("epics", metadata,
              Column("id", Integer, primary_key=True, autoincrement=True),
              Column("name", String(255)),
              Column("creation_date", DateTime, nullable=True),
              Column("description", String(1000), nullable=True),
              Column("project", ForeignKey("projects.id"), nullable=True),
              Column("assignee", ForeignKey("users.id"), nullable=True),
              Column("status", Enum(EpicStatus)),
              Column("created_by", ForeignKey("users.id"), nullable=True))

epic_tasks = Table("epic_tasks", metadata,
                   Column("id", Integer, primary_key=True, autoincrement=True),
                   Column("task", ForeignKey("tasks.id"), nullable=False),
                   Column("epic", ForeignKey("epics.id"), nullable=False))

stories = Table("stories", metadata,
                Column("id", Integer, primary_key=True, autoincrement=True),
                Column("name", String(255)),
                Column("creation_date", DateTime, nullable=True),
                Column("description", String(1000), nullable=True),
                Column("project", ForeignKey("projects.id"), nullable=True),
                Column("assignee", ForeignKey("users.id"), nullable=True),
                Column("status", Enum(StoryStatus)),
                Column("created_by", ForeignKey("users.id"), nullable=True))

story_tasks = Table(
    "story_tasks", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("task", ForeignKey("tasks.id"), nullable=False),
    Column("story", ForeignKey("stories.id"), nullable=False))
# class SprintTasks(Base):
#     __tablename__ = "sprint_tasks"
#     id = Integer(primary_key=True, autoincrement=True)
#     task_id = Integer(nullable=False)
#     sprint_id = Integer(nullable=False)
#     ta

asana_tasks = Table(
    "external_connectors.asana.tasks", metadata,
    # Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project", ForeignKey("projects.id")),
    Column("id", ForeignKey("tasks.id"), nullable=False, primary_key=True),
    Column("asana_task_id", String(20)),
    Column("sync_date", DateTime, nullable=True))

asana_projects = Table(
    "external_connectors.asana.projects", metadata,
    # Column("id", Integer, primary_key=True, autoincrement=True),
    Column("id", ForeignKey("projects.id"), nullable=False, primary_key=True),
    Column("asana_project_id", String(20)),
    Column("sync_date", DateTime, nullable=True))

def start_mappers():
    asana_task_mapper = mapper(AsanaTask, asana_tasks)
    asana_project_mapper = mapper(AsanaProject, asana_projects)
    task_commentary_mapper = mapper(TaskCommentary, task_commentaries)
    project_commentary_mapper = mapper(ProjectCommentary, project_commentaries)
    epic_commentary_mapper = mapper(EpicCommentary, epic_commentaries)
    story_commentary_mapper = mapper(StoryCommentary, story_commentaries)
    sprint_commentary_mapper = mapper(SprintCommentary, sprint_commentaries)
    task_event_mapper = mapper(TaskEvent, task_events)
    project_event_mapper = mapper(ProjectEvent, project_events)
    user_mapper = mapper(User, users)
    tag_mapper = mapper(BaseTag, tags)
    task_tag_mapper = mapper(TaskTag,
                             task_tags,
                             properties={
                                 "base_tag":
                                 relationship(tag_mapper,
                                              collection_class=list)
                             })
    project_tag_mapper = mapper(ProjectTag,
                                project_tags,
                                properties={
                                    "base_tag":
                                    relationship(tag_mapper,
                                                 collection_class=list)
                                })
    task_collaborator_mapper = mapper(
        TaskCollaborator,
        task_collaborators,
        properties={"users": relationship(user_mapper, collection_class=list)})
    project_collaborator_mapper = mapper(
        ProjectCollaborator,
        project_collaborators,
        properties={"users": relationship(user_mapper, collection_class=list)})
    time_tracker_mapper = mapper(TimeTrackerEntry, time_tracker_entries)
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
                             "time_spent":
                             relationship(time_tracker_mapper,
                                          collection_class=list,
                                          cascade="all, delete-orphan"),
                         })
    epic_tasks_mapper = mapper(
        EpicTask,
        epic_tasks,
        properties={"tasks": relationship(task_mapper, collection_class=list)})
    epic_mapper = mapper(Epic,
                         epics,
                         properties={
                             "commentaries":
                             relationship(epic_commentary_mapper,
                                          collection_class=list,
                                          cascade="all, delete-orphan"),
                             "tasks":
                             relationship(epic_tasks_mapper,
                                          collection_class=list)
                         })
    story_tasks_mapper = mapper(
        StoryTask,
        story_tasks,
        properties={"tasks": relationship(task_mapper, collection_class=list)})
    story_mapper = mapper(Story,
                          stories,
                          properties={
                             "commentaries":
                             relationship(story_commentary_mapper,
                                          collection_class=list,
                                          cascade="all, delete-orphan"),
                              "tasks":
                              relationship(story_tasks_mapper,
                                           collection_class=list)
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
                                "epics":
                                relationship(epic_mapper,
                                             collection_class=set),
                                "stories":
                                relationship(story_mapper,
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
    sprint_tasks_mapper = mapper(
        SprintTask,
        sprint_tasks,
        properties={"tasks": relationship(task_mapper, collection_class=list)})
    sprint_mapper = mapper(Sprint,
                           sprints,
                           properties={
                               "commentaries":
                               relationship(sprint_commentary_mapper,
                                            collection_class=list,
                                        cascade="all, delete-orphan"),
                               "tasks":
                               relationship(sprint_tasks_mapper,
                                            collection_class=list)
                           })
