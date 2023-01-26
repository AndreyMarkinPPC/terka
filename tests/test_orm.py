import pytest
from datetime import datetime

from src.domain.task import Task, TaskStatus
from src.domain.user import User
from src.domain.event_history import Event
from src.domain.commentary import Commentary


def test_user_can_load(session):
    session.execute("INSERT INTO users (name) VALUES "
                    '("user_1")')
    expected = [User("user_1")]
    print(session.query(User).all()[0].name)
    assert session.query(User).all() == expected


def test_can_save_tasks(session):
    new_task = Task("task_1")
    session.add(new_task)
    session.commit()
    rows = list(session.execute('SELECT id, name, status FROM "tasks"'))
    assert rows == [(1, "task_1", "BACKLOG")]


def test_can_save_tasks_with_project(session):
    new_task = Task(name="task_1", project="new project")
    session.add(new_task)
    session.commit()
    rows = list(session.execute('SELECT id, name, project, status FROM "tasks"'))
    assert rows == [(1, "task_1", "new project", "BACKLOG")]


def test_can_save_users(session):
    new_user = User("user_2")
    session.add(new_user)
    session.commit()

    rows = list(session.execute('SELECT id, name FROM "users"'))
    assert rows == [(1, "user_2")]


def test_can_save_one_event(session):
    date = datetime.now()
    event = Event("tasks", 1, date, "status", "BACKLOG", "TODO")
    session.add(event)
    session.commit()
    rows = list(
        session.execute(
            'SELECT id, source, element_id, date, type, old_value, new_value FROM "events"'
        ))
    assert rows == [(1, "tasks", 1, date.strftime("%Y-%m-%d %H:%M:%S.%f"),
                     "status", "BACKLOG", "TODO")]


def test_can_save_multiple_events(session):
    date1 = datetime.now()
    event1 = Event("tasks", 1, date1, "status", "BACKLOG", "TODO")
    date2 = datetime.now()
    event2 = Event("tasks", 1, date2, "status", "TODO", "DONE")
    session.add(event1)
    session.add(event2)
    session.commit()
    rows = list(session.execute('SELECT id FROM "events"'))
    assert rows == [(1, ), (2, )]


def test_can_save_one_commentary(session):
    date = datetime.now()
    commentary = Commentary(1, "Test commentary", date)
    session.add(commentary)
    session.commit()
    rows = list(
        session.execute('SELECT task_id, date, text FROM "commentaries"'))
    assert rows == [(1, date.strftime("%Y-%m-%d %H:%M:%S.%f"),
                     "Test commentary")]


def test_can_save_multiple_commentaries(session):
    date1 = datetime.now()
    commentary1 = Commentary(1, "Test commentary", date1 )
    date2 = datetime.now()
    commentary2 = Commentary(1, "Test commentary", date2)
    session.add(commentary1)
    session.add(commentary2)
    session.commit()
    rows = list(session.execute('SELECT id FROM "commentaries"'))
    assert rows == [(1, ), (2, )]
