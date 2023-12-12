import pytest
from terka import bootstrap
from terka.domain import _commands, entities, events


class TestTask:

    def test_create_simple_task(self, bus):
        cmd = _commands.CreateTask(name="test")
        bus.handle(cmd)
        new_task = bus.handler.uow.tasks.get_by_id(entities.task.Task, 1)
        assert new_task.name == "test"

    def test_updating_task_sets_modification_date(self, bus):
        cmd = _commands.CreateTask(name="test")
        task_id = bus.handle(cmd)
        new_task = bus.handler.uow.tasks.get_by_id(entities.task.Task, task_id)
        update_cmd = _commands.UpdateTask(new_task.id, status="TODO")
        bus.handle(update_cmd)
        new_task = bus.handler.uow.tasks.get_by_id(entities.task.Task, task_id)
        assert new_task.modification_date > new_task.creation_date
        assert new_task.status == entities.task.TaskStatus.TODO

    def test_completing_task_creates_status_task_event(self, bus):
        cmd = _commands.CreateTask(name="test")
        task_id = bus.handle(cmd)
        complete_cmd = _commands.CompleteTask(task_id)
        bus.handle(complete_cmd)
        new_task = bus.handler.uow.tasks.get_by_id(entities.task.Task, task_id)
        task_event = bus.handler.uow.tasks.get_by_conditions(
            entities.event_history.TaskEvent, {
                "task": task_id,
                "new_value": "DONE",
                "old_value": "BACKLOG"
            })
        assert task_event
        assert new_task.status == entities.task.TaskStatus.DONE

    def test_deleting_task_creates_status_task_event(self, bus):
        cmd = _commands.CreateTask(name="test")
        task_id = bus.handle(cmd)
        complete_cmd = _commands.DeleteTask(task_id)
        bus.handle(complete_cmd)
        new_task = bus.handler.uow.tasks.get_by_id(entities.task.Task, task_id)
        task_event = bus.handler.uow.tasks.get_by_conditions(
            entities.event_history.TaskEvent, {
                "task": task_id,
                "new_value": "DELETED",
                "old_value": "BACKLOG"
            })
        assert task_event
        assert new_task.status == entities.task.TaskStatus.DELETED

    def test_creating_task_with_tag_creates_tag(self, bus):
        cmd = _commands.CreateTask(name="test")
        task_id = bus.handle(cmd, context={"tags": "new_tag"})
        new_task_tag = bus.handler.uow.tasks.get_by_conditions(
            entities.tag.TaskTag, {"task": task_id})
        new_base_tag = bus.handler.uow.tasks.get_by_conditions(
            entities.tag.BaseTag, {"text": "new_tag"})
        assert new_task_tag
        assert new_base_tag

    def test_creating_task_with_collaborator_creates_user(self, bus):
        cmd = _commands.CreateTask(name="test")
        task_id = bus.handle(cmd,
                             context={"collaborators": "new_collaborator"})
        [new_task_collaborator] = bus.handler.uow.tasks.get_by_conditions(
            entities.collaborator.TaskCollaborator, {"task": task_id})
        new_user = bus.handler.uow.tasks.get_by_id(entities.user.User,
                                                   new_task_collaborator.id)
        assert new_task_collaborator
        assert new_user

    def test_creating_task_with_comment_creates_comment(self, bus):
        cmd = _commands.CreateTask(name="test")
        task_id = bus.handle(cmd, context={"comment": "new_commentary"})
        new_task_comment = bus.handler.uow.tasks.get_by_conditions(
            entities.commentary.TaskCommentary, {"task": task_id})
        assert new_task_comment
