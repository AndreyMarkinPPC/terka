from typing import Any, Dict, List, Tuple

from dataclasses import dataclass
from datetime import datetime, date

import re
import sys, tempfile, os
from subprocess import run
import yaml

import logging
import rich
from rich.console import Console
from rich.table import Table

from src.domain.task import Task
from src.domain.project import Project
from src.domain.user import User
from src.domain.commentary import Commentary
from src.domain.event_history import Event

from src.service_layer import services
from src.adapters.repository import AbsRepository

logger = logging.getLogger(__name__)


@dataclass
class CurrentEntry:
    value: str
    type: str


def generate_message_template(current_entry: CurrentEntry, task: Task,
                              repo) -> str:
    project_name = services.lookup_project_name(task.project_id, repo)
    message_template = f"""
    # You are editing {current_entry.type}, enter below:
    {current_entry.value}
    ---
    Task context:
    id: {task.id}
    name: {task.name}
    description: {task.description}
    project: {project_name}
    """
    return re.sub("\n +", "\n", message_template.lstrip())


class BaseHandler:

    def __init__(self, successor):
        self._successor = successor

    def handle(self, entity):
        if self._successor:
            return self._successor.handle(entity)
        return None


class TaskHandler(BaseHandler):

    def handle(self, entity):
        if entity == "tasks":
            logger.debug("Handling task")
            return Task
        return super().handle(entity)


class ProjectHandler(BaseHandler):

    def handle(self, entity):
        if entity == "projects":
            logger.debug("Handling project")
            return Project
        return super().handle(entity)


class UserHandler(BaseHandler):

    def handle(self, entity):
        if entity == "users":
            logger.debug("Handling user")
            return User
        return super().handle(entity)


class CommentaryHandler(BaseHandler):

    def handle(self, entity):
        if entity == "commentaries":
            logger.debug("Handling commentary")
            return Commentary
        return super().handle(entity)


