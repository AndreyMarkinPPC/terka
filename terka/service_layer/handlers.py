from typing import Type
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
import functools
import logging

from terka.adapters import publisher, printer
from terka.domain import _commands, events, models
from terka.service_layer import exceptions, templates, unit_of_work

COMMAND_HANDLERS = {}
EVENT_HANDLERS = defaultdict(list)


def register(cmd=None, event=None):

    def fn(func):

        @functools.wraps(func)
        def inner_function(cmd, handler, context):
            return func(cmd, handler, context)

        if cmd:
            COMMAND_HANDLERS[cmd] = inner_function
        elif event:
            EVENT_HANDLERS[event].append(inner_function)
        return inner_function

    return fn


class Handler:

    def __init__(
        self,
        uow: unit_of_work.AbstractUnitOfWork,
        publisher: publisher.BasePublisher = None,
        printer: printer.Printer = printer.Printer()
    ) -> None:
        self.uow = uow
        self.publisher = publisher
        self.printer = printer


class SprintCommandHandlers:

    @register(cmd=_commands.CreateSprint)
    def create(cmd: _commands.CreateSprint,
               handler: Handler,
               context: dict = {}) -> None:
        if not cmd:
            cmd, context = templates.create_command_from_editor(
                models.sprint.Sprint, type(cmd))
        with handler.uow as uow:
            # TODO: Add code for checking existing sprints
            new_sprint = models.sprint.Sprint(**asdict(cmd))
            uow.tasks.add(new_sprint)
            uow.commit()

    @register(cmd=_commands.StartSprint)
    def start(cmd: _commands.StartSprint,
              handler: Handler,
              context: dict = {}) -> None:
        with handler.uow as uow:
            if not (existing_sprint := uow.tasks.get_by_id(
                    models.sprint.Sprint, cmd.id)):
                raise exceptions.EntityNotFound(
                    f"Sprint id {cmd.id} is not found")
            if existing_sprint.end_date < datetime.today().date():
                raise exceptions.TerkaSprintEndDateInThePast(
                    "Cannot start the sprint, end date in the past")
            if existing_sprint.status.name == "ACTIVE":
                raise exceptions.TerkaSprintActive("Sprint already started")
            if existing_sprint.status.name == "COMPLETED":
                raise exceptions.TerkaSprintCompleted(
                    "Cannot start completed sprint")
            uow.tasks.update(models.sprint.Sprint, cmd.id,
                             {"status": "ACTIVE"})
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
            logging.debug(f"Sprint started, context: {cmd}")

    @register(cmd=_commands.CompleteSprint)
    def complete(cmd: _commands.CompleteSprint,
                 handler: Handler,
                 context: dict = {}) -> None:
        with handler.uow as uow:
            if not (existing_sprint := uow.tasks.get_by_id(
                    models.sprint.Sprint, cmd.id)):
                raise exceptions.EntityNotFound(
                    f"Sprint id {cmd.id} is not found")
            uow.tasks.update(models.sprint.Sprint, cmd.id,
                             {"status": "COMPLETED"})
            for sprint_task in existing_sprint.tasks:
                task = sprint_task.tasks
                task_params = {}
                if task.status.name == "TODO":
                    task_params.update({"status": "BACKLOG"})
                if task.due_date:
                    task_params.update({"due_date": None})
                if task_params:
                    uow.published_events.append(
                        events.TaskUpdated(task.id,
                                           events.UpdateMask(**task_params)))
            uow.commit()
            uow.published_events.append(events.SprintCompleted(cmd.id))
            if comment := cmd.comment:
                uow.published_events.append(
                    events.Sprintommented(id=cmd.id, text=comment))
            uow.commit()
            logging.debug(f"Sprint completed, context: {cmd}")
        handler.publisher.publish("Topic", events.SprintCompleted(cmd.id))

    @register(cmd=_commands.ListSprint)
    def list(cmd: _commands.ListSprint,
             handler: Handler,
             context: dict = {}) -> None:
        with handler.uow as uow:
            if sprints := uow.tasks.list(models.sprint.Sprint):
                handler.printer.console.print_sprint(
                    sprints, printer.PrintOptions.from_kwargs(**context))


class SprintEventHandlers:

    def assign_story_points(event: events.SprintTaskStoryPointAssigned,
                            handler: Handler,
                            context: dict = {}) -> None:
        with handler.uow as uow:
            uow.tasks.update(models.sprint.SprintTask, event.id,
                             {"story_points": event.story_points})
            uow.commit()
            logging.debug(f"Story point assigned, context: {event}")


