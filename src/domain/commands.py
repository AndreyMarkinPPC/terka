from typing import Any, Dict, List, Tuple

from dataclasses import dataclass
from datetime import datetime

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

from src.service_layer import services, printer
from src.service_layer.ui import TerkaTask
from src.adapters.repository import AbsRepository
from src.utils import format_command

logger = logging.getLogger(__name__)


@dataclass
class CurrentEntry:
    value: str
    type: str


def generate_message_template(current_entry: CurrentEntry, task: Task,
                              repo) -> str:
    project = services.lookup_project_name(task.project, repo)
    message_template = f"""
    # You are editing {current_entry.type}, enter below:
    {current_entry.value}
    ---
    Task context:
    id: {task.id}
    name: {task.name}
    description: {task.description}
    project: {project.name}
    """
    return re.sub("\n +", "\n", message_template.lstrip())


class BaseHandler:

    def __init__(self, successor) -> None:
        self._successor = successor

    def handle(self, entity):
        if self._successor:
            return self._successor.handle(entity)
        return None


class TaskHandler(BaseHandler):

    def handle(self, entity):
        if "tasks".startswith(entity):
            logger.debug("Handling task")
            return Task, "tasks"
        return super().handle(entity)


class ProjectHandler(BaseHandler):

    def handle(self, entity):
        if "projects".startswith(entity):
            logger.debug("Handling project")
            return Project, "projects"
        return super().handle(entity)


class UserHandler(BaseHandler):

    def handle(self, entity):
        if "users".startswith(entity):
            logger.debug("Handling user")
            return User, "users"
        return super().handle(entity)


class CommentaryHandler(BaseHandler):

    def handle(self, entity):
        if "commentaries".startswith(entity):
            logger.debug("Handling commentary")
            return Commentary, "commentaries"
        return super().handle(entity)