class CommandHandler:

    def __init__(self, repo: AbsRepository):
        self.repo = repo
        self.handler = self._init_handlers()
        self.home_dir = os.path.expanduser('~')

    def _init_handlers(self):
        handler_chain = BaseHandler(None)
        for handler in [
                TaskHandler, ProjectHandler, UserHandler, CommentaryHandler
        ]:
            new_handler = handler(handler_chain)
            handler_chain = new_handler
        return handler_chain

    def handle(self, entity):
        return self.handler.handle(entity)

    def execute(self, command, entity_type, kwargs: Dict[str, Any]):
        entity = self.handle(entity_type)
        session = self.repo.session
        if not command and not entity_type:
            print("Running terka in interactive mode")
            exit()
        elif not entity and command not in ("unfocus", "log"):
            raise ValueError(f"Entity *{entity_type}* is not a valid entity")
        if command == "list":
            if entity_type == "tasks" and "status" not in kwargs:
                kwargs["status"] = "BACKLOG,TODO,IN_PROGRESS,REVIEW"
            entities = self.repo.list(entity, kwargs)
            session.commit()
            print_entities(entities, entity_type, self.repo)
            logger.info("<list> %s", entity_type)
            return entities, None, None
        elif command == "log":
            console = Console()
            table = Table(box=rich.box.SIMPLE)
            with open(f"{self.home_dir}/.terka/terka.log", "r") as f:
                head = f.readlines()
            for column in ("date", "source", "level", "message"):
                table.add_column(column)
            tail = head[-10:]
            for row in tail[::-1]:
                info, message = row.split("] ")
                date, source, level = info.split("][")
                table.add_row(re.sub("\[", "", date), source, level, message)
            console.print(table)
        elif command == "focus":
            with open(f"{self.home_dir}/.terka/config.yaml",
                      "r",
                      encoding="utf-8") as f:
                config = yaml.safe_load(f)
            if entity_type == "tasks":
                config["task_id"] = kwargs["id"]
                if "project_name" in config.keys():
                    del config["project_name"]
            if entity_type == "projects":
                config["project_name"] = kwargs["id"]
                if "task_id" in config.keys():
                    del config["task_id"]
            with open(f"{self.home_dir}/.terka/config.yaml",
                      "w",
                      encoding="utf-8") as f:
                yaml.dump(config, f)
            logger.info("<focus> %s: %s", entity_type, "")
        elif command == "unfocus":
            with open(f"{self.home_dir}/.terka/config.yaml",
                      "r",
                      encoding="utf-8") as f:
                config = yaml.safe_load(f)
            if "task_id" in config.keys():
                del config["task_id"]
            if "project_name" in config.keys():
                del config["project_name"]
            with open(f"{self.home_dir}/.terka/config.yaml",
                      "w",
                      encoding="utf-8") as f:
                yaml.dump(config, f)
            logger.info("<unfocus> %s: %s", entity_type, "")
        elif command == "count":
            entities = self.repo.list(entity, kwargs)
            print(len(entities))
            logger.info("<count> tasks")
        elif command == "create":
            kwargs["created_by"] = services.lookup_user_id(
                # config.get("user"),
                "am",
                self.repo)
            if entity_type == "commentaries":
                kwargs["element_id"] = kwargs["task_id"]
                kwargs["source"] = "projects" if "project_id" in kwargs.keys(
                ) else "tasks"
            obj = entity(**kwargs)
            if entity_type != "commentaries" and (existing_obj :=
                                                  self.repo.list(
                                                      entity,
                                                      {"name": obj.name})):
                print("Found existing entity\n")
                existing_id = str(existing_obj[0].id)
                self.execute("show", entity_type, {"id": existing_id})
                answer = input("Do you want to create entity anyway? [Y/n] ")
                if answer.lower() != "y":
                    exit()
            else:
                self.repo.add(obj)
                session.commit()
            if hasattr(obj, "project"):
                project = services.lookup_project_name(obj.project, self.repo)
            else:
                project = None
            print_new_object(obj, project)
            logger.info("<create> %s: %s", entity_type, obj.id)
            return entity, obj
        elif command == "delete":
            kwargs.update({"status": "DELETED"})
            self.execute("update", entity_type, kwargs)
            logger.info("<delete> %s", entity_type)
            return entity, None
        elif command == "update":
            if (task_id := kwargs.get("id")):
                del kwargs["id"]
                tasks = get_ids(task_id)
                for task in tasks:
                    if (old_values := self.repo.list(entity, {"id": task})):
                        old_values = old_values[0]
                        old_settings = {
                            key: getattr(old_values, key)
                            for key in kwargs.keys()
                        }
                        if old_settings != kwargs:
                            new_kwargs = {}
                            for k, v in kwargs.items():
                                if old_settings[k] != v:
                                    new_kwargs[k] = v
                            self.repo.update(entity, task, new_kwargs)
                            logger.info("<update> %s: %s", entity_type, task)
                            now = datetime.now()
                            for key, value in new_kwargs.items():
                                try:
                                    old_value = old_settings[key].name
                                except:
                                    old_value = old_settings[key]
                                self.repo.add(
                                    Event(entity_type, task, now, key,
                                          old_value, value))
                    session.commit()
                return entity, None
            else:
                raise ValueError("No task_id is provided")
        elif command == "edit":
            if (task_id := kwargs.get("id")):
                tasks = get_ids(task_id)
                for task in tasks:
                    if task.isdigit():
                        entities = self.repo.list(entity, {"id": task})
                        task_id = task
                    else:
                        entities = self.repo.list(entity, {"name": task})
                        task_id = entities[0].id
                    if entity_type == "tasks":
                        task = entities[0]
                        if kwargs.get("description"):
                            current_entry = task.description
                            current_type = "description"
                        elif kwargs.get("name"):
                            current_entry = task.name
                            current_type = "name"
                        else:
                            raise ValueError(
                                "Either name or description should be specified!"
                            )

                    message_template = generate_message_template(
                        CurrentEntry(current_entry, current_type), task,
                        self.repo)
                    with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
                        tf.write(message_template.encode("utf-8"))
                        tf.flush()
                        run(["vim", "+2", tf.name])
                        tf.seek(0)
                        new_entry = tf.read()

                    updated_entry = []
                    new_entry = new_entry.decode("utf-8").rstrip()
                    for i, row in enumerate(new_entry.split("\n")):
                        if not row.startswith("#") and row:
                            if row.startswith("--"):
                                break
                            updated_entry.append(row)
                new_kwargs = {
                    "id": task_id,
                    current_type: " ".join(updated_entry)
                }
                self.execute("update", entity_type, new_kwargs)
                return entities, None, None
        elif command == "show":
            if (task_id := kwargs.get("id")):
                tasks = get_ids(task_id)
                for task in tasks:
                    if task.isdigit():
                        entities = self.repo.list(entity, {"id": task})
                        task_id = task
                    else:
                        entities = self.repo.list(entity, {"name": task})
                        task_id = entities[0].id
                    history = self.repo.list(Event, {
                        "element_id": task_id,
                        "source": entity_type
                    })
                    commentaries = self.repo.list(Commentary, {
                        "element_id": task_id,
                        "source": entity_type
                    })
                    if entity_type == "projects":
                        for entity_ in entities:
                            print_task(entity_.tasks, self.repo)
                            logger.info("<show> %s: %s", entity_type,
                                        entity_.id)
                        if history:
                            print_history(history)
                        if commentaries:
                            print_commentaries(commentaries)
                    #TODO: show completed tasks as well
                    if entity_type == "tasks":
                        if kwargs.get("description"):
                            print(entities[0].description)
                            return
                        if kwargs.get("name"):
                            print(entities[0].name)
                            return
                        print_task(entities, self.repo, show_completed=True)
                        logger.info("<show> %s: %s", entity_type, task_id)
                        if history:
                            print_history(history)
                        if commentaries:
                            print_commentaries(commentaries)
                return entities, history, commentaries
        elif command == "done":
            if entity_type != "tasks":
                raise ValueError("can complete only tasks!")
            else:
                kwargs.update({"status": "DONE"})
                self.execute("update", entity_type, kwargs)
        else:
            raise ValueError(f"Uknown command: {command}")