class TaskCommandHandlers:

    @register(cmd=_commands.CreateTask)
    def create(cmd: _commands.CreateTask,
               handler: Handler,
               context: dict = {}) -> None:
        # TODO: context should be taken from console as well
        if not cmd.name:
            cmd, context = templates.create_command_from_editor(
                models.task.Task, _commands.CreateTask)
        with handler.uow as uow:
            cmd = convert_project(cmd, handler)
            new_task = models.task.Task(**asdict(cmd))
            uow.tasks.add(new_task)
            uow.flush()
            task_created_event = events.TaskCreated(new_task.id)
            uow.published_events.append(task_created_event)
            uow.commit()
            TaskCommandHandlers._process_extra_args(new_task.id, context, uow)
            handler.publisher.publish("Topic", task_created_event)
            handler.printer.console.print_new_object(new_task)

    @register(cmd=_commands.UpdateTask)
    def update(cmd: _commands.UpdateTask,
               handler: Handler,
               context: dict = {}) -> None:
        with handler.uow as uow:
            if not (existing_task := uow.tasks.get_by_id(
                    models.task.Task, cmd.id)):
                raise exceptions.EntityNotFound(
                    f"Task id {cmd.id} is not found")
            if not cmd:
                cmd, context = templates.create_command_from_editor(
                    existing_task, _commands.UpdateTask)
                cmd.id = existing_task.id
            cmd = convert_project(cmd, handler)
            uow.tasks.update(models.task.Task, cmd.id,
                             cmd.get_only_set_attributes())
            uow.commit()
            TaskCommandHandlers._process_extra_args(cmd.id, context, uow)

    @register(cmd=_commands.CollaborateTask)
    def collaborate(cmd: _commands.CollaborateTask,
                    handler: Handler,
                    context: dict = {}) -> None:
        with handler.uow as uow:
            if not (existing_task := uow.tasks.get_by_id(
                    models.task.Task, cmd.id)):
                raise exceptions.EntityNotFound(
                    f"Task id {cmd.id} is not found")
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

    @register(cmd=_commands.AddTask)
    def add(cmd: _commands.AddTask,
            handler: Handler,
            context: dict = {}) -> None:

        if (sprint := cmd.sprint) and (story_points := cmd.story_points):
            updated_context = {"entity_type": "sprint", "entity_id": sprint}
            TaskCommandHandlers._add(
                _commands.AddTask(cmd.id,
                                  sprint=sprint,
                                  story_points=story_points), handler,
                updated_context)

        else:
            for field in cmd.__dataclass_fields__:
                if field_value := getattr(cmd, field):
                    updated_context = {
                        "entity_type": field,
                        "entity_id": field_value
                    }
                    if field == "sprint":
                        TaskCommandHandlers._add(
                            _commands.AddTask(cmd.id, sprint=field_value),
                            handler, updated_context)
                    if field == "epic":
                        TaskCommandHandlers._add(
                            _commands.AddTask(cmd.id, epic=field_value),
                            handler, updated_context)
                    if field == "story":
                        TaskCommandHandlers._add(
                            _commands.AddTask(cmd.id, story=field_value),
                            handler, updated_context)

    def _add(cmd: _commands.AddTask, handler: Handler, context) -> None:
        entity_name, entity_id = context["entity_type"], context["entity_id"]
        entity_module = getattr(models, entity_name)
        entity = getattr(entity_module, entity_name.capitalize())
        entity_task_type = getattr(entity_module,
                                   f"{entity_name.capitalize()}Task")
        entity_dict = {"task": cmd.id}
        entity_dict[entity_name] = entity_id
        story_points = cmd.story_points
        with handler.uow as uow:
            if not (existing_entity := uow.tasks.get_by_id(entity, entity_id)):
                raise exceptions.EntityNotFound(
                    f"{entity_name} id {entity_id} is not found")
            if (existing_entity_task := uow.tasks.list(entity_task_type,
                                                       entity_dict)):
                if not story_points:
                    raise exceptions.TaskAddedToEntity(
                        f"task {cmd.id} already added to "
                        f"{entity_name} {entity_id}")
                else:
                    uow.tasks.update(entity_task_type,
                                     existing_entity_task[0].id,
                                     {"story_points": float(story_points)})
                    uow.commit()
            else:
                if entity_name == "sprint" and story_points:
                    entity_dict["story_points"] = story_points
                entity_task = entity_task_type(**entity_dict)
                uow.tasks.add(entity_task)
                uow.commit()
                logging.debug(f"Task added to {entity_name}, context {cmd}")
                if entity_name == "sprint":
                    if existing_entity.status == models.sprint.SprintStatus.COMPLETED:
                        raise exceptions.TerkaSprintCompleted(
                            f"Sprint {entity_id} is completed")
                    if existing_task := uow.tasks.get_by_id(
                            models.task.Task, cmd.id):
                        task_params = {}
                        if existing_task.status.name == "BACKLOG":
                            task_params.update({"status": "TODO"})
                        if (not existing_task.due_date
                                or existing_task.due_date
                                > existing_entity.end_date
                                or existing_task.due_date
                                < existing_entity.start_date):
                            task_params.update(
                                {"due_date": existing_entity.end_date})
                        if task_params:
                            uow.published_events.append(
                                events.TaskUpdated(
                                    cmd.id, events.UpdateMask(**task_params)))

    @register(cmd=_commands.AssignTask)
    def assign(cmd: _commands.AssignTask,
               handler: Handler,
               context: dict = {}) -> None:
        ...

    @register(cmd=_commands.CompleteTask)
    def complete(cmd: _commands.CompleteTask,
                 handler: Handler,
                 context: dict = {}) -> None:
        with handler.uow as uow:
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
            handler.publisher.publish("Topic", task_completed_event)

    @register(cmd=_commands.DeleteTask)
    def delete(cmd: _commands.DeleteTask,
               handler: Handler,
               context: dict = {}) -> None:

        for field in cmd.__dataclass_fields__:
            if field_value := getattr(cmd, field):
                updated_context = {
                    "entity_type": field,
                    "entity_id": field_value
                }
                if field == "sprint":
                    TaskCommandHandlers._delete(
                        _commands.DeleteTask(cmd.id, sprint=field_value),
                        handler, updated_context)
                if field == "epic":
                    TaskCommandHandlers._delete(
                        _commands.DeleteTask(cmd.id, epic=field_value),
                        handler, updated_context)
                if field == "story":
                    TaskCommandHandlers._delete(
                        _commands.DeleteTask(cmd.id, story=field_value),
                        handler, updated_context)

    def _delete(cmd: _commands.DeleteTask,
                handler: Handler,
                context: dict = {}) -> None:
        with handler.uow as uow:
            if "entity_type" in context and "entity_id" in context:
                entity_name, entity_id = context["entity_type"], context[
                    "entity_id"]
                entity_module = getattr(models, entity_name)
                entity = getattr(entity_module, entity_name.capitalize())
                entity_task_type = getattr(entity_module,
                                           f"{entity_name.capitalize()}Task")
                entity_dict = {"task": cmd.id}
                entity_dict[entity_name] = entity_id
                if not (existing_entity := uow.tasks.get_by_id(
                        entity, entity_id)):
                    raise exceptions.EntityNotFound(
                        f"{entity_name} id {entity_id} is not found")
                if existing_entity_task := uow.tasks.list(
                        entity_task_type, entity_dict):
                    uow.tasks.delete(entity_task_type, cmd.id)
                    uow.commit()
                    logging.debug(
                        f"Task deleted from {entity_name.capitalize()} "
                        f"{entity_id}, context {cmd}")
                    if entity_name == "sprint":
                        if existing_task := uow.tasks.get_by_id(
                                models.task.Task, cmd.id):
                            task_params = {}
                            if existing_task.status.name == "TODO":
                                task_params.update({"status": "BACKLOG"})
                            task_params.update({"due_date": None})
                            if task_params:
                                uow.published_events.append(
                                    events.TaskUpdated(
                                        cmd.id,
                                        events.UpdateMask(**task_params)))
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
        handler.publisher.publish("Topic", events.TaskCompleted(cmd.id))

    @register(cmd=_commands.CommentTask)
    def comment(cmd: _commands.CommentTask,
                handler: Handler,
                context: dict = {}) -> None:
        with handler.uow as uow:
            uow.tasks.add(
                models.commentary.TaskCommentary(id=cmd.id, text=cmd.text))
            uow.tasks.update(models.task.Task, cmd.id,
                             {"modification_date": datetime.now()})
            uow.commit()

    @register(cmd=_commands.TrackTask)
    def track(cmd: _commands.TrackTask,
              handler: Handler,
              context: dict = {}) -> None:
        with handler.uow as uow:
            if not (existing_task := uow.tasks.get_by_id(
                    models.task.Task, cmd.id)):
                raise exceptions.EntityNotFound(
                    f"Task id {cmd.id} is not found")
            uow.tasks.add(
                models.time_tracker.TimeTrackerEntry(
                    task=cmd.id, time_spent_minutes=cmd.hours))
            uow.commit()

    @register(cmd=_commands.TagTask)
    def tag(cmd: _commands.TagTask,
            handler: Handler,
            context: dict = {}) -> None:
        with handler.uow as uow:
            if not (existing_task := uow.tasks.get_by_id(
                    models.task.Task, cmd.id)):
                raise exceptions.EntityNotFound(
                    f"Task id {cmd.id} is not found")
            if not (existing_tag := uow.tasks.list(models.tag.BaseTag,
                                                   {"text": cmd.tag})):
                new_tag = models.tag.BaseTag(text=cmd.tag)
                uow.tasks.add(new_tag)
                uow.flush()
                tag_id = new_tag.id
            else:
                tag_id = existing_tag[0].id
            if not uow.tasks.list(models.tag.TaskTag, {
                    "task": cmd.id,
                    "tag": tag_id
            }):
                uow.tasks.add(models.tag.TaskTag(id=cmd.id, tag_id=tag_id))
                uow.commit()

    def _process_extra_args(id, context, uow):
        if tags := context.get("tags"):
            for tag in tags.split(","):
                uow.published_events.append(events.TaskTagAdded(id=id,
                                                                tag=tag))
        if collaborators := context.get("collaborators"):
            for collaborator_name in collaborators.split(","):
                uow.published_events.append(
                    events.TaskCollaboratorAdded(
                        id=id, collaborator=collaborator_name))
        if sprints := context.get("sprint"):
            for sprint_id in sprints.split(","):
                uow.published_events.append(
                    events.TaskAddedToSprint(id=id, sprint_id=sprint_id))
        if epics := context.get("epic"):
            for epic_id in epics.split(","):
                uow.published_events.append(
                    events.TaskAddedToEpic(id=id, epic_id=epic_id))
        if stories := context.get("story"):
            for story_id in stories.split(","):
                uow.published_events.append(
                    events.TaskAddedToStory(id=id, story_id=story_id))
        if comment := context.get("comment"):
            uow.published_events.append(
                events.TaskCommentAdded(id=id, text=comment))
        if hours := context.get("time_spent"):
            uow.published_events.append(
                events.TaskHoursSubmitted(id=id, hours=hours))


