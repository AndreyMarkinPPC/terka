from dataclasses import asdict
from datetime import datetime

from terka.adapters import publisher
from terka.domain import _commands, events, models
from terka.service_layer import exceptions, templates, unit_of_work


class SprintCommandHandlers:

    @staticmethod
    def create(cmd: _commands.CreateSprint,
               uow: unit_of_work.AbstractUnitOfWork,
               publisher: publisher.BasePublisher) -> None:
        if not cmd:
            cmd = templates.create_command_from_editor(models.sprint.Sprint,
                                                       _commands.CreateSprint)
        with uow:
            # TODO: Add code for checking existing sprints
            new_sprint = models.sprint.Sprint(**asdict(cmd))
            uow.tasks.add(new_sprint)
            uow.commit()

    @staticmethod
    def start(cmd: _commands.StartSprint, uow: unit_of_work.AbstractUnitOfWork,
              publisher: publisher.BasePublisher) -> None:
        with uow:
            if not (existing_sprint := uow.tasks.get_by_id(
                    models.sprint.Sprint, cmd.id)):
                raise exceptions.EntityNotFound(
                    f"Sprint id {cmd.id} is not found")
            if existing_sprint.end_date < datetime.today().date():
                raise exceptions.TerkaSprintEndDateInThePast(
                    "Cannot start the sprint, end date in the past")
            if existing_sprint.status.name == "ACTIVE":
                raise exceptions.TerkaSprintActive(
                    "Sprint already started")
            if existing_sprint.status.name == "COMPLETED":
                raise exceptions.TerkaSprintCompleted(
                    "Cannot start completed sprint")
            uow.tasks.update(models.sprint.Sprint, cmd.id, {"status": "ACTIVE"})
            for sprint_task in existing_sprint.tasks:
                task = sprint_task.tasks
                task_params = {}
                if task.status.name == "BACKLOG":
                    task_params.update({"status": "TODO"})
                if not task.due_date or task.due_date > existing_sprint.end_date:
                    task_params.update({"due_date": existing_sprint.end_date})
                if task_params:
                    uow.published_events.append(
                        events.TaskUpdated(task.id,
                                           events.UpdateMask(**task_params)))
                if sprint_task.story_points == 0:
                    story_points = input(
                        "Please enter story points estimation "
                        f"for task <{task.id}>: {task.name}: ")
                    try:
                        story_points = float(story_points)
                        uow.published_events.append(
                            events.SprintTaskStoryPointAssigned(
                                sprint_task.id, story_points))
                    except ValueError:
                        print(
                            "[red]Provide number when specifying story points[/red]"
                        )
            uow.commit()


class SprintEventHandlers:

    @staticmethod
    def assign_story_points(event: events.SprintTaskStoryPointAssigned,
                            uow: unit_of_work.AbstractUnitOfWork) -> None:
        with uow:
            uow.tasks.update(models.sprint.SprintTask, event.id,
                             {"story_points": event.story_points})
            uow.commit()