def get_attributes(obj) -> List[Tuple[str, str]]:
    import inspect
    attributes = []
    for name, value in inspect.getmembers(obj):
        if not name.startswith("_") and not inspect.ismethod(value):
            if hasattr(value, "name"):
                attributes.append((name, value.name))
            elif isinstance(value, datetime):
                attributes.append((name, value.strftime("%Y-%m-%d %H:%M")))
            else:
                attributes.append((name, str(value)))
    return attributes


class Printer:

    def __init__(self):
        self.console = Console()
        self.table = Table(box=rich.box.SIMPLE)
        
    def print(self, entities, zero_tasks = False, zero_tasks_only = False):
        for column in ("id", "name", "description", "open_tasks", "overdue",
                       "backlog", "todo", "in_progress", "review", "done"):
            self.table.add_column(column)
        for entity in entities:
            if entity.status.name == "DELETED":
                continue
            open_tasks = sort_open_tasks(entity)
            overdue_tasks = [
                task for task in entity.tasks
                if task.due_date and task.due_date <= datetime.now().date()
                and task.status.name not in ("DELETED", "DONE")
            ]
            backlog = count_task_status(entity.tasks, "BACKLOG")
            todo = count_task_status(entity.tasks, "TODO")
            in_progress = count_task_status(entity.tasks, "IN_PROGRESS")
            review = count_task_status(entity.tasks, "REVIEW")
            done = count_task_status(entity.tasks, "DONE")

            if zero_tasks or open_tasks > 0:
                self.table.add_row(f"[red]{entity.id}[/red]", entity.name,
                              entity.description, str(open_tasks),
                              str(len(overdue_tasks)), str(backlog), str(todo),
                              str(in_progress), str(review), str(done))
            if zero_tasks_only and open_tasks == 0:
                self.table.add_row(f"[red]{entity.id}[/red]", entity.name,
                              entity.description, str(tasks))
            self.console.print(self.table)
        

def print_new_object(obj, project):
    console = Console()
    table = Table(box=rich.box.SIMPLE)
    attributes = get_attributes(obj)
    for column, _ in attributes:
        table.add_column(column)
    table.add_row(*list(zip(*attributes))[1])
    console.print(table)


def print_history(entities):
    console = Console()
    table = Table(box=rich.box.SIMPLE)
    print("History:")
    for column in ("date", "type", "old_value", "new_value"):
        table.add_column(column)
    for event in entities:
        table.add_row(event.date.strftime("%Y-%m-%d %H:%M"), event.type,
                      event.old_value, event.new_value)
    console.print(table)