class TaskEventHandlers(Handler):

    @register(event=events.TaskCreated)
    def created(event: events.TaskCreated,
                handler: Handler,
                context: dict = {}) -> None:
        # TODO: Decide what to do here
        ...

    @register(event=events.TaskCompleted)
    def completed(event: events.TaskCompleted,
                  handler: Handler,
                  context: dict = {}) -> None:
        with handler.uow as uow:
            task_event = models.event_history.TaskEvent(task_id=event.id,
                                                        event_type="STATUS",
                                                        old_value="",
                                                        new_value="DONE")
            uow.tasks.add(task_event)
            uow.commit()

    @register(event=events.TaskUpdated)
    def updated(event: events.TaskUpdated,
                handler: Handler,
                context: dict = {}) -> None:
        with handler.uow as uow:
            uow.tasks.update(models.task.Task, event.id,
                             event.update_mask.get_only_set_attributes())
            current_task = uow.tasks.get_by_id(models.task.Task, event.id)
            for key, updated_value in asdict(event.update_mask).items():
                old_value = getattr(current_task, key)
                if hasattr(old_value, "name"):
                    old_value = old_value.name
                if old_value != updated_value:
                    if updated_value or key.endswith("date"):
                        task_event = models.event_history.TaskEvent(
                            task_id=event.id,
                            event_type=key.upper(),
                            old_value=old_value,
                            new_value=updated_value)
                        uow.tasks.add(task_event)
            uow.commit()
            logging.debug(f"Task updated, context {event}")

    @register(event=events.TaskDeleted)
    def deleted(event: events.TaskDeleted,
                handler: Handler,
                context: dict = {}) -> None:
        with handler.uow as uow:
            task_event = models.event_history.TaskEvent(task_id=event.id,
                                                        event_type="STATUS",
                                                        old_value="",
                                                        new_value="DELETED")
            uow.tasks.add(task_event)
            uow.commit()

    @register(event=events.TaskTagAdded)
    def tag_added(event: events.TaskTagAdded,
                  handler: Handler,
                  context: dict = {}) -> None:
        TaskCommandHandlers.tag(cmd=_commands.TagTask(**asdict(event)),
                                handler=handler,
                                context=context)

    @register(event=events.TaskCommentAdded)
    def comment_added(event: events.TaskCommentAdded,
                      handler: Handler,
                      context: dict = {}) -> None:
        TaskCommandHandlers.comment(cmd=_commands.CommentTask(**asdict(event)),
                                    handler=handler,
                                    context=context)

    @register(event=events.TaskCollaboratorAdded)
    def collaborator_added(event: events.TaskCollaboratorAdded,
                           handler: Handler,
                           context: dict = {}) -> None:
        TaskCommandHandlers.collaborate(
            cmd=_commands.CollaborateTask(**asdict(event)),
            handler=handler,
            context=context)

    @register(event=events.TaskHoursSubmitted)
    def hours_submitted(event: events.TaskHoursSubmitted,
                        handler: Handler,
                        context: dict = {}) -> None:
        TaskCommandHandlers.track(cmd=_commands.TrackTask(id=event.id,
                                                          hours=event.hours),
                                  handler=handler,
                                  context=context)

    @register(event=events.TaskAddedToEpic)
    def added_to_epic(event: events.TaskAddedToEpic,
                      handler: Handler,
                      context: dict = {}) -> None:
        TaskCommandHandlers.add(cmd=_commands.AddTask(id=event.id,
                                                      epic=event.epic_id),
                                handler=handler,
                                context=context)

    @register(event=events.TaskAddedToSprint)
    def added_to_sprint(event: events.TaskAddedToSprint,
                        handler: Handler,
                        context: dict = {}) -> None:
        TaskCommandHandlers.add(cmd=_commands.AddTask(id=event.id,
                                                      sprint=event.sprint_id),
                                handler=handler,
                                context=context)

    @register(event=events.TaskAddedToStory)
    def added_to_story(event: events.TaskAddedToStory,
                       handler: Handler,
                       context: dict = {}) -> None:
        TaskCommandHandlers.add(cmd=_commands.AddTask(id=event.id,
                                                      story=event.story_id),
                                handler=handler,
                                context=context)


