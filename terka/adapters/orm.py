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
from sqlalchemy.orm import mapper, registry, relationship, validates, declarative_base, backref

from terka.domain.entities import (collaborator, commentary, epic,
                                   event_history, note, project, sprint, story,
                                   tag, task, time_tracker, user, workspace)

from terka.domain.external_connectors import asana

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
              Column("status", Enum(task.TaskStatus)),
              Column("priority", Enum(task.TaskPriority)),
              Column("sync", Boolean))

projects = Table(
    "projects",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(255)),
    Column("description", String(255)),
    Column("status", Enum(project.ProjectStatus)),
    Column("workspace", ForeignKey("workspaces.id"), nullable=True),
)

workspaces = Table("workspaces", metadata,
                   Column("id", Integer, primary_key=True, autoincrement=True),
                   Column("name", String(255)),
                   Column("description", String(255)))
task_events = Table(
    "task_events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("task", ForeignKey("tasks.id"), nullable=True),
    Column("date", DateTime, nullable=False),
    Column("type", Enum(event_history.EventType)),
    Column("old_value", String(225)),
    Column("new_value", String(225)),
)

project_events = Table(
    "project_events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project", ForeignKey("projects.id"), nullable=True),
    Column("date", DateTime, nullable=False),
    Column("type", Enum(event_history.EventType)),
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

task_notes = Table(
    "task_notes",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("task", ForeignKey("tasks.id"), nullable=True),
    Column("created_by", ForeignKey("users.id"), nullable=True),
    Column("date", DateTime, nullable=False),
    Column("name", String(225)),
    Column("text", String(1000)),
)

project_notes = Table(
    "project_notes",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project", ForeignKey("projects.id"), nullable=True),
    Column("created_by", ForeignKey("users.id"), nullable=True),
    Column("date", DateTime, nullable=False),
    Column("name", String(225)),
    Column("text", String(1000)),
)

epic_notes = Table(
    "epic_notes",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("epic", ForeignKey("epics.id"), nullable=True),
    Column("created_by", ForeignKey("users.id"), nullable=True),
    Column("date", DateTime, nullable=False),
    Column("name", String(225)),
    Column("text", String(1000)),
)

story_notes = Table(
    "story_notes",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("story", ForeignKey("stories.id"), nullable=True),
    Column("created_by", ForeignKey("users.id"), nullable=True),
    Column("date", DateTime, nullable=False),
    Column("name", String(225)),
    Column("text", String(1000)),
)

sprint_notes = Table(
    "sprint_notes",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("sprint", ForeignKey("sprints.id"), nullable=True),
    Column("created_by", ForeignKey("users.id"), nullable=True),
    Column("date", DateTime, nullable=False),
    Column("name", String(225)),
    Column("text", String(1000)),
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
                Column("status", Enum(sprint.SprintStatus)),
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
              Column("status", Enum(epic.EpicStatus)),
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
                Column("status", Enum(story.StoryStatus)),
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
    "external_connectors.asana.tasks",
    metadata,
    # Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project", ForeignKey("projects.id")),
    Column("id", ForeignKey("tasks.id"), nullable=False, primary_key=True),
    Column("asana_task_id", String(20)),
    Column("sync_date", DateTime, nullable=True))

asana_projects = Table(
    "external_connectors.asana.projects", metadata,
    Column("id", ForeignKey("projects.id"), nullable=False, primary_key=True),
    Column("asana_project_id", String(20)),
    Column("sync_date", DateTime, nullable=True))

asana_users = Table(
    "external_connectors.asana.users", metadata,
    Column("id", ForeignKey("users.id"), nullable=False, primary_key=True),
    Column("asana_user_id", String(20)))


