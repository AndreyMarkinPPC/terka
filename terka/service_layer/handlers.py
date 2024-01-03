from typing import Type
import asana as asn
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
import functools
import logging
import os
from rich.prompt import Confirm, Prompt

from terka import utils
from terka.adapters import publisher, printer
from terka.domain import commands, events, entities
from terka.domain.external_connectors import asana
from terka.service_layer import exceptions, messagebus, templates, unit_of_work, views
from terka.utils import format_command, format_entity

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

    def __init__(self,
                 uow: unit_of_work.AbstractUnitOfWork,
                 publisher: publisher.BasePublisher | None = None,
                 printer: printer.Printer = printer.Printer(),
                 config: dict | None = None) -> None:
        self.uow = uow
        self.publisher = publisher
        self.printer = printer
        self.config = config


class CommandHandler:

    def __init__(self, bus: messagebus.MessageBus) -> None:
        self.bus = bus

    def execute(self, command: str, entity: str,
                task_dict: dict | list[dict]) -> None:
        if isinstance(task_dict, list):
            for _task_dict in task_dict:
                self.execute(command, entity, _task_dict)
        else:
            command = format_command(command)
            entity = format_entity(entity)
            _command = f"{command.capitalize()}{entity.capitalize()}"
            try:
                self.bus.handle(getattr(commands,
                                        _command).from_kwargs(**task_dict),
                                context=task_dict)
            except AttributeError as e:
                print(e)
                raise exceptions.TerkaCommandException(
                    f"Unknown command: `terka {command} {entity}`")


class SprintCommandHandlers:

    @register(cmd=commands.CreateSprint)
    def create(cmd: commands.CreateSprint,
               handler: Handler,
               context: dict = {}) -> int:
        if not cmd:
            cmd, context = templates.create_command_from_editor(
                entities.sprint.Sprint, type(cmd))
        with handler.uow as uow:
            # TODO: Add code for checking existing sprints
            new_sprint = entities.sprint.Sprint(**asdict(cmd))
            uow.tasks.add(new_sprint)
            uow.commit()
            new_sprint_id = new_sprint.id
            handler.printer.console.print_new_object(new_sprint)
            return new_sprint_id

    @register(cmd=commands.StartSprint)
    def start(cmd: commands.StartSprint,
              handler: Handler,
              context: dict = {}) -> None:
        with handler.uow as uow:
            if not (existing_sprint := uow.tasks.get_by_id(
                    entities.sprint.Sprint, cmd.id)):
                raise exceptions.EntityNotFound(
                    f"Sprint id {cmd.id} is not found")
            if existing_sprint.status.name == "ACTIVE":
                raise exceptions.TerkaSprintActive("Sprint already started")
            if existing_sprint.status.name == "COMPLETED":
                raise exceptions.TerkaSprintCompleted(
                    "Cannot start completed sprint")
            uow.tasks.update(entities.sprint.Sprint, cmd.id,
                             {"status": "ACTIVE"})
            for sprint_task in existing_sprint.tasks:
                task = sprint_task.tasks
                task_params = {}
                if task.status.name == "BACKLOG":
                    task_params.update({"status": "TODO"})
                if not task.due_date or task.due_date > existing_sprint.end_date:
                    task_params.update({"due_date": existing_sprint.end_date})
                if task_params:
                    task_params["id"] = task.id
                    uow.published_events.append(
                        commands.UpdateTask(**task_params))
                # FIXME: ask-input should be provided via CLI
                if sprint_task.story_points == 0 and context.get("ask-input"):
                    story_points = input(
                        "Please enter story points estimation "
                        f"for task <{task.id}>: {task.name}: ")
                    try:
                        story_points = float(story_points)
                        # TODO: Should call command (AddTask with arguments story_points)
                        uow.published_events.append(
                            events.SprintTaskStoryPointAssigned(
                                sprint_task.id, story_points))
                    except ValueError:
                        print(
                            "[red]Provide number when specifying story points[/red]"
                        )
            uow.commit()
            logging.debug(f"Sprint started, context: {cmd}")

    @register(cmd=commands.CompleteSprint)
    def complete(cmd: commands.CompleteSprint,
                 handler: Handler,
                 context: dict = {}) -> None:
        with handler.uow as uow:
            if not (existing_sprint := uow.tasks.get_by_id(
                    entities.sprint.Sprint, cmd.id)):
                raise exceptions.EntityNotFound(
                    f"Sprint id {cmd.id} is not found")
            uow.tasks.update(entities.sprint.Sprint, cmd.id,
                             {"status": "COMPLETED"})
            for sprint_task in existing_sprint.tasks:
                task = sprint_task.tasks
                task_params = {}
                if task.status.name == "TODO":
                    task_params.update({"status": "BACKLOG"})
                if task.due_date:
                    task_params.update({"due_date": None})
                if task_params:
                    task_params["id"] = task.id
                    uow.published_events.append(
                        commands.UpdateTask(**task_params))
            uow.commit()
            logging.debug(f"Sprint completed, context: {cmd}")
        handler.publisher.publish("Topic", events.SprintCompleted(cmd.id))

    @register(cmd=commands.ShowSprint)
    def show(cmd: commands.ShowSprint,
             handler: Handler,
             context: dict = {}) -> None:
        with handler.uow as uow:
            if not (existing_sprint := uow.tasks.get_by_id(
                    entities.sprint.Sprint, cmd.id)):
                raise exceptions.EntityNotFound(
                    f"Sprint id {cmd.id} is not found")
            handler.printer.tui.print_sprint(existing_sprint, handler)

    @register(cmd=commands.ListSprint)
    def list(cmd: commands.ListSprint,
             handler: Handler,
             context: dict = {}) -> None:
        with handler.uow as uow:
            if sprints := uow.tasks.list(entities.sprint.Sprint):
                handler.printer.console.print_sprint(
                    sprints, printer.PrintOptions.from_kwargs(**context))