class ProjectCommandHandlers:

    @register(cmd=_commands.CreateProject)
    def create(cmd: _commands.CreateProject,
               handler: Handler,
               context: dict = {}) -> None:
        if not cmd.name:
            cmd, context = templates.create_command_from_editor(
                models.project.Project, _commands.CreateProject)
        project_id = None
        with handler.uow as uow:
            if not (existing_project := uow.tasks.get(models.project.Project,
                                                      cmd.name)):
                cmd = convert_workspace(cmd, handler)
                new_project = models.project.Project(**asdict(cmd))
                uow.tasks.add(new_project)
                uow.flush()
                project_id = int(new_project.id)
                new_event = events.ProjectCreated(project_id)
                uow.published_events.append(new_event)
                uow.commit()
                handler.printer.console.print_new_object(new_project)
                handler.publisher.publish("Topic", new_event)
            else:
                logging.warning(f"Project {cmd.name} already exists")
                project_id = existing_project.id
            return project_id

    @register(cmd=_commands.UpdateProject)
    def update(cmd: _commands.UpdateProject,
               handler: Handler,
               context: dict = {}) -> None:
        with handler.uow as uow:
            project = ProjectCommandHandlers._validate_project(cmd.id, uow)
            if not cmd.name:
                cmd, context = templates.create_command_from_editor(
                    project, _commands.UpdateProject)
                cmd.id = project.id
            uow.tasks.update(models.project.Project, project.id,
                             cmd.get_only_set_attributes())
            if tags := context.get("tags"):
                for tag in tags.split(","):
                    uow.published_events.append(
                        events.ProjectTagAdded(id=project.id, tag=tag))
            if collaborators := context.get("collaborators"):
                for collaborator_name in collaborators.split(","):
                    uow.published_events.append(
                        events.ProjecCollaboratorAdded(
                            id=project.id, collaborator=collaborator_name))
            if comment := context.get("comment"):
                uow.published_events.append(
                    events.ProjectCommentAdded(id=project_id, text=comment))
            uow.commit()

    @register(cmd=_commands.CompleteProject)
    def complete(cmd: _commands.CompleteProject,
                 handler: Handler,
                 context: dict = {}) -> None:
        with handler.uow as uow:
            project = ProjectCommandHandlers._validate_project(cmd.id, uow)
            uow.tasks.update(models.project.Project, project.id,
                             {"status": "COMPLETED"})
            uow.published_events.append(events.ProjectCompleted(project.id))
            if comment := cmd.comment:
                uow.published_events.append(
                    events.ProjectCommented(id=project.id, text=comment))
            uow.commit()
        handler.publisher.publish("Topic", events.ProjectCompleted(project.id))

    @register(cmd=_commands.DeleteProject)
    def delete(cmd: _commands.DeleteProject,
               handler: Handler,
               context: dict = {}) -> None:
        with handler.uow as uow:
            project = ProjectCommandHandlers._validate_project(cmd.id, uow)
            uow.tasks.update(models.project.Project, project.id,
                             {"status": "DELETED"})
            uow.published_events.append(events.ProjectDeleted(project.id))
            if comment := cmd.comment:
                uow.published_events.append(
                    events.ProjectCommented(id=project.id, text=comment))
            uow.commit()
            handler.publisher.publish("Topic",
                                      events.ProjectDeleted(project.id))

    @register(cmd=_commands.CommentProject)
    def comment(cmd: _commands.CommentProject,
                handler: Handler,
                context: dict = {}) -> None:
        with handler.uow as uow:
            project = ProjectCommandHandlers._validate_project(cmd.id, uow)
            uow.tasks.add(
                models.commentary.ProjectCommentary(id=project.id,
                                                    text=cmd.text))
            uow.commit()

    @register(cmd=_commands.TagProject)
    def tag(cmd: _commands.TagProject,
            handler: Handler,
            context: dict = {}) -> None:
        with handler.uow as uow:
            project = ProjectCommandHandlers._validate_project(cmd.id, uow)
            if not (existing_tag := uow.tasks.list(models.tag.BaseTag,
                                                   {"text": cmd.tag})):
                new_tag = models.tag.BaseTag(text=cmd.tag)
                uow.tasks.add(new_tag)
                uow.flush()
                tag_id = new_tag.id
            else:
                tag_id = existing_tag[0].id
            if not uow.tasks.list(models.tag.ProjectTag, {
                    "project": project.id,
                    "tag": tag_id
            }):
                uow.tasks.add(
                    models.tag.ProjectTag(id=project.id, tag_id=tag_id))
                uow.commit()

    @register(cmd=_commands.ListProject)
    def list(cmd: _commands.ListProject,
             handler: Handler,
             context: dict = {}) -> None:
        with handler.uow as uow:
            if projects := uow.tasks.list(models.project.Project):
                handler.printer.console.print_project(
                    projects, printer.PrintOptions.from_kwargs(**context))

    def _validate_project(id: str | int, uow) -> models.project.Project:
        if id.isnumeric():
            if not (existing_project := uow.tasks.get_by_id(
                    models.project.Project, id)):
                raise exceptions.EntityNotFound(
                    f"Project id {id} is not found")
        else:
            if not (existing_project := uow.tasks.get(models.project.Project,
                                                      id)):

                raise exceptions.EntityNotFound(
                    f"Project id {id} is not found")
        return existing_project