class TaskCommandHandlers:

    @staticmethod
    def create(cmd: _commands.CreateTask, uow: unit_of_work.AbstractUnitOfWork,
               publisher: publisher.BasePublisher) -> None:
        if not cmd.name:
            cmd = templates.create_command_from_editor(models.task.Task,
                                                       _commands.CreateTask)

        with uow:
            if not (project_name := cmd.project).isnumeric():
                if not (existing_project := uow.tasks.get(
                        models.project.Project, project_name)):
                    print(f"Creating new project: {project_name}. "
                          "Do you want to continue (Y/n)?")
                    answer = input()
                    while answer.lower() != "y":
                        print("Provide a project name: ")
                        project_name = input()
                        print(f"Creating new project: {project_name}. "
                              "Do you want to continue (Y/n)?")
                        answer = input()
                    project_id = ProjectCommandHandlers.create(
                        cmd=_commands.CreateProject(name=project_name),
                        uow=uow,
                        publisher=publisher)
                    cmd.project = project_id
                else:
                    cmd.project = int(existing_project.id)
            new_task = models.task.Task(**asdict(cmd))
            uow.tasks.add(new_task)
            uow.flush()
            uow.published_events.append(events.TaskCreated(new_task.id))
            if tags := cmd.tags:
                for tag in tags.split(","):
                    uow.published_events.append(
                        events.TaskTagAdded(id=new_task.id, tag=tag))
            if collaborators := cmd.collaborators:
                for collaborator_name in collaborators.split(","):
                    uow.published_events.append(
                        events.TaskCollaboratorAdded(
                            id=new_task.id, collaborator=collaborator_name))
            if sprints := cmd.sprint_id:
                for sprint_id in sprints.split(","):
                    uow.published_events.append(
                        events.TaskAddedToSprint(id=new_task.id,
                                                 sprint_id=sprint_id))
            if epics := cmd.epic_id:
                for epic_id in epics.split(","):
                    uow.published_events.append(
                        events.TaskAddedToEpic(id=new_task.id,
                                               epic_id=epic_id))
            if stories := cmd.story_id:
                for story_id in stories.split(","):
                    uow.published_events.append(
                        events.TaskAddedToStory(id=new_task.id,
                                                story_id=story_id))
            uow.commit()
            publisher.publish("Topic", events.TaskCompleted(new_task.id))

    @staticmethod
    def update(cmd: _commands.UpdateTask, uow: unit_of_work.AbstractUnitOfWork,
               publisher: publisher.BasePublisher) -> None:
        ...

    @staticmethod
    def collaborate(cmd: _commands.CollaborateTask,
                    uow: unit_of_work.AbstractUnitOfWork,
                    publisher: publisher.BasePublisher) -> None:
        with uow:
            if not (existing_task := uow.tasks.get_by_id(
                    models.task.Task, cmd.id)):
                raise exceptions.EntityNotFound(
                    f"Task id {event.id} is not found")
            if not (existing_user := uow.tasks.list(
                    models.user.User, {"name": cmd.collaborator})):
                new_user = models.user.User(name=cmd.collaborator)
                uow.tasks.add(new_user)
                uow.flush()
                user_id = new_user.id
            else:
                user_id = existing_user[0].id
            if not uow.tasks.list(models.collaborator.TaskCollaborator, {
                    "task": cmd.id,
                    "collaborator": user_id
            }):
                uow.tasks.add(
                    models.collaborator.TaskCollaborator(
                        id=cmd.id, collaborator_id=user_id))
                uow.commit()

    @staticmethod
    def add(cmd: _commands.AddTask, uow: unit_of_work.AbstractUnitOfWork,
            publisher: publisher.BasePublisher) -> None:

        entity_name = cmd.entity_type
        entity_module = getattr(models, entity_name)
        entity = getattr(entity_module, entity_name.capitalize())
        entity_task_type = getattr(entity_module,
                                   f"{entity_name.capitalize()}Task")
        entity_dict = {"task": cmd.id}
        entity_dict[cmd.entity_type] = cmd.entity_id
        with uow:
            if not uow.tasks.get_by_id(entity, cmd.entity_id):
                raise exceptions.EntityNotFound(
                    f"{entity_name} id {cmd.entity_id} is not found")
            if uow.tasks.list(entity_task_type, entity_dict):
                raise exceptions.TaskAddedToEntity(
                    f"task {event.id} already added to "
                    f"{entity_name} {cmd.entity_id}")
            entity_task = entity_task_type(**entity_dict)
            uow.tasks.add(entity_task)
            uow.commit()

    @staticmethod
    def assign(cmd: _commands.AssignTask, uow: unit_of_work.AbstractUnitOfWork,
               publisher: publisher.BasePublisher) -> None:
        ...

    @staticmethod
    def complete(cmd: _commands.CompleteTask,
                 uow: unit_of_work.AbstractUnitOfWork,
                 publisher: publisher.BasePublisher) -> None:
        with uow:
            uow.tasks.update(models.task.Task, cmd.id, {"status": "DONE"})
            task_completed_event = events.TaskCompleted(cmd.id)
            uow.published_events.append(task_completed_event)
            if comment := cmd.comment:
                uow.published_events.append(
                    events.TaskCommentAdded(id=cmd.id, text=comment))
            if hours := cmd.hours:
                uow.published_events.append(
                    events.TaskHoursSubmitted(id=cmd.id, hours=hours))
            uow.commit()
            publisher.publish("Topic", task_completed_event)

    @staticmethod
    def delete(cmd: _commands.DeleteTask, uow: unit_of_work.AbstractUnitOfWork,
               publisher: publisher.BasePublisher) -> None:
        with uow:
            if cmd.entity_type and cmd.entity_id:
                ...
            else:
                uow.tasks.update(models.task.Task, cmd.id,
                                 {"status": "DELETED"})
                uow.published_events.append(events.TaskDeleted(cmd.id))
            if comment := cmd.comment:
                uow.published_events.append(
                    events.TaskCommentAdded(id=cmd.id, text=comment))
            if hours := cmd.hours:
                uow.published_events.append(
                    events.TaskHoursSubmitted(id=cmd.id, hours=hours))
            uow.commit()
        publisher.publish("Topic", events.TaskCompleted(cmd.id))

    # @staticmethod
    # def collaborate(cmd: _commands.TaskCollaboratorAdded, uow: unit_of_work.AbstractUnitOfWork,
    #         publisher: publisher.BasePublisher) -> None:
    #     ...
    @staticmethod
    def tag(cmd: _commands.TagTask, uow: unit_of_work.AbstractUnitOfWork,
            publisher: publisher.BasePublisher) -> None:
        ...
        # with uow:
        #     if not (tag := uow.tasks.get

        #     uow.tasks.add(task.Task, cmd.id, {"status": "DELETED"})
        #     uow.published_events.append(events.TaskDeleted(cmd.id))
        #     if comment := cmd.comment:
        #         uow.published_events.append(
        #             events.TaskCommentAdded(id=cmd.id, text=comment))
        #     if hours := cmd.hours:
        #         uow.published_events.append(
        #             events.TaskHoursSubmitted(id=cmd.id, hours=hours))
        #     uow.commit()
        # publisher.publish("Topic", events.TaskCompleted(cmd.id))
        #         tag = self.repo.list(BaseTag, tag_info)
        #         if not tag:
        #             tag = BaseTag(**tag_info)
        #             self.repo.add(tag)
        #             session.commit()
        #             tag_id = tag.id
        #         else:
        #             tag_id = tag[0].id
        #         existing_task_tag = self.repo.list(TaskTag, {
        #             "task": task_id,
        #             "tag": tag_id
        #         })
        #         if not existing_task_tag:
        #             task_ids = get_ids(task_id)
        #             for task_id in task_ids:
        #                 obj = TaskTag(id=task_id, tag_id=tag_id)
        #                 self.repo.add(obj)


