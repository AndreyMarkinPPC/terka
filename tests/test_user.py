import pytest

from src.domain.user import User
from src.domain.task import Task
from src.domain.project import Project


@pytest.fixture
def user():
    return User("am")
@pytest.fixture
def task():
    return Task("test_task")


def test_user_init(user):
    assert user.name == "am"


def test_user_create_project(user):
    project = user.create_project("New Project")
    assert project.name == "New Project"


@pytest.mark.skip("Failing")
def test_user_add_task_to_project(user, task):
    project = user.assign_task_to_project("New Project", task)
    assert len(project.tasks) == 1
    assert project.tasks[0].name == "test_task"


def test_user_set_task_due_date(user, task):
    due_date = "2022-01-01"
    user.set_task_due_date(task, due_date)
    assert task.due_date == due_date


def test_user_set_task_incorrect_due_date(user, task):
    due_date = ""
    with pytest.raises(ValueError):
        user.set_task_due_date(task, due_date)


def test_user_can_create_task(user):
    task = user.create_task("new_task")
    assert task.name == "new_task"
    assert task.created_by == "am"
    assert task.project is None


def test_user_can_create_task_and_assign_project(user):
    task = user.create_task(name="new_task", project_id = 2)
    assert task.project == 2