class ProjectEventHandlers:

    @register(event=events.ProjectCreated)
    def created(event: events.ProjectCreated,
                handler: Handler,
                context: dict = {}) -> None:
        # TODO: Decide what to do here
        ...

    @register(event=events.ProjectCommented)
    def commented(event: events.ProjectCommented,
                  handler: Handler,
                  context: dict = {}) -> None:
        ProjectCommandHandlers.comment(
            cmd=_commands.CommentProject(**asdict(event)), handler=handler)


class EpicCommandHandlers:

    @register(cmd=_commands.CreateEpic)
    def create(cmd: _commands.CreateEpic,
               handler: Handler,
               context: dict = {}):
        if not cmd.name:
            cmd, context = templates.create_command_from_editor(
                models.epic.Epic, type(cmd))
        with handler.uow as uow:
            cmd = convert_project(cmd, handler)
            new_epic = models.epic.Epic(**asdict(cmd))
            uow.tasks.add(new_epic)
            uow.commit()
            handler.printer.console.print_new_object(new_epic)

    @register(cmd=_commands.CompleteEpic)
    def complete(cmd: _commands.CompleteEpic,
                 handler: Handler,
                 context: dict = {}) -> None:
        with handler.uow as uow:
            uow.tasks.update(models.project.Epic, cmd.id,
                             {"status": "COMPLETED"})
            uow.published_events.append(events.EpicCompleted(cmd.id))
            if comment := cmd.comment:
                uow.published_events.append(
                    events.EpicCommented(id=cmd.id, text=comment))
            uow.commit()
        handler.publisher.publish("Topic", events.EpicCompleted(cmd.id))

    @register(cmd=_commands.DeleteEpic)
    def delete(cmd: _commands.DeleteEpic,
               handler: Handler,
               context: dict = {}) -> None:
        with handler.uow as uow:
            uow.tasks.update(models.epic.Epic, cmd.id, {"status": "DELETED"})
            uow.published_events.append(events.EpicDeleted(cmd.id))
            if comment := cmd.comment:
                uow.published_events.append(
                    events.EpicCommented(id=cmd.id, text=comment))
            uow.commit()
        handler.publisher.publish("Topic", events.EpicDeleted(cmd.id))

    @register(cmd=_commands.CommentEpic)
    def comment(cmd: _commands.CommentEpic,
                handler: Handler,
                context: dict = {}) -> None:
        with handler.uow as uow:
            uow.tasks.add(
                models.commentary.EpicCommentary(id=cmd.id, text=cmd.text))
            uow.commit()

    @register(cmd=_commands.AddEpic)
    def add(cmd: _commands.AddEpic,
            handler: Handler,
            context: dict = {}) -> None:
        with handler.uow as uow:
            if not (existing_epic := uow.tasks.get_by_id(
                    models.epic.Epic, cmd.id)):
                raise exceptions.EntityNotFound(f"Epic {cmd.id} is not found")
            if not uow.tasks.get_by_id(models.sprint.Sprint, cmd.sprint_id):
                raise exceptions.EntityNotFound(
                    f"Sprint {cmd.sprint_id} is not found")
            for epic_task in existing_epic.tasks:
                task = epic_task.tasks
                if task.status.name not in ("DONE", "DELETED"):
                    TaskCommandHandlers.add(
                        _commands.AddTask(id=task.id,
                                          entity_type="sprint",
                                          entity_id=cmd.sprint_id), handler)

    @register(cmd=_commands.ListEpic)
    def list(cmd: _commands.ListEpic,
             handler: Handler,
             context: dict = {}) -> None:
        with handler.uow as uow:
            if epics := uow.tasks.list(models.epic.Epic):
                handler.printer.console.print_composite(
                    epics, uow.tasks,
                    printer.PrintOptions.from_kwargs(**context), "epic")


