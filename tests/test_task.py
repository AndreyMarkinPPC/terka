import pytest

from datetime import datetime
from src.domain.task import Task, TaskStatus


@pytest.fixture
def task():
    return Task(name="name")


def test_create_task_with_name_and_creation_date():
    now = datetime.now()
    task = Task(name = "name", creation_date=now)
    assert task.name == "name"
    assert task.description is None
    assert task.creation_date == now
    assert task.task_id == 1
    assert task.project == None
    assert task.assignee == None



def test_create_task_with_description():
    task2 = Task(name="name", description="description")
    assert task2.description == "description"
    assert task2.task_id == 2


def test_fails_empty_name():
    with pytest.raises(ValueError):
        task = Task("")


def test_fails_incorrect_date():
    with pytest.raises(ValueError):
        task = Task("test", creation_date="2020-01-01")


def test_task_get_backlog_enum(task):
    assert task.status == TaskStatus.BACKLOG