def print_commentaries(entities):
    console = Console()
    table = Table(box=rich.box.SIMPLE)
    print("Comments:")
    for column in ("date", "text"):
        table.add_column(column)
    for event in entities:
        table.add_row(event.date.strftime("%Y-%m-%d %H:%M"), event.text)
    console.print(table)


def sort_open_tasks(entities):
    return len([
        task for task in entities.tasks
        if task.status.name not in ("DONE", "DELETED")
    ])


def print_entities(entities, type, repo):
    if type == "projects":
        entities.sort(key=sort_open_tasks, reverse=True)
        print_project(entities)
    elif type == "tasks":
        entities.sort(key=lambda c: (c.status.value, c.priority.value
                                     if hasattr(c.priority, "value") else 0),
                      reverse=True)
        print_task(entities, repo)
    else:
        print_default_entity(entities)


def print_default_entity(entities):
    console = Console()
    table = Table(box=rich.box.SIMPLE)
    for column in ("id", "date", "text"):
        table.add_column(column)
    for entity in entities:
        table.add_row(f"[red]{entity.id}[/red]",
                      entity.date.strftime("%Y-%m-%d %H:%M"), entity.text)
    console.print(table)


def print_project(entities,
                  zero_tasks: bool = False,
                  zero_tasks_only: bool = False):
    console = Console()
    table = Table(box=rich.box.SIMPLE)
    for column in ("id", "name", "description", "open_tasks", "overdue",
                   "backlog", "todo", "in_progress", "review", "done"):
        table.add_column(column)
    for entity in entities:
        if entity.status.name == "DELETED":
            continue
        open_tasks = sort_open_tasks(entity)
        overdue_tasks = [
            task for task in entity.tasks
            if task.due_date and task.due_date <= datetime.now().date()
            and task.status.name not in ("DELETED", "DONE")
        ]
        backlog = count_task_status(entity.tasks, "BACKLOG")
        todo = count_task_status(entity.tasks, "TODO")
        in_progress = count_task_status(entity.tasks, "IN_PROGRESS")
        review = count_task_status(entity.tasks, "REVIEW")
        done = count_task_status(entity.tasks, "DONE")

        if zero_tasks or open_tasks > 0:
            table.add_row(f"[red]{entity.id}[/red]", entity.name,
                          entity.description, str(open_tasks),
                          str(len(overdue_tasks)), str(backlog), str(todo),
                          str(in_progress), str(review), str(done))
        if zero_tasks_only and open_tasks == 0:
            table.add_row(f"[red]{entity.id}[/red]", entity.name,
                          entity.description, str(tasks))
        console.print(table)


def count_task_status(tasks, status: str) -> int:
    return len([task for task in tasks if task.status.name == status])


def print_task(entities, repo, show_completed=False):
    console = Console()
    table = Table(box=rich.box.SIMPLE)
    for column in ("id", "name", "description", "status", "priority",
                   "project", "due_date"):
        table.add_column(column)
    entities = list(entities)
    entities.sort(key=lambda c: (c.status.value, c.priority.value),
                  reverse=True)
    for entity in entities:
        try:
            project = services.lookup_project_name(entity.project_id, repo)
        except:
            project = None
        if entity.status.name in ("DELETED", "DONE") and not show_completed:
            continue
        else:
            priority = entity.priority.name if hasattr(entity.priority,
                                                       "name") else "UNKNOWN"
            if entity.due_date and entity.due_date <= date.today():
                table.add_row(f"[red]{entity.id}[/red]", entity.name,
                              entity.description, entity.status.name, priority,
                              project, str(entity.due_date))
            else:
                table.add_row(str(entity.id), entity.name, entity.description,
                              entity.status.name, priority, project,
                              str(entity.due_date))
    console.print(table)


def get_ids(id_string: str):
    if "," in id_string:
        ids = id_string.split(",")
    elif ".." in id_string:
        task_range = id_string.split("..")
        ids = range(int(task_range[0]), int(task_range[1]) + 1)
    else:
        ids = [id_string]
    return ids