class EpicEventHandlers:
    ...


class StoryCommandHandlers:

    @register(cmd=_commands.CreateStory)
    def create(cmd: _commands.CreateStory,
               handler: Handler,
               context: dict = {}):
        if not cmd.name:
            cmd, context = templates.create_command_from_editor(
                models.story.Story, type(cmd))
        with handler.uow as uow:
            cmd = convert_project(cmd, handler)
            new_story = models.story.Story(**asdict(cmd))
            uow.tasks.add(new_story)
            uow.commit()
            handler.printer.console.print_new_object(new_story)

    @register(cmd=_commands.CompleteStory)
    def complete(cmd: _commands.CompleteStory,
                 handler: Handler,
                 context: dict = {}) -> None:
        with handler.uow as uow:
            uow.tasks.update(models.project.Story, cmd.id,
                             {"status": "COMPLETED"})
            uow.published_events.append(events.StoryCompleted(cmd.id))
            if comment := cmd.comment:
                uow.published_events.append(
                    events.StoryCommented(id=cmd.id, text=comment))
            uow.commit()
        handler.publisher.publish("Topic", events.StoryCompleted(cmd.id))

    @register(cmd=_commands.DeleteStory)
    def delete(cmd: _commands.DeleteStory,
               handler: Handler,
               context: dict = {}) -> None:
        with handler.uow as uow:
            uow.tasks.update(models.story.Story, cmd.id, {"status": "DELETED"})
            uow.published_events.append(events.StoryDeleted(cmd.id))
            if comment := cmd.comment:
                uow.published_events.append(
                    events.StoryCommented(id=cmd.id, text=comment))
            uow.commit()
        handler.publisher.publish("Topic", events.StoryDeleted(cmd.id))

    @register(cmd=_commands.CommentStory)
    def comment(cmd: _commands.CommentStory,
                handler: Handler,
                context: dict = {}) -> None:
        with handler.uow as uow:
            uow.tasks.add(
                models.commentary.StoryCommentary(id=cmd.id, text=cmd.text))
            uow.commit()

    @register(cmd=_commands.AddStory)
    def add(cmd: _commands.AddStory,
            handler: Handler,
            context: dict = {}) -> None:
        with handler.uow as uow:
            if not (existing_story := uow.tasks.get_by_id(
                    models.story.Story, cmd.id)):
                raise exceptions.EntityNotFound(f"Story {cmd.id} is not found")
            if not uow.tasks.get_by_id(models.sprint.Sprint, cmd.sprint_id):
                raise exceptions.EntityNotFound(
                    f"Sprint {cmd.sprint_id} is not found")
            for story_task in existing_story.tasks:
                task = story_task.tasks
                if task.status.name not in ("DONE", "DELETED"):
                    TaskCommandHandlers.add(
                        _commands.AddTask(id=task.id,
                                          entity_type="sprint",
                                          entity_id=cmd.sprint_id), handler)