class TaskEventHandlers:

    @staticmethod
    def created(event: events.TaskCreated,
                uow: unit_of_work.AbstractUnitOfWork) -> None:
        # TODO: Decide what to do here
        ...

    @staticmethod
    def completed(event: events.TaskCompleted,
                  uow: unit_of_work.AbstractUnitOfWork) -> None:
        with uow:
            task_event = models.event_history.TaskEvent(task_id=event.id,
                                                        event_type="STATUS",
                                                        old_value="",
                                                        new_value="DONE")
            uow.tasks.add(task_event)
            uow.commit()

    @staticmethod
    def updated(event: events.TaskUpdated,
                uow: unit_of_work.AbstractUnitOfWork) -> None:
        with uow:
            uow.tasks.update(models.task.Task, event.id,
                            event.update_mask.get_only_set_attributes())
            uow.commit()

    @staticmethod
    def deleted(event: events.TaskDeleted,
                uow: unit_of_work.AbstractUnitOfWork) -> None:
        with uow:
            task_event = models.event_history.TaskEvent(task_id=event.id,
                                                        event_type="STATUS",
                                                        old_value="",
                                                        new_value="DELETED")
            uow.tasks.add(task_event)
            uow.commit()

    @staticmethod
    def tag_added(event: events.TaskTagAdded,
                  uow: unit_of_work.AbstractUnitOfWork) -> None:
        with uow:
            if not (existing_task := uow.tasks.get_by_id(
                    models.task.Task, event.id)):
                raise exceptions.EntityNotFound(
                    f"Task id {event.id} is not found")
            if not (existing_tag := uow.tasks.list(models.tag.BaseTag,
                                                   {"text": event.tag})):
                new_tag = models.tag.BaseTag(text=event.tag)
                uow.tasks.add(new_tag)
                uow.flush()
                tag_id = new_tag.id
            else:
                tag_id = existing_tag[0].id
            if not uow.tasks.list(models.tag.TaskTag, {
                    "task": event.id,
                    "tag": tag_id
            }):
                uow.tasks.add(models.tag.TaskTag(id=event.id, tag_id=tag_id))
                uow.commit()

    @staticmethod
    def comment_added(event: events.TaskCommentAdded,
                      uow: unit_of_work.AbstractUnitOfWork) -> None:
        with uow:
            uow.tasks.add(
                models.commentary.TaskCommentary(id=event.id, text=event.text))
            uow.tasks.update(models.task.Task, event.id,
                             {"modification_date": datetime.now()})
            uow.commit()

    @staticmethod
    def collaborator_added(event: events.TaskCollaboratorAdded,
                           uow: unit_of_work.AbstractUnitOfWork) -> None:
        TaskCommandHandlers.collaborate(
            cmd=_commands.CollaborateTask(**asdict(event)),
            uow=uow,
            publisher=publisher)

    @staticmethod
    def hours_submitted(event: events.TaskHoursSubmitted,
                        uow: unit_of_work.AbstractUnitOfWork) -> None:
        with uow:
            uow.tasks.add(
                models.time_tracker.TimeTrackerEntry(
                    task=event.id, time_spent_minutes=event.hours))
            uow.commit()

    @staticmethod
    def added_to_epic(event: events.TaskAddedToEpic,
                      uow: unit_of_work.AbstractUnitOfWork) -> None:
        TaskCommandHandlers.add(cmd=_commands.AddTask(id=event.id,
                                                      entity_type="epic",
                                                      entity_id=event.epic_id),
                                uow=uow,
                                publisher=publisher)

    @staticmethod
    def added_to_sprint(event: events.TaskAddedToSprint,
                        uow: unit_of_work.AbstractUnitOfWork) -> None:
        TaskCommandHandlers.add(cmd=_commands.AddTask(
            id=event.id, entity_type="sprint", entity_id=event.sprint_id),
                                uow=uow,
                                publisher=publisher)

    @staticmethod
    def added_to_story(event: events.TaskAddedToStory,
                       uow: unit_of_work.AbstractUnitOfWork) -> None:
        TaskCommandHandlers.add(cmd=_commands.AddTask(
            id=event.id, entity_type="story", entity_id=event.story_id),
                                uow=uow,
                                publisher=publisher)