class CommandHandler:

    def __init__(self, repo: AbsRepository):
        self.repo = repo
        self.handler = self._init_handlers()
        self.home_dir = os.path.expanduser('~')
        self.printer = printer.Printer()

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

    def execute(self,
                command,
                entity_type=None,
                kwargs: Dict[str, Any]=None,
                show_history=False):
        session = self.repo.session
        if entity_type:
            entity, entity_type = self.handle(entity_type)
        else:
            entity = None
        if not entity and command not in ("init", "unfocus", "log", "calendar", "help"):
            raise ValueError(f"Entity *{entity_type}* is not a valid entity")
        command = format_command(command)
        if command == "list":
            if entity_type == "tasks" and "status" not in kwargs:
                kwargs["status"] = "BACKLOG,TODO,IN_PROGRESS,REVIEW"
            if (custom_sort := kwargs.get("sort")):
                del kwargs["sort"]
            else:
                custom_sort = None
            if entity_type == "projects" and "project_id" in kwargs:
                kwargs["id"] = kwargs.pop("project_id")
            entities = self.repo.list(entity, kwargs)
            if custom_sort == "due_date":
                entities_with_due_date = []
                entities_without_due_date = []
                for entity in entities:
                    if entity.due_date:
                        entities_with_due_date.append(entity)
                entities_with_due_date.sort(key=lambda c: c.due_date,
                                            reverse=False)
                entities = entities_with_due_date
            session.commit()
            self.printer.print_entities(entities, entity_type, self.repo, custom_sort)
            logger.info("<list> %s", entity_type)
            return entities, None, None
        elif command == "help":
            print("""
            available commands: 'list', 'show', 'create', 'update', 'done', 'calendar', 'log', 'edit'
            available entities: 'tasks', 'projects', 'commentaries'
            """
          )
        elif command == "init":
            home_dir = os.path.expanduser('~')
            path = os.path.join(home_dir, ".terka")
            if not os.path.exists(path):
                answer = input(f"Do you want to init terka in this directory {path}? [Y/n]")
                if "y" in answer.lower():
                    os.mkdirs(path)
                    with open(os.path.join(path, "config.yaml"), "w") as f:
                      yaml.dump({"user": "admin"}, f)
                elif "n" in answer.lower():
                    path = input("Specify full path to the terka directory: ")
                    os.mkdirs(path)
                else:
                    exit()
            elif not os.path.exists(os.path.join(path, "config.yaml")):
                answer = input(f"Config.yaml not found in {path}, Create it? [Y/n]")
                if "y" in answer.lower():
                    with open(os.path.join(path, "config.yaml"), "w") as f:
                      yaml.dump({"user": "admin"}, f)
                else:
                    exit()
            else:
                print("Terka directory already exist.")
        elif command == "get":
            if entity_type == "tasks" and "status" not in kwargs:
                kwargs["status"] = "BACKLOG,TODO,IN_PROGRESS,REVIEW,DONE"
            if (custom_sort := kwargs.get("sort")):
                del kwargs["sort"]
            else:
                custom_sort = None
            if entity_type == "projects" and "project_id" in kwargs:
                kwargs["id"] = kwargs.pop("project_id")
            entities = self.repo.list(entity, kwargs)
            if custom_sort == "due_date":
                entities_with_due_date = []
                entities_without_due_date = []
                for entity in entities:
                    if entity.due_date:
                        entities_with_due_date.append(entity)
                entities_with_due_date.sort(key=lambda c: c.due_date,
                                            reverse=False)
                entities = entities_with_due_date
            session.commit()
            return entities
        elif command == "calendar":
            kwargs["sort"] = "due_date"
            self.execute("list", "tasks", kwargs)
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
                if "project_id" in kwargs.keys():
                    kwargs["source"] = "projects"
                    kwargs["element_id"] = kwargs["project_id"]
                else:
                    kwargs["source"] = "tasks"
                    kwargs["element_id"] = kwargs["id"]
                    existing_task = self.repo.list(Task,
                                                   {"id": kwargs["id"]})
                    if not existing_task:
                        raise ValueError(
                            f"Task with id {kwargs['id']} is not found!")
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
            if hasattr(obj, "project") and obj.project:
                project = services.lookup_project_name(obj.project, self.repo)
            else:
                project = None
            self.printer.print_new_object(obj, project)
            logger.info("<create> %s: %s", entity_type, obj.id)
            return entity, obj
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
                        else:
                            print("nothing to update")  #TODO: reword
                    session.commit()
                return entity, None
            else:
                raise ValueError("No task_id is provided")
        elif command == "delete":
            kwargs.update({"status": "DELETED"})
            self.execute("update", entity_type, kwargs)
            logger.info("<delete> %s", entity_type)
            return entity, None
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
            show_completed = bool(kwargs.get("show_completed"))
            if (task_id := kwargs.get("id")):
                tasks = get_ids(task_id)
                for task in tasks:
                    if task.isdigit():
                        entities = self.repo.list(entity, {"id": task})
                        task_id = task
                    else:
                        entities = self.repo.list(entity, {"name": task})
                        if entities:
                            task_id = entities[0].id
                        else:
                            task_id = None
                    if task_id:
                        history = self.repo.list(Event, {
                            "element_id": task_id,
                            "source": entity_type
                        })
                        commentaries = self.repo.list(Commentary, {
                            "element_id": task_id,
                            "source": entity_type
                        })
                    else:
                        history = None
                        commentaries = None
                    if entity_type == "projects":
                        if task_id:
                            self.printer.print_project(entities)
                        else:
                            print(f"No entity {task} found!")
                        for entity_ in entities:
                            self.printer.print_task(entity_.tasks,
                                       self.repo,
                                       show_completed=show_completed)
                            logger.info("<show> %s: %s", entity_type,
                                        entity_.id)
                        if history and show_history:
                            self.printer.print_history(history)
                        if commentaries:
                            self.printer.print_commentaries(commentaries)
                    #TODO: show completed tasks as well
                    if entity_type == "tasks":
                        # if kwargs.get("description"):
                        #     print(entities[0].description)
                        #     return
                        # if kwargs.get("name"):
                        #     print(entities[0].name)
                        #     return
                        if task_id:
                            self.printer.print_task(entities,
                                       self.repo,
                                       show_completed=show_completed,
                                       history=history,
                                       comments=commentaries)
                        else:
                            print(f"No entity {task} found!")
                        logger.info("<show> %s: %s", entity_type, task_id)
                        if history:
                            self.printer.print_history(history)
                        if commentaries:
                            self.printer.print_commentaries(commentaries)
                return entities, history, commentaries
        elif command == "done":
            if entity_type != "tasks":
                raise ValueError("can complete only tasks!")
            else:
                kwargs.update({"status": "DONE"})
                self.execute("update", entity_type, kwargs)
                console = Console()
                console.print(
                    "[green]Yay! You've just completed a task![/green]")

        else:
            raise ValueError(f"Uknown command: {command}")



def get_ids(id_string: str):
    if "," in id_string:
        ids = id_string.split(",")
    elif ".." in id_string:
        task_range = id_string.split("..")
        ids = range(int(task_range[0]), int(task_range[1]) + 1)
    else:
        ids = [id_string]
    return ids