class WorkspaceCommandHandlers:

    @register(cmd=_commands.CreateWorkspace)
    def create(cmd: _commands.CreateWorkspace,
               handler: Handler,
               context: dict = {}) -> None:
        if not cmd:
            cmd, context = templates.create_command_from_editor(
                models.sprint.Sprint, type(cmd))
        with handler.uow as uow:
            if not uow.tasks.get(models.workspace.Workspace, cmd.name):
                new_workspace = models.workspace.Workspace(**asdict(cmd))
                uow.tasks.add(new_workspace)
                uow.commit()
                handler.printer.console.print_new_object(new_workspace)
            else:
                logging.warning(f"Workspace {cmd.name} already exists")


class TagCommandHandlers:

    @register(cmd=_commands.ListTag)
    def list(cmd: _commands.ListTag,
             handler: Handler,
             context: dict = {}) -> None:
        with handler.uow as uow:
            if tags := uow.tasks.list(models.tag.BaseTag):
                handler.printer.console.print_tag(tags)


class UserCommandHandlers:

    @register(cmd=_commands.ListUser)
    def list(cmd: _commands.ListUser,
             handler: Handler,
             context: dict = {}) -> None:
        with handler.uow as uow:
            if users := uow.tasks.list(models.user.User):
                handler.printer.console.print_user(users)