class SprintEventHandlers:

    def assign_story_points(event: events.SprintTaskStoryPointAssigned,
                            handler: Handler,
                            context: dict = {}) -> None:
        with handler.uow as uow:
            uow.tasks.update(entities.sprint.SprintTask, event.id,
                             {"story_points": event.story_points})
            uow.commit()
            logging.debug(f"Story point assigned, context: {event}")


class TaskCommandHandlers:

    @register(cmd=commands.CreateTask)
    def create(cmd: commands.CreateTask,
               handler: Handler,
               context: dict = {}) -> int:
        if not cmd.name:
            cmd, context = templates.create_command_from_editor(
                entities.task.Task, commands.CreateTask)
        with handler.uow as uow:
            cmd.inject(handler.config)
            cmd = convert_project(cmd, handler)
            cmd = convert_user(cmd, handler)
            new_task = entities.task.Task(**asdict(cmd))
            uow.tasks.add(new_task)
            uow.flush()
            new_task_id = new_task.id
            task_created_event = events.TaskCreated(new_task.id)
            uow.published_events.append(task_created_event)
            uow.commit()
            TaskCommandHandlers._process_extra_args(new_task.id, context, uow)
            handler.publisher.publish("Topic", task_created_event)
            handler.printer.console.print_new_object(new_task)
            return new_task_id

    @register(cmd=commands.UpdateTask)
    def update(cmd: commands.UpdateTask,
               handler: Handler,
               context: dict = {}) -> None:
        with handler.uow as uow:
            if not (existing_task := uow.tasks.get_by_id(
                    entities.task.Task, cmd.id)):
                raise exceptions.EntityNotFound(
                    f"Task id {cmd.id} is not found")
            if not cmd:
                cmd, context = templates.create_command_from_editor(
                    existing_task, commands.UpdateTask)
                cmd.id = existing_task.id
            cmd = convert_project(cmd, handler)
            for f in cmd.__dataclass_fields__:
                if f == "id":
                    continue
                new_value = getattr(cmd, f)
                old_value = getattr(existing_task, f)
                if hasattr(old_value, "name"):
                    old_value = old_value.name
                if (f == "due_date" and new_value != old_value) or (
                        new_value and new_value != old_value):
                    uow.published_events.append(
                        events.TaskUpdated(cmd.id,
                                           type=f.upper(),
                                           old_value=old_value,
                                           new_value=new_value))
            update_dict = cmd.get_only_set_attributes()
            if status := update_dict.get("status"):
                update_dict["status"] = entities.task.TaskStatus[status]
            if priority := update_dict.get("priority"):
                update_dict["priority"] = entities.task.TaskPriority[priority]
            uow.tasks.update(entities.task.Task, cmd.id, update_dict)
            uow.commit()
            TaskCommandHandlers._process_extra_args(cmd.id, context, uow)

    @register(cmd=commands.CollaborateTask)
    def collaborate(cmd: commands.CollaborateTask,
                    handler: Handler,
                    context: dict = {}) -> None:
        with handler.uow as uow:
            if not (existing_task := uow.tasks.get_by_id(
                    entities.task.Task, cmd.id)):
                raise exceptions.EntityNotFound(
                    f"Task id {cmd.id} is not found")
            if not (existing_user := uow.tasks.list(
                    entities.user.User, {"name": cmd.collaborator})):
                new_user = entities.user.User(name=cmd.collaborator)
                uow.tasks.add(new_user)
                uow.flush()
                user_id = new_user.id
            else:
                user_id = existing_user[0].id
            if not uow.tasks.list(entities.collaborator.TaskCollaborator, {
                    "task": cmd.id,
                    "collaborator": user_id
            }):
                uow.tasks.add(
                    entities.collaborator.TaskCollaborator(
                        id=cmd.id, collaborator_id=user_id))
                uow.commit()

    @register(cmd=commands.AddTask)
    def add(cmd: commands.AddTask,
            handler: Handler,
            context: dict = {}) -> None:

        if (sprint := cmd.sprint) and (story_points := cmd.story_points):
            updated_context = {"entity_type": "sprint", "entity_id": sprint}
            TaskCommandHandlers._add(
                commands.AddTask(cmd.id,
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
                            commands.AddTask(cmd.id, sprint=field_value),
                            handler, updated_context)
                    if field == "epic":
                        TaskCommandHandlers._add(
                            commands.AddTask(cmd.id, epic=field_value),
                            handler, updated_context)
                    if field == "story":
                        TaskCommandHandlers._add(
                            commands.AddTask(cmd.id, story=field_value),
                            handler, updated_context)

    def _add(cmd: commands.AddTask, handler: Handler, context) -> None:
        entity_name, entity_id = context["entity_type"], context["entity_id"]
        entity_module = getattr(entities, entity_name)
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
                    if existing_entity.status == entities.sprint.SprintStatus.COMPLETED:
                        raise exceptions.TerkaSprintCompleted(
                            f"Sprint {entity_id} is completed")
                    if existing_task := uow.tasks.get_by_id(
                            entities.task.Task, cmd.id):
                        task_params = {}
                        if existing_task.status.name == "BACKLOG":
                            task_params.update({"status": "TODO"})
                        if (not existing_task.due_date
                                or existing_task.due_date >
                                existing_entity.end_date
                                or existing_task.due_date <
                                existing_entity.start_date):
                            task_params.update(
                                {"due_date": existing_entity.end_date})
                        if task_params:
                            task_params["id"] = existing_task.id
                            uow.published_events.append(
                                commands.UpdateTask(**task_params))

    @register(cmd=commands.AssignTask)
    def assign(cmd: commands.AssignTask,
               handler: Handler,
               context: dict = {}) -> None:
        ...

    @register(cmd=commands.CompleteTask)
    def complete(cmd: commands.CompleteTask,
                 handler: Handler,
                 context: dict = {}) -> None:
        with handler.uow as uow:
            if not (existing_task := uow.tasks.get_by_id(
                    entities.task.Task, cmd.id)):
                raise exceptions.EntityNotFound(
                    f"Task id {cmd.id} is not found")
            task_completed_event = events.TaskUpdated(
                task=cmd.id,
                type="STATUS",
                old_value=existing_task.status.name,
                new_value="DONE")
            uow.published_events.append(task_completed_event)
            uow.tasks.update(entities.task.Task, cmd.id,
                             {"status": entities.task.TaskStatus.DONE})
            TaskCommandHandlers._process_extra_args(cmd.id, context, uow)
            uow.commit()
            handler.publisher.publish("Topic", task_completed_event)

    @register(cmd=commands.DeleteTask)
    def delete(cmd: commands.DeleteTask,
               handler: Handler,
               context: dict = {}) -> None:

        updated_context = {}
        for field in cmd.__dataclass_fields__:
            if field == "id":
                continue
            field_value = getattr(cmd, field)

            if field_value := getattr(cmd, field):
                updated_context = {
                    "entity_type": field,
                    "entity_id": field_value
                }
                if field == "sprint":
                    TaskCommandHandlers._delete(
                        commands.DeleteTask(cmd.id, sprint=field_value),
                        handler, updated_context)
                if field == "epic":
                    TaskCommandHandlers._delete(
                        commands.DeleteTask(cmd.id, epic=field_value), handler,
                        updated_context)
                if field == "story":
                    TaskCommandHandlers._delete(
                        commands.DeleteTask(cmd.id, story=field_value),
                        handler, updated_context)
        if not updated_context:
            TaskCommandHandlers._delete(cmd, handler, context)

    def _delete(cmd: commands.DeleteTask,
                handler: Handler,
                context: dict = {}) -> None:
        with handler.uow as uow:
            if not (existing_task := uow.tasks.get_by_id(
                    entities.task.Task, cmd.id)):
                raise exceptions.EntityNotFound(
                    f"Task id {cmd.id} is not found")
            if "entity_type" in context and "entity_id" in context:
                entity_name, entity_id = context["entity_type"], context[
                    "entity_id"]
                entity_module = getattr(entities, entity_name)
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
                    uow.tasks.delete(entity_task_type,
                                     existing_entity_task[0].id)
                    uow.commit()
                    logging.debug(
                        f"Task deleted from {entity_name.capitalize()} "
                        f"{entity_id}, context {cmd}")
                    if entity_name == "sprint":
                        if existing_task := uow.tasks.get_by_id(
                                entities.task.Task, cmd.id):
                            task_params = {}
                            if existing_task.status.name == "TODO":
                                task_params.update({"status": "BACKLOG"})
                            task_params.update({"due_date": None})
                            if task_params:
                                # FIXME: Duplication
                                task_params["id"] = existing_task.id
                                uow.published_events.append(
                                    commands.UpdateTask(**task_params))
            else:
                task_deleted_event = events.TaskUpdated(
                    task=cmd.id,
                    type="STATUS",
                    old_value=existing_task.status.name,
                    new_value="DELETED")
                uow.published_events.append(task_deleted_event)
                uow.tasks.update(entities.task.Task, cmd.id,
                                 {"status": entities.task.TaskStatus.DELETED})
                uow.published_events.append(task_deleted_event)
            TaskCommandHandlers._process_extra_args(cmd.id, context, uow)
            uow.commit()
        handler.publisher.publish("Topic", events.TaskCompleted(cmd.id))

    @register(cmd=commands.CommentTask)
    def comment(cmd: commands.CommentTask,
                handler: Handler,
                context: dict = {}) -> None:
        with handler.uow as uow:
            if text := cmd.text.strip():
                uow.tasks.add(
                    entities.commentary.TaskCommentary(id=cmd.id, text=text))
                uow.tasks.update(entities.task.Task, cmd.id,
                                 {"modification_date": datetime.now()})
                uow.commit()

    @register(cmd=commands.TrackTask)
    def track(cmd: commands.TrackTask,
              handler: Handler,
              context: dict = {}) -> None:
        with handler.uow as uow:
            if not (existing_task := uow.tasks.get_by_id(
                    entities.task.Task, cmd.id)):
                raise exceptions.EntityNotFound(
                    f"Task id {cmd.id} is not found")
            uow.tasks.add(
                entities.time_tracker.TimeTrackerEntry(
                    task=cmd.id, time_spent_minutes=cmd.hours))
            uow.commit()

    @register(cmd=commands.TagTask)
    def tag(cmd: commands.TagTask,
            handler: Handler,
            context: dict = {}) -> None:
        with handler.uow as uow:
            if not (existing_task := uow.tasks.get_by_id(
                    entities.task.Task, cmd.id)):
                raise exceptions.EntityNotFound(
                    f"Task id {cmd.id} is not found")
            if not (existing_tag := uow.tasks.list(entities.tag.BaseTag,
                                                   {"text": cmd.tag})):
                new_tag = entities.tag.BaseTag(text=cmd.tag)
                uow.tasks.add(new_tag)
                uow.flush()
                tag_id = new_tag.id
            else:
                tag_id = existing_tag[0].id
            if not uow.tasks.list(entities.tag.TaskTag, {
                    "task": cmd.id,
                    "tag": tag_id
            }):
                uow.tasks.add(entities.tag.TaskTag(id=cmd.id, tag_id=tag_id))
                uow.commit()

    def _process_extra_args(id, context, uow):
        if tags := context.get("tags"):
            for tag in tags.split(","):
                uow.published_events.append(commands.TagTask(id=id, tag=tag))
        if collaborators := context.get("collaborators"):
            for collaborator_name in collaborators.split(","):
                uow.published_events.append(
                    commands.CollaborateTask(id=id,
                                             collaborator=collaborator_name))
        if sprints := context.get("sprint"):
            for sprint in sprints.split(","):
                uow.published_events.append(
                    commands.AddTask(id=id, sprint=sprint))
        if epics := context.get("epic"):
            for epic in epics.split(","):
                uow.published_events.append(commands.AddTask(id=id, epic=epic))
        if stories := context.get("story"):
            for story in stories.split(","):
                uow.published_events.append(
                    commands.AddTask(id=id, story=story))
        if comment := context.get("comment"):
            uow.published_events.append(
                commands.CommentTask(id=id, text=comment))
        if hours := context.get("time_spent"):
            uow.published_events.append(commands.TrackTask(id=id, hours=hours))

    @register(cmd=commands.ListTask)
    def list(cmd: commands.ListTask,
             handler: Handler,
             context: dict = {}) -> None:
        filter_options = utils.FilterOptions.from_kwargs(**context)
        with handler.uow as uow:
            if filter_options:
                tasks = uow.tasks.get_by_conditions(
                    entities.task.Task,
                    filter_options.get_only_set_attributes())
            else:
                tasks = uow.tasks.list(entities.task.Task)
            if tasks:
                print_options = printer.PrintOptions.from_kwargs(**context)
                handler.printer.console.print_task(tasks, print_options)


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
            task_event = entities.event_history.TaskEvent(task=event.id,
                                                          type="STATUS",
                                                          old_value="",
                                                          new_value="DONE")
            uow.tasks.add(task_event)
            uow.tasks.update(entities.task.Task, event.id,
                             {"modification_date": datetime.now()})
            uow.commit()

    @register(event=events.TaskUpdated)
    def updated(event: events.TaskUpdated,
                handler: Handler,
                context: dict = {}) -> None:
        with handler.uow as uow:
            task_event = entities.event_history.TaskEvent(**asdict(event))
            uow.tasks.add(task_event)
            uow.tasks.update(entities.task.Task, event.task,
                             {"modification_date": datetime.now()})
            uow.commit()
            logging.debug(f"Task updated, context {event}")

    @register(event=events.TaskDeleted)
    def deleted(event: events.TaskDeleted,
                handler: Handler,
                context: dict = {}) -> None:
        with handler.uow as uow:
            task_event = entities.event_history.TaskEvent(task_id=event.id,
                                                          type="STATUS",
                                                          old_value="",
                                                          new_value="DELETED")
            uow.tasks.add(task_event)
            uow.tasks.update(entities.task.Task, event.d,
                             {"modification_date": datetime.now()})
            uow.commit()

    @register(event=events.TaskCommentAdded)
    def comment_added(event: events.TaskCommentAdded,
                      handler: Handler,
                      context: dict = {}) -> None:
        TaskCommandHandlers.comment(cmd=commands.CommentTask(**asdict(event)),
                                    handler=handler,
                                    context=context)
        with handler.uow as uow:
            uow.tasks.update(entities.task.Task, event.id,
                             {"modification_date": datetime.now()})

    @register(event=events.TaskCollaboratorAdded)
    def collaborator_added(event: events.TaskCollaboratorAdded,
                           handler: Handler,
                           context: dict = {}) -> None:
        TaskCommandHandlers.collaborate(
            cmd=commands.CollaborateTask(**asdict(event)),
            handler=handler,
            context=context)

    @register(event=events.TaskHoursSubmitted)
    def hours_submitted(event: events.TaskHoursSubmitted,
                        handler: Handler,
                        context: dict = {}) -> None:
        TaskCommandHandlers.track(cmd=commands.TrackTask(id=event.id,
                                                         hours=event.hours),
                                  handler=handler,
                                  context=context)

    @register(event=events.TaskAddedToEpic)
    def added_to_epic(event: events.TaskAddedToEpic,
                      handler: Handler,
                      context: dict = {}) -> None:
        TaskCommandHandlers.add(cmd=commands.AddTask(id=event.id,
                                                     epic=event.epic_id),
                                handler=handler,
                                context=context)

    @register(event=events.TaskAddedToSprint)
    def added_to_sprint(event: events.TaskAddedToSprint,
                        handler: Handler,
                        context: dict = {}) -> None:
        TaskCommandHandlers.add(cmd=commands.AddTask(id=event.id,
                                                     sprint=event.sprint_id),
                                handler=handler,
                                context=context)

    @register(event=events.TaskAddedToStory)
    def added_to_story(event: events.TaskAddedToStory,
                       handler: Handler,
                       context: dict = {}) -> None:
        TaskCommandHandlers.add(cmd=commands.AddTask(id=event.id,
                                                     story=event.story_id),
                                handler=handler,
                                context=context)

    @register(event=events.TaskSynced)
    def synced(event: events.TaskSynced,
               handler: Handler,
               context: dict = {}) -> None:
        with handler.uow as uow:
            if synced_task := uow.tasks.get_by_conditions(
                    asana.AsanaTask, {"asana_task_id": event.asana_task_id}):
                uow.tasks.update(asana.AsanaTask, synced_task[0].id,
                                 {"sync_date": event.sync_date})
            else:
                uow.tasks.add(asana.AsanaTask(**asdict(event)))
            uow.commit()


class ProjectCommandHandlers:

    @register(cmd=commands.CreateProject)
    def create(cmd: commands.CreateProject,
               handler: Handler,
               context: dict = {}) -> None:
        if not cmd.name:
            cmd, context = templates.create_command_from_editor(
                entities.project.Project, commands.CreateProject)
        project_id = None
        with handler.uow as uow:
            if not (existing_project := uow.tasks.get(entities.project.Project,
                                                      cmd.name)):
                cmd = convert_workspace(cmd, handler)
                new_project = entities.project.Project(**asdict(cmd))
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

    @register(cmd=commands.UpdateProject)
    def update(cmd: commands.UpdateProject,
               handler: Handler,
               context: dict = {}) -> None:
        with handler.uow as uow:
            project = ProjectCommandHandlers._validate_project(cmd.id, uow)
            if not cmd.name:
                cmd, context = templates.create_command_from_editor(
                    project, commands.UpdateProject)
                cmd.id = project.id
            uow.tasks.update(entities.project.Project, project.id,
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

    @register(cmd=commands.CompleteProject)
    def complete(cmd: commands.CompleteProject,
                 handler: Handler,
                 context: dict = {}) -> None:
        with handler.uow as uow:
            project = ProjectCommandHandlers._validate_project(cmd.id, uow)
            uow.tasks.update(entities.project.Project, project.id,
                             {"status": "COMPLETED"})
            uow.published_events.append(events.ProjectCompleted(project.id))
            # TODO: implement _process_extra_args for projects
            uow.commit()
            handler.publisher.publish("Topic",
                                      events.ProjectCompleted(project.id))

    @register(cmd=commands.DeleteProject)
    def delete(cmd: commands.DeleteProject,
               handler: Handler,
               context: dict = {}) -> None:
        with handler.uow as uow:
            project = ProjectCommandHandlers._validate_project(cmd.id, uow)
            uow.tasks.update(entities.project.Project, project.id,
                             {"status": "DELETED"})
            uow.published_events.append(events.ProjectDeleted(project.id))
            if comment := cmd.comment:
                uow.published_events.append(
                    events.ProjectCommented(id=project.id, text=comment))
            uow.commit()
            handler.publisher.publish("Topic",
                                      events.ProjectDeleted(project.id))

    @register(cmd=commands.CommentProject)
    def comment(cmd: commands.CommentProject,
                handler: Handler,
                context: dict = {}) -> None:
        with handler.uow as uow:
            project = ProjectCommandHandlers._validate_project(cmd.id, uow)
            uow.tasks.add(
                entities.commentary.ProjectCommentary(id=project.id,
                                                      text=cmd.text))
            uow.commit()

    @register(cmd=commands.TagProject)
    def tag(cmd: commands.TagProject,
            handler: Handler,
            context: dict = {}) -> None:
        with handler.uow as uow:
            project = ProjectCommandHandlers._validate_project(cmd.id, uow)
            if not (existing_tag := uow.tasks.list(entities.tag.BaseTag,
                                                   {"text": cmd.tag})):
                new_tag = entities.tag.BaseTag(text=cmd.tag)
                uow.tasks.add(new_tag)
                uow.flush()
                tag_id = new_tag.id
            else:
                tag_id = existing_tag[0].id
            if not uow.tasks.list(entities.tag.ProjectTag, {
                    "project": project.id,
                    "tag": tag_id
            }):
                uow.tasks.add(
                    entities.tag.ProjectTag(id=project.id, tag_id=tag_id))
                uow.commit()

    @register(cmd=commands.ShowProject)
    def show(cmd: commands.ShowProject,
             handler: Handler,
             context: dict = {}) -> None:
        with handler.uow as uow:
            project = ProjectCommandHandlers._validate_project(cmd.id, uow)
            handler.printer.tui.print_project(project, handler)

    @register(cmd=commands.ListProject)
    def list(cmd: commands.ListProject,
             handler: Handler,
             context: dict = {}) -> None:
        with handler.uow as uow:
            filter_options = utils.FilterOptions.from_kwargs(**context)
            with handler.uow as uow:
                if filter_options:
                    projects = uow.tasks.get_by_conditions(
                        entities.project.Project,
                        filter_options.get_only_set_attributes())
                else:
                    projects = uow.tasks.list(entities.project.Project)
                handler.printer.console.print_project(
                    projects, printer.PrintOptions.from_kwargs(**context))

    @register(cmd=commands.SyncProject)
    def sync(cmd: commands.SyncProject,
             handler: Handler,
             context: dict = {}) -> None:
        with handler.uow as uow:
            if cmd.id:
                project = ProjectCommandHandlers._validate_project(cmd.id, uow)
                ProjectCommandHandlers._sync_project(uow, project)
            else:
                projects = uow.tasks.list(entities.project.Project)
                for project in projects:
                    self._sync_project(uow, project)

    def _validate_project(id: str | int, uow) -> entities.project.Project:
        if id.isnumeric():
            if not (existing_project := uow.tasks.get_by_id(
                    entities.project.Project, id)):
                raise exceptions.EntityNotFound(
                    f"Project id {id} is not found")
        else:
            if not (existing_project := uow.tasks.get(entities.project.Project,
                                                      id)):

                raise exceptions.EntityNotFound(
                    f"Project id {id} is not found")
        return existing_project

    def _sync_project(uow, project: entities.project.Project):
        asana_project = uow.tasks.get_by_id(asana.AsanaProject, project.id)
        if not asana_project:
            return
        asana_project_id = asana_project.asana_project_id
        if last_sync_date := asana_project.sync_date:
            tasks = [
                task for task in project.tasks
                if task.creation_date > last_sync_date or (
                    task.modification_date
                    and task.modification_date > last_sync_date)
            ]
        else:
            tasks = project.tasks
        if not tasks:
            return
        project_sync_date = datetime.now()
        synced_tasks = views.external_connectors_asana_tasks(
            uow.repo.session, project.id)
        # TODO: Store default assign user and token in config
        configuration = asn.Configuration()
        configuration.access_token = os.getenv("ASANA_PERSONAL_ACCESS_TOKEN")
        asana_client = asn.ApiClient(configuration)
        asana_migrator = asana.AsanaMigrator(asana_client)
        asana_migrator.load_task_statuses(asana_project_id)
        for i, task in enumerate(tasks):
            if not task.sync:
                continue
            sync_info = synced_tasks.get(task.id)
            if asana_task_id := asana_migrator.migrate_task(
                    asana_project_id, task, sync_info):
                uow.published_events.append(
                    events.TaskSynced(id=task.id,
                                      project=project.id,
                                      asana_task_id=asana_task_id,
                                      sync_date=datetime.now()))
        uow.published_events.append(
            events.ProjectSynced(project.id, asana_project_id,
                                 project_sync_date))


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
            cmd=commands.CommentProject(**asdict(event)), handler=handler)

    @register(event=events.ProjectSynced)
    def synced(event: events.ProjectSynced,
               handler: Handler,
               context: dict = {}) -> None:
        with handler.uow as uow:
            if synced_project := uow.tasks.get_by_conditions(
                    asana.AsanaProject,
                {"asana_project_id": event.asana_project_id}):
                uow.tasks.update(asana.AsanaProject, synced_project[0].id,
                                 {"sync_date": event.sync_date})
            else:
                uow.tasks.add(asana.AsanaProject(**asdict(event)))
            uow.commit()


class EpicCommandHandlers:

    @register(cmd=commands.CreateEpic)
    def create(cmd: commands.CreateEpic, handler: Handler, context: dict = {}):
        if not cmd.name:
            cmd, context = templates.create_command_from_editor(
                entities.epic.Epic, type(cmd))
        with handler.uow as uow:
            cmd = convert_project(cmd, handler)
            new_epic = entities.epic.Epic(**asdict(cmd))
            uow.tasks.add(new_epic)
            uow.commit()
            new_epic_id = new_epic.id
            handler.printer.console.print_new_object(new_epic)
            return new_epic_id

    @register(cmd=commands.CompleteEpic)
    def complete(cmd: commands.CompleteEpic,
                 handler: Handler,
                 context: dict = {}) -> None:
        with handler.uow as uow:
            uow.tasks.update(entities.project.Epic, cmd.id,
                             {"status": "COMPLETED"})
            uow.published_events.append(events.EpicCompleted(cmd.id))
            if comment := cmd.comment:
                uow.published_events.append(
                    events.EpicCommented(id=cmd.id, text=comment))
            uow.commit()
        handler.publisher.publish("Topic", events.EpicCompleted(cmd.id))

    @register(cmd=commands.DeleteEpic)
    def delete(cmd: commands.DeleteEpic,
               handler: Handler,
               context: dict = {}) -> None:
        with handler.uow as uow:
            uow.tasks.update(entities.epic.Epic, cmd.id, {"status": "DELETED"})
            uow.published_events.append(events.EpicDeleted(cmd.id))
            if comment := cmd.comment:
                uow.published_events.append(
                    events.EpicCommented(id=cmd.id, text=comment))
            uow.commit()
        handler.publisher.publish("Topic", events.EpicDeleted(cmd.id))

    @register(cmd=commands.CommentEpic)
    def comment(cmd: commands.CommentEpic,
                handler: Handler,
                context: dict = {}) -> None:
        with handler.uow as uow:
            uow.tasks.add(
                entities.commentary.EpicCommentary(id=cmd.id, text=cmd.text))
            uow.commit()

    @register(cmd=commands.AddEpic)
    def add(cmd: commands.AddEpic,
            handler: Handler,
            context: dict = {}) -> None:
        with handler.uow as uow:
            if not (existing_epic := uow.tasks.get_by_id(
                    entities.epic.Epic, cmd.id)):
                raise exceptions.EntityNotFound(f"Epic {cmd.id} is not found")
            if not uow.tasks.get_by_id(entities.sprint.Sprint, cmd.sprint):
                raise exceptions.EntityNotFound(
                    f"Sprint {cmd.sprint} is not found")
            for epic_task in existing_epic.tasks:
                task = epic_task.tasks
                if task.status.name not in ("DONE", "DELETED"):
                    uow.published_events.append(
                        commands.AddTask(id=task.id, sprint=cmd.sprint))

    @register(cmd=commands.ListEpic)
    def list(cmd: commands.ListEpic,
             handler: Handler,
             context: dict = {}) -> None:
        with handler.uow as uow:
            if epics := uow.tasks.list(entities.epic.Epic):
                handler.printer.console.print_composite(
                    epics, uow.tasks,
                    printer.PrintOptions.from_kwargs(**context), "epic")


class EpicEventHandlers:
    ...


class StoryCommandHandlers:

    @register(cmd=commands.CreateStory)
    def create(cmd: commands.CreateStory,
               handler: Handler,
               context: dict = {}) -> int:
        if not cmd.name:
            cmd, context = templates.create_command_from_editor(
                entities.story.Story, type(cmd))
        with handler.uow as uow:
            cmd = convert_project(cmd, handler)
            new_story = entities.story.Story(**asdict(cmd))
            uow.tasks.add(new_story)
            uow.commit()
            new_story_id = new_story.id
            handler.printer.console.print_new_object(new_story)
            return new_story_id

    @register(cmd=commands.CompleteStory)
    def complete(cmd: commands.CompleteStory,
                 handler: Handler,
                 context: dict = {}) -> None:
        with handler.uow as uow:
            uow.tasks.update(entities.project.Story, cmd.id,
                             {"status": "COMPLETED"})
            uow.published_events.append(events.StoryCompleted(cmd.id))
            if comment := cmd.comment:
                uow.published_events.append(
                    events.StoryCommented(id=cmd.id, text=comment))
            uow.commit()
        handler.publisher.publish("Topic", events.StoryCompleted(cmd.id))

    @register(cmd=commands.DeleteStory)
    def delete(cmd: commands.DeleteStory,
               handler: Handler,
               context: dict = {}) -> None:
        with handler.uow as uow:
            uow.tasks.update(entities.story.Story, cmd.id,
                             {"status": "DELETED"})
            uow.published_events.append(events.StoryDeleted(cmd.id))
            if comment := cmd.comment:
                uow.published_events.append(
                    events.StoryCommented(id=cmd.id, text=comment))
            uow.commit()
        handler.publisher.publish("Topic", events.StoryDeleted(cmd.id))

    @register(cmd=commands.CommentStory)
    def comment(cmd: commands.CommentStory,
                handler: Handler,
                context: dict = {}) -> None:
        with handler.uow as uow:
            uow.tasks.add(
                entities.commentary.StoryCommentary(id=cmd.id, text=cmd.text))
            uow.commit()

    @register(cmd=commands.AddStory)
    def add(cmd: commands.AddStory,
            handler: Handler,
            context: dict = {}) -> None:
        with handler.uow as uow:
            if not (existing_story := uow.tasks.get_by_id(
                    entities.story.Story, cmd.id)):
                raise exceptions.EntityNotFound(f"Story {cmd.id} is not found")
            if not uow.tasks.get_by_id(entities.sprint.Sprint, cmd.sprint):
                raise exceptions.EntityNotFound(
                    f"Sprint {cmd.sprint} is not found")
            for story_task in existing_story.tasks:
                task = story_task.tasks
                if task.status.name not in ("DONE", "DELETED"):
                    uow.published_events.append(
                        commands.AddTask(id=task.id, sprint=cmd.sprint))


class WorkspaceCommandHandlers:

    @register(cmd=commands.CreateWorkspace)
    def create(cmd: commands.CreateWorkspace,
               handler: Handler,
               context: dict = {}) -> None:
        if not cmd:
            cmd, context = templates.create_command_from_editor(
                entities.sprint.Sprint, type(cmd))
        with handler.uow as uow:
            if not uow.tasks.get(entities.workspace.Workspace, cmd.name):
                new_workspace = entities.workspace.Workspace(**asdict(cmd))
                uow.tasks.add(new_workspace)
                uow.commit()
                handler.printer.console.print_new_object(new_workspace)
            else:
                logging.warning(f"Workspace {cmd.name} already exists")


class TagCommandHandlers:

    @register(cmd=commands.ListTag)
    def list(cmd: commands.ListTag,
             handler: Handler,
             context: dict = {}) -> None:
        with handler.uow as uow:
            if tags := uow.tasks.list(entities.tag.BaseTag):
                handler.printer.console.print_tag(tags)


class UserCommandHandlers:

    @register(cmd=commands.CreateUser)
    def create(cmd: commands.CreateUser,
               handler: Handler,
               context: dict = {}) -> None:
        with handler.uow as uow:
            if not uow.tasks.get(entities.user.User, cmd.name):
                new_user = entities.user.User(**asdict(cmd))
                uow.tasks.add(new_user)
                uow.commit()
                handler.printer.console.print_new_object(new_user)
            else:
                logging.warning(f"User {cmd.name} already exists")

    @register(cmd=commands.ListUser)
    def list(cmd: commands.ListUser,
             handler: Handler,
             context: dict = {}) -> None:
        with handler.uow as uow:
            if users := uow.tasks.list(entities.user.User):
                handler.printer.console.print_user(users)


class NoteCommandHandlers:

    @register(cmd=commands.ShowNote)
    def show(cmd: commands.ShowNote,
             handler: Handler,
             context: dict = {}) -> None:
        with handler.uow as uow:
            note_type = get_note_type(context)
            if note := uow.tasks.get_by_id(note_type, cmd.id):
                handler.printer.tui.show_note(note)


def convert_project(cmd: commands.Command,
                    handler: Handler,
                    context: dict = {}) -> Type[commands.Command]:
    if not (project_name := cmd.project):
        cmd.project = None
        return cmd
    if project_name.isnumeric():
        cmd.project = int(project_name)
        return cmd
    if not (existing_project := handler.uow.tasks.get(entities.project.Project,
                                                      project_name)):
        answer = Confirm.ask(
            f"Creating new project: {project_name}. Do you want to continue?")
        if not answer:
            project_name = Prompt.ask("Provide a project name: ")
            answer = Confirm.ask(
                f"Creating new project: {project_name}. Do you want to continue?"
            )
        project_id = ProjectCommandHandlers.create(
            cmd=commands.CreateProject(name=project_name),
            handler=handler,
            context=context)
        cmd.project = project_id
    else:
        cmd.project = int(existing_project.id)
    return cmd


def convert_workspace(cmd: commands.Command,
                      handler: Handler,
                      context: dict = {}) -> Type[commands.Command]:
    if not (workspace := cmd.workspace):
        # TODO: Get workspace from config
        cmd.workspace = 1
        return cmd
    try:
        cmd.workspace = int(workspace)
        return cmd
    except ValueError:
        ...
    if not (existing_workspace := handler.uow.tasks.get(
            entities.workspace.Workspace, workspace)):
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
            cmd=commands.CreateWorkspace(name=workspace),
            handler=handler,
            context=context)
        cmd.workspace = workspace_id
    else:
        cmd.workspace = int(existing_workspace.id)
    return cmd


def convert_user(cmd: commands.Command,
                 handler: Handler,
                 context: dict = {}) -> Type[commands.Command]:
    if not (created_by := cmd.created_by):
        return cmd
    try:
        cmd.created_by = int(created_by)
        return cmd
    except ValueError:
        ...
    if not (existing_user := handler.uow.tasks.get(entities.user.User,
                                                   created_by)):
        user_id = UserCommandHandlers.create(
            cmd=commands.CreateUser(name=created_by),
            handler=handler,
            context=context)
        cmd.created_by = user_id
    else:
        cmd.created_by = int(existing_user.id)
    return cmd


def get_note_type(kwargs: dict[str, str]) -> entities.note.BaseNote:
    if "project" in kwargs:
        return entities.note.ProjectNote
    if "task" in kwargs:
        return entities.note.TaskNote
    if "sprint" in kwargs:
        return entities.note.SprintNote
    if "story" in kwargs:
        return entities.note.StoryNote
    if "epic" in kwargs:
        return entities.note.EpicNote
