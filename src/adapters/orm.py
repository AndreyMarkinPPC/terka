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
from src.domain.event_history import Event
from src.domain.commentary import Commentary


metadata = MetaData()
Base = declarative_base()

class Tasks(Base):
    __tablename__ = "tasks"
    id = Column("id", Integer, primary_key=True, autoincrement=True)
    name = Column(String(255))
    creation_date = Column(DateTime, nullable=True)
    description = Column(String(1000), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    project_obj = relationship("Projects")
    assignee = Column(Integer, ForeignKey("users.id"), nullable=True)
    assignee_ = relationship("Users")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by = relationship("Users")
    due_date = Column(Date, nullable=True)
    status = Column(Enum(TaskStatus))
    priority = Column(Enum(TaskPriority))
    # comment = Column(String(1000), ForeignKey("commentaries.text"))


class Projects(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255))
    description = Column(String(255))
    status = Column(Enum(ProjectStatus))


class Users(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50))

class Commentaries(Base):
    __tablename__ = "commentaries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50))
    element_id = Column(Integer)
    date =Column(DateTime, nullable=False)
    text = Column(String(225))
    # task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    # task = relationship("Tasks", primaryjoin="Tasks.id=element_id", secondaryjoin="tasks=source")

tasks = Table(
    "tasks",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(255)),
    Column("creation_date", DateTime, nullable=True),
    Column("description", String(1000), nullable=True),
    Column("project", ForeignKey("projects.id"), nullable=True),
    Column("assignee", ForeignKey("users.id"), nullable=True),
    Column("created_by", ForeignKey("users.id"), nullable=True),
    Column("due_date", Date, nullable=True),
    Column("status", Enum(TaskStatus)),
    Column("priority", Enum(TaskPriority))
)

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(50))
)

projects = Table(
    "projects",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(255)),
    Column("description", String(255)),
    Column("status", Enum(ProjectStatus))
)


events = Table(
    "events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("source", String(10)),
    Column("element_id", Integer),
    Column("date", DateTime, nullable=False),
    Column("type", String(10)),
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


def start_mappers():
    commentary_mapper = mapper(Commentary, commentaries)
    task_mapper = mapper(Task, tasks,
        properties={
            "commentaries": relationship(
                commentary_mapper,
                collection_class=set)
        }
                         )
    user_mapper = mapper(User, users)
    event_mapper = mapper(Event, events)
    project_mapper = mapper(
        Project, projects,
        properties={
            "tasks": relationship(
                task_mapper,
                collection_class=set)
        }
    )
