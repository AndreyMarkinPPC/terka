import pytest
from datetime import datetime, timedelta
import terka
from terka import bootstrap
from terka.domain import commands, entities, events


class TestTask:

    def test_create_simple_task(self, bus):
        cmd = commands.CreateTask(name="test")
        bus.handle(cmd)
        new_task = bus.uow.tasks.get_by_id(entities.task.Task, 1)
        expected_task = entities.task.Task(
            name="test",
            description=None,
            project=None,
            assignee=None,
            due_date=None,
            status=entities.task.TaskStatus.BACKLOG,
            priority=entities.task.TaskPriority.NORMAL)
        assert new_task == expected_task

    def test_updating_task_sets_modification_date(self, bus):
        cmd = commands.CreateTask(name="test")
        task_id = bus.handle(cmd)
        new_task = bus.uow.tasks.get_by_id(entities.task.Task, task_id)
        update_cmd = commands.UpdateTask(new_task.id, status="TODO")
        bus.handle(update_cmd)
        new_task = bus.uow.tasks.get_by_id(entities.task.Task, task_id)
        assert new_task.modification_date > new_task.creation_date
        assert new_task.status == entities.task.TaskStatus.TODO

    def test_completing_task_creates_status_task_event(self, bus):
        cmd = commands.CreateTask(name="test")
        task_id = bus.handle(cmd)
        complete_cmd = commands.CompleteTask(task_id)
        bus.handle(complete_cmd)
        new_task = bus.uow.tasks.get_by_id(entities.task.Task, task_id)
        task_event = bus.uow.tasks.get_by_conditions(
            entities.event_history.TaskEvent, {
                "task": task_id,
                "new_value": "DONE",
                "old_value": "BACKLOG"
            })
        assert task_event
        assert new_task.status == entities.task.TaskStatus.DONE

    def test_deleting_task_creates_status_task_event(self, bus):
        cmd = commands.CreateTask(name="test")
        task_id = bus.handle(cmd)
        complete_cmd = commands.DeleteTask(task_id)
        bus.handle(complete_cmd)
        new_task = bus.uow.tasks.get_by_id(entities.task.Task, task_id)
        task_event = bus.uow.tasks.get_by_conditions(
            entities.event_history.TaskEvent, {
                "task": task_id,
                "new_value": "DELETED",
                "old_value": "BACKLOG"
            })
        assert task_event
        assert new_task.status == entities.task.TaskStatus.DELETED

    def test_creating_task_with_tag_creates_tag(self, bus):
        cmd = commands.CreateTask(name="test")
        task_id = bus.handle(cmd, context={"tags": "new_tag"})
        new_task_tag = bus.uow.tasks.get_by_conditions(
            entities.tag.TaskTag, {"task": task_id})
        new_base_tag = bus.uow.tasks.get_by_conditions(
            entities.tag.BaseTag, {"text": "new_tag"})
        assert new_task_tag
        assert new_base_tag

    def test_creating_task_with_collaborator_creates_user(self, bus):
        cmd = commands.CreateTask(name="test")
        task_id = bus.handle(cmd,
                             context={"collaborators": "new_collaborator"})
        [new_task_collaborator] = bus.uow.tasks.get_by_conditions(
            entities.collaborator.TaskCollaborator, {"task": task_id})
        new_user = bus.uow.tasks.get_by_id(entities.user.User,
                                                   new_task_collaborator.id)
        assert new_task_collaborator
        assert new_user

    def test_creating_task_with_comment_creates_comment(self, bus):
        cmd = commands.CreateTask(name="test")
        task_id = bus.handle(cmd, context={"comment": "new_commentary"})
        new_task_comment = bus.uow.tasks.get_by_conditions(
            entities.commentary.TaskCommentary, {"task": task_id})
        assert new_task_comment

    def test_commenting_task_with_empty_comment_is_ignored(self, bus):
        cmd = commands.CreateTask(name="test")
        task_id = bus.handle(cmd, context={"comment": " "})
        new_task_comment = bus.uow.tasks.get_by_conditions(
            entities.commentary.TaskCommentary, {"task": task_id})
        assert not new_task_comment

    def test_tagging_task_with_empty_tag_is_ignored(self, bus):
        cmd = commands.CreateTask(name="test")
        task_id = bus.handle(cmd, context={"tag": " "})
        new_task_tag = bus.uow.tasks.get_by_conditions(
            entities.tag.TaskTag, {"task": task_id})
        assert not new_task_tag

    @pytest.mark.parametrize("entity", ["epic", "sprint", "story"])
    def test_tagging_task_with_service_tag_is_ignored(self, bus, entity):
        cmd = commands.CreateTask(name="test")
        task_id = bus.handle(cmd, context={"tag": f"{entity}: 1"})
        new_task_tag = bus.uow.tasks.get_by_conditions(
            entities.tag.TaskTag, {"task": task_id})
        assert not new_task_tag