def start_mappers(engine=None):
    asana_task_mapper = mapper(asana.AsanaTask, asana_tasks)
    asana_project_mapper = mapper(asana.AsanaProject, asana_projects)
    asana_user_mapper = mapper(asana.AsanaUser, asana_users)

    task_commentary_mapper = mapper(commentary.TaskCommentary,
                                    task_commentaries)
    project_commentary_mapper = mapper(commentary.ProjectCommentary,
                                       project_commentaries)
    epic_commentary_mapper = mapper(commentary.EpicCommentary,
                                    epic_commentaries)
    story_commentary_mapper = mapper(commentary.StoryCommentary,
                                     story_commentaries)
    sprint_commentary_mapper = mapper(commentary.SprintCommentary,
                                      sprint_commentaries)

    task_note_mapper = mapper(note.TaskNote, task_notes)
    project_note_mapper = mapper(note.ProjectNote, project_notes)
    epic_note_mapper = mapper(note.EpicNote, epic_notes)
    story_note_mapper = mapper(note.StoryNote, story_notes)
    sprint_note_mapper = mapper(note.SprintNote, sprint_notes)

    task_event_mapper = mapper(event_history.TaskEvent, task_events)
    project_event_mapper = mapper(event_history.ProjectEvent, project_events)
    user_mapper = mapper(
        user.User,
        users)

    tag_mapper = mapper(tag.BaseTag, tags)
    task_tag_mapper = mapper(tag.TaskTag,
                             task_tags,
                             properties={
                                 "base_tag":
                                 relationship(tag_mapper,
                                              collection_class=list)
                             })
    project_tag_mapper = mapper(tag.ProjectTag,
                                project_tags,
                                properties={
                                    "base_tag":
                                    relationship(tag_mapper,
                                                 collection_class=list)
                                })
    task_collaborator_mapper = mapper(
        collaborator.TaskCollaborator,
        task_collaborators,
        properties={"users": relationship(user_mapper, collection_class=list)})
    project_collaborator_mapper = mapper(
        collaborator.ProjectCollaborator,
        project_collaborators,
        properties={"users": relationship(user_mapper, collection_class=list)})
    time_tracker_mapper = mapper(time_tracker.TimeTrackerEntry,
                                 time_tracker_entries)
    task_mapper = mapper(task.Task,
                         tasks,
                         properties={
                             "assigned_to":
                             relationship(user.User,
                                          foreign_keys=[tasks.c.assignee]),
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
                             "notes":
                             relationship(task_note_mapper,
                                          collection_class=set,
                                          cascade="all, delete-orphan"),
                             "history":
                             relationship(task_event_mapper,
                                          collection_class=list,
                                          cascade="all, delete-orphan"),
                             "time_spent":
                             relationship(time_tracker_mapper,
                                          collection_class=list,
                                          cascade="all, delete-orphan"),
                             "project_":
                             relationship(
                                 project.Project,
                                 back_populates="tasks",
                             )
                         })
    epic_tasks_mapper = mapper(epic.EpicTask,
                               epic_tasks,
                               properties={
                                   "tasks":
                                   relationship(task_mapper,
                                                backref=backref("epics"),
                                                collection_class=list)
                               })
    epic_mapper = mapper(epic.Epic,
                         epics,
                         properties={
                             "commentaries":
                             relationship(epic_commentary_mapper,
                                          collection_class=list,
                                          cascade="all, delete-orphan"),
                             "notes":
                             relationship(epic_note_mapper,
                                          collection_class=set,
                                          cascade="all, delete-orphan"),
                             "tasks":
                             relationship(epic_tasks_mapper,
                                          backref=backref("epics"),
                                          collection_class=list)
                         })
    story_tasks_mapper = mapper(story.StoryTask,
                                story_tasks,
                                properties={
                                    "tasks":
                                    relationship(task_mapper,
                                                 backref=backref("stories"),
                                                 collection_class=list)
                                })
    story_mapper = mapper(story.Story,
                          stories,
                          properties={
                              "commentaries":
                              relationship(story_commentary_mapper,
                                           collection_class=list,
                                           cascade="all, delete-orphan"),
                              "notes":
                              relationship(story_note_mapper,
                                           collection_class=set,
                                           cascade="all, delete-orphan"),
                              "tasks":
                              relationship(story_tasks_mapper,
                                           collection_class=list)
                          })
    project_mapper = mapper(project.Project,
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
                                "notes":
                                relationship(project_note_mapper,
                                             collection_class=set,
                                             cascade="all, delete-orphan"),
                                "history":
                                relationship(project_event_mapper,
                                             collection_class=list),
                                "last_synced":
                                relationship(asana_project_mapper,
                                             collection_class=list,
                                             cascade="all, delete-orphan"),
                                "workspace_":
                                relationship(workspace.Workspace,
                                             back_populates="projects")
                            })
    sprint_tasks_mapper = mapper(sprint.SprintTask,
                                 sprint_tasks,
                                 properties={
                                     "tasks":
                                     relationship(task_mapper,
                                                  backref=backref("sprints"),
                                                  collection_class=list)
                                 })
    sprint_mapper = mapper(sprint.Sprint,
                           sprints,
                           properties={
                               "commentaries":
                               relationship(sprint_commentary_mapper,
                                            collection_class=list,
                                            cascade="all, delete-orphan"),
                               "notes":
                               relationship(sprint_note_mapper,
                                            collection_class=set,
                                            cascade="all, delete-orphan"),
                               "tasks":
                               relationship(sprint_tasks_mapper,
                                            collection_class=list),
                           })
    workspace_mapper = mapper(workspace.Workspace,
                              workspaces,
                              properties={
                                  "projects":
                                  relationship(project_mapper,
                                               collection_class=list),
                              })
    if engine:
        metadata.create_all(engine)