class ProjectCommandHandlers:

    @staticmethod
    def create(cmd: _commands.CreateProject,
               uow: unit_of_work.AbstractUnitOfWork,
               publisher: publisher.BasePublisher) -> int:
        project_id = None
        with uow:
            new_project = models.project.Project(**asdict(cmd))
            uow.tasks.add(new_project)
            uow.flush()
            project_id = int(new_project.id)
            new_event = events.ProjectCreated(project_id)
            uow.published_events.append(new_event)
            uow.commit()
            publisher.publish("Topic", new_event)
        return project_id


class ProjectEventHandlers:

    @staticmethod
    def created(event: events.ProjectCreated,
                uow: unit_of_work.AbstractUnitOfWork) -> None:
        # TODO: Decide what to do here
        ...


EVENT_HANDLERS = {
    events.TaskCreated: [TaskEventHandlers.created],
    events.TaskCompleted: [TaskEventHandlers.completed],
    events.TaskUpdated: [TaskEventHandlers.updated],
    events.TaskDeleted: [TaskEventHandlers.deleted],
    events.TaskCommentAdded: [TaskEventHandlers.comment_added],
    events.TaskCollaboratorAdded: [TaskEventHandlers.collaborator_added],
    events.TaskHoursSubmitted: [TaskEventHandlers.hours_submitted],
    events.TaskTagAdded: [TaskEventHandlers.tag_added],
    events.TaskAddedToEpic:
    [TaskEventHandlers.added_to_epic, TaskCommandHandlers.tag],
    events.TaskAddedToSprint:
    [TaskEventHandlers.added_to_sprint, TaskCommandHandlers.tag],
    events.TaskAddedToStory:
    [TaskEventHandlers.added_to_story, TaskCommandHandlers.tag],
    events.ProjectCreated: [ProjectEventHandlers.created],
    events.SprintTaskStoryPointAssigned:
    [SprintEventHandlers.assign_story_points],
}

COMMAND_HANDLERS = {
    _commands.CompleteTask: TaskCommandHandlers.complete,
    _commands.DeleteTask: TaskCommandHandlers.delete,
    _commands.CreateTask: TaskCommandHandlers.create,
    _commands.AddTask: TaskCommandHandlers.add,
    _commands.CreateProject: ProjectCommandHandlers.create,
    _commands.CreateSprint: SprintCommandHandlers.create,
    _commands.StartSprint: SprintCommandHandlers.start,
}