class TestSprint:

    @pytest.fixture(scope="class")
    def tasks(self, bus):
        create_task_1 = commands.CreateTask(name="task_1")
        create_task_2 = commands.CreateTask(name="task_2")
        task_1 = bus.handle(create_task_1)
        task_2 = bus.handle(create_task_2)
        return task_1, task_2

    @pytest.fixture
    def new_sprint(self, bus):
        today = datetime.now()
        next_monday = (today + timedelta(days=(7 - today.weekday())))
        next_sunday = (today + timedelta(days=(13 - today.weekday())))
        cmd = commands.CreateSprint(start_date=next_monday,
                                     end_date=next_sunday)
        sprint_id = bus.handle(cmd)
        return sprint_id

    @pytest.fixture
    def sprint_with_tasks(self, bus, new_sprint, tasks):
        task_1, task_2 = tasks
        add_task_1 = commands.AddTask(id=task_1, sprint=new_sprint)
        add_task_2 = commands.AddTask(id=task_2, sprint=new_sprint)
        bus.handle(add_task_1)
        bus.handle(add_task_2)

    def test_new_sprint_created(self, new_sprint):
        assert new_sprint

    def test_referencing_non_existing_sprints_raises_entity_not_found_exception(
            self, bus):
        with pytest.raises(terka.service_layer.exceptions.EntityNotFound):
            bus.handle(commands.StartSprint(9999))

    def test_cannot_create_sprint_with_end_date_in_past(self, bus):
        today = datetime.now()
        start_date = (today - timedelta(days=(7 - today.weekday())))
        end_date = (today - timedelta(days=(1 - today.weekday())))
        cmd = commands.CreateSprint(start_date=start_date, end_date=end_date)
        # TODO: check for a specific message
        with pytest.raises(ValueError):
            bus.handle(cmd)

    def test_adding_task_to_sprint(self, bus, new_sprint, sprint_with_tasks):
        sprint_tasks = bus.uow.tasks.get_by_conditions(
            entities.sprint.SprintTask, {"sprint": new_sprint})
        assert len(sprint_tasks) == 2
        for task in sprint_tasks:
            assert task.story_points == 0

    def test_starting_sprint_changes_status_due_date(self, bus, new_sprint,
                                                     sprint_with_tasks):
        cmd = commands.StartSprint(new_sprint)
        bus.handle(cmd)
        sprint = bus.uow.tasks.get_by_id(entities.sprint.Sprint,
                                                 new_sprint)
        assert sprint.status == entities.sprint.SprintStatus.ACTIVE
        sprint_tasks = bus.uow.tasks.get_by_conditions(
            entities.sprint.SprintTask, {"sprint": new_sprint})
        for sprint_task in sprint_tasks:
            task = bus.uow.tasks.get_by_id(entities.task.Task,
                                                   sprint_task.task)
            assert task.status == entities.task.TaskStatus.TODO
            assert task.due_date == sprint.end_date

    def test_cannot_start_active_sprint(self, bus, new_sprint):
        cmd = commands.StartSprint(new_sprint)
        bus.handle(cmd)
        cmd = commands.StartSprint(new_sprint)
        with pytest.raises(terka.service_layer.exceptions.TerkaSprintActive):
            bus.handle(cmd)

    def test_cannot_start_completed_sprint(self, bus, new_sprint):
        cmd = commands.StartSprint(new_sprint)
        bus.handle(cmd)
        cmd = commands.CompleteSprint(new_sprint)
        bus.handle(cmd)
        cmd = commands.StartSprint(new_sprint)
        with pytest.raises(
                terka.service_layer.exceptions.TerkaSprintCompleted):
            bus.handle(cmd)

    def test_completing_sprint_changes_status_due_date(self, bus, new_sprint,
                                                       sprint_with_tasks):
        cmd = commands.CompleteSprint(new_sprint)
        bus.handle(cmd)
        sprint = bus.uow.tasks.get_by_id(entities.sprint.Sprint,
                                                 new_sprint)
        assert sprint.status == entities.sprint.SprintStatus.COMPLETED
        sprint_tasks = bus.uow.tasks.get_by_conditions(
            entities.sprint.SprintTask, {"sprint": new_sprint})
        for sprint_task in sprint_tasks:
            task = bus.uow.tasks.get_by_id(entities.task.Task,
                                                   sprint_task.task)
            assert task.status == entities.task.TaskStatus.BACKLOG
            assert not task.due_date

    def test_completing_sprint_with_in_progress_review_tasks_doesnt_change_their_status(
            self, bus, new_sprint, sprint_with_tasks):
        cmd = commands.StartSprint(new_sprint)
        bus.handle(cmd)
        sprint = bus.uow.tasks.get_by_id(entities.sprint.Sprint,
                                                 new_sprint)
        update_task = commands.UpdateTask(id=1, status="REVIEW")
        bus.handle(update_task)
        sprint_tasks = bus.uow.tasks.get_by_conditions(
            entities.sprint.SprintTask, {"sprint": new_sprint})
        for sprint_task in sprint_tasks:
            task = bus.uow.tasks.get_by_id(entities.task.Task,
                                                   sprint_task.task)
            if task.id == 1:
                assert task.status == entities.task.TaskStatus.REVIEW

    def test_cannot_add_ask_to_completed_sprint(self, bus, new_sprint,
                                                sprint_with_tasks):
        cmd = commands.CompleteSprint(new_sprint)
        bus.handle(cmd)
        create_task_3 = commands.CreateTask(name="task_3")
        task_3 = bus.handle(create_task_3)
        cmd = commands.AddTask(id=task_3, sprint=new_sprint)
        with pytest.raises(
                terka.service_layer.exceptions.TerkaSprintCompleted):
            bus.handle(cmd)

    def test_deleting_task_from_sprint(self, bus, new_sprint,
                                       sprint_with_tasks):
        cmd = commands.StartSprint(new_sprint)
        bus.handle(cmd)
        sprint = bus.uow.tasks.get_by_id(entities.sprint.Sprint,
                                                 new_sprint)
        delete_task = commands.DeleteTask(id=sprint.tasks[0].task,
                                           sprint=new_sprint)
        bus.handle(delete_task)
        sprint = bus.uow.tasks.get_by_id(entities.sprint.Sprint,
                                                 new_sprint)
        assert len(sprint.tasks) == 1

    def test_adding_story_to_sprint_adds_non_completed_tasks(
            self, bus, new_sprint, tasks):
        task_1, task_2 = tasks
        create_story = commands.CreateStory(name="story_1")
        story_id = bus.handle(create_story)
        add_task_1 = commands.AddTask(id=task_1, story=story_id)
        add_task_2 = commands.AddTask(id=task_2, story=story_id)
        bus.handle(add_task_1)
        bus.handle(add_task_2)
        add_story_to_sprint = commands.AddStory(id=story_id,
                                                 sprint=new_sprint)
        bus.handle(add_story_to_sprint)
        sprint = bus.uow.tasks.get_by_id(entities.sprint.Sprint,
                                                 new_sprint)
        assert len(sprint.tasks) == 2

    def test_adding_epic_to_sprint_adds_non_completed_tasks(
            self, bus, new_sprint, tasks):
        task_1, task_2 = tasks
        create_epic = commands.CreateEpic(name="epic_1")
        epic_id = bus.handle(create_epic)
        add_task_1 = commands.AddTask(id=task_1, epic=epic_id)
        add_task_2 = commands.AddTask(id=task_2, epic=epic_id)
        bus.handle(add_task_1)
        bus.handle(add_task_2)
        add_epic_to_sprint = commands.AddEpic(id=epic_id, sprint=new_sprint)
        bus.handle(add_epic_to_sprint)
        sprint = bus.uow.tasks.get_by_id(entities.sprint.Sprint,
                                                 new_sprint)
        assert len(sprint.tasks) == 2

    def test_adding_story_to_sprint_adds_only_non_completed_tasks(
            self, bus, new_sprint, tasks):
        task_1, task_2 = tasks
        create_story = commands.CreateStory(name="story_1")
        story_id = bus.handle(create_story)
        add_task_1 = commands.AddTask(id=task_1, story=story_id)
        add_task_2 = commands.AddTask(id=task_2, story=story_id)
        bus.handle(add_task_1)
        bus.handle(add_task_2)
        complete_task = commands.CompleteTask(task_1)
        bus.handle(complete_task)
        add_story_to_sprint = commands.AddStory(id=story_id,
                                                 sprint=new_sprint)
        bus.handle(add_story_to_sprint)
        sprint = bus.uow.tasks.get_by_id(entities.sprint.Sprint,
                                                 new_sprint)
        assert len(sprint.tasks) == 1

    def test_adding_epic_to_sprint_adds_only_non_completed_tasks(
            self, bus, new_sprint, tasks):
        task_1, task_2 = tasks
        create_epic = commands.CreateEpic(name="epic_1")
        epic_id = bus.handle(create_epic)
        add_task_1 = commands.AddTask(id=task_1, epic=epic_id)
        add_task_2 = commands.AddTask(id=task_2, epic=epic_id)
        bus.handle(add_task_1)
        bus.handle(add_task_2)
        complete_task = commands.CompleteTask(task_1)
        bus.handle(complete_task)
        add_epic_to_sprint = commands.AddEpic(id=epic_id, sprint=new_sprint)
        bus.handle(add_epic_to_sprint)
        sprint = bus.uow.tasks.get_by_id(entities.sprint.Sprint,
                                                 new_sprint)
        assert len(sprint.tasks) == 1