def convert_project(cmd: _commands.Command,
                    handler: Handler,
                    context: dict = {}) -> Type[_commands.Command]:
    if not (project_name := cmd.project):
        cmd.project = None
        return cmd
    if project_name.isnumeric():
        cmd.project = int(project_name)
        return cmd
    if not (existing_project := handler.uow.tasks.get(models.project.Project,
                                                      project_name)):
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
            cmd=_commands.CreateProject(name=project_name), handler=handler)
        cmd.project = project_id
    else:
        cmd.project = int(existing_project.id)
    return cmd


def convert_workspace(cmd: _commands.Command,
                      handler: Handler,
                      context: dict = {}) -> Type[_commands.Command]:
    if not (workspace := cmd.workspace):
        cmd.workspace = 1
        return cmd
    if workspace.isnumeric():
        cmd.workspace = int(workspace)
        return cmd
    if not (existing_workspace := handler.uow.tasks.get(
            models.workspace.Workspace, workspace)):
        print(f"Creating new workspace: {workspace}. "
              "Do you want to continue (Y/n)?")
        answer = input()
        while answer.lower() != "y":
            print("Provide workspace name: ")
            project_name = input()
            print(f"Creating new workspace: {workspace}. "
                  "Do you want to continue (Y/n)?")
            answer = input()
        workspace_id = WorkspaceCommandHandlers.create(
            cmd=_commands.CreateWorkspace(name=workspace), handler=handler)
        cmd.workspace = workspace_id
    else:
        cmd.workspace = int(existing_workspace.id)
    return cmd
