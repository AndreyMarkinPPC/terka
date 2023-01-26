from typing import Any, Dict, List, Tuple

from dataclasses import dataclass
from datetime import datetime, date, timedelta

import re
import sys, tempfile, os
from subprocess import run
from statistics import mean, median
import yaml

import logging
import rich
from rich.console import Console
from rich.table import Table

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Header, Static, Input

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

    def execute(self,
                command,
                entity_type=None,
                kwargs: Dict[str, Any]=None,
                show_history=False):
        session = self.repo.session
        entity = self.handle(entity_type)
        # if not command and not entity_type:
        #     print("Running terka in interactive mode")
        #     command = input("enter command: ")
        #     entity_type = input("enter entity: ")
        if not entity and command not in ("init", "unfocus", "log", "calendar"):
            raise ValueError(f"Entity *{entity_type}* is not a valid entity")
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
            print_entities(entities, entity_type, self.repo, custom_sort)
            logger.info("<list> %s", entity_type)
            return entities, None, None
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
                            print_project(entities)
                        else:
                            print(f"No entity {task} found!")
                        for entity_ in entities:
                            print_task(entity_.tasks,
                                       self.repo,
                                       show_completed=show_completed)
                            logger.info("<show> %s: %s", entity_type,
                                        entity_.id)
                        if history and show_history:
                            print_history(history)
                        if commentaries:
                            print_commentaries(commentaries)
                    #TODO: show completed tasks as well
                    if entity_type == "tasks":
                        # if kwargs.get("description"):
                        #     print(entities[0].description)
                        #     return
                        # if kwargs.get("name"):
                        #     print(entities[0].name)
                        #     return
                        if task_id:
                            print_task(entities,
                                       self.repo,
                                       show_completed=show_completed,
                                       history=history,
                                       comments=commentaries)
                        else:
                            print(f"No entity {task} found!")
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
                console = Console()
                console.print(
                    "[green]Yay! You've just completed a task![/green]")

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


def print_entities(entities, type, repo, custom_sort):
    if type == "projects":
        entities.sort(key=sort_open_tasks, reverse=True)
        print_project(entities)
    elif type == "tasks":
        if custom_sort:
            entities.sort(key=lambda c: getattr(c, custom_sort), reverse=False)
        else:
            entities.sort(key=lambda c:
                          (c.status.value, c.priority.value
                           if hasattr(c.priority, "value") else 0),
                          reverse=True)
        print_task(entities=entities, repo=repo, custom_sort=custom_sort)
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
    table = Table(box=rich.box.SQUARE_DOUBLE_HEAD)
    for column in ("id", "name", "description", "open_tasks", "overdue",
                   "backlog", "todo", "in_progress", "review", "done",
                   "median_task_age"):
        table.add_column(column)
    for entity in entities:
        if entity.status.name == "DELETED":
            continue
        open_tasks = sort_open_tasks(entity)
        if open_tasks > 0:
            overdue_tasks = [
                task for task in entity.tasks
                if task.due_date and task.due_date <= datetime.now().date()
                and task.status.name not in ("DELETED", "DONE")
            ]
            median_task_age = round(
                median([(datetime.now() - task.creation_date).days
                        for task in entity.tasks
                        if task.status.name not in ("DELETED", "DONE")]))
            backlog = count_task_status(entity.tasks, "BACKLOG")
            todo = count_task_status(entity.tasks, "TODO")
            in_progress = count_task_status(entity.tasks, "IN_PROGRESS")
            review = count_task_status(entity.tasks, "REVIEW")
            done = count_task_status(entity.tasks, "DONE")

            if zero_tasks or len(overdue_tasks) > 0:
                entity_id = f"[red]{entity.id}[/red]"
            else:
                entity_id = f"[green]{entity.id}[/green]"
            table.add_row(f"{entity_id}", entity.name, entity.description,
                          str(open_tasks),
                          str(len(overdue_tasks)), str(backlog), str(todo),
                          str(in_progress), str(review), str(done),
                          str(median_task_age))
            # if zero_tasks_only and open_tasks == 0:
            #     table.add_row(f"[red]{entity.id}[/red]", entity.name,
            #                   entity.description, str(tasks))
    console.print(table)


def count_task_status(tasks, status: str) -> int:
    return len([task for task in tasks if task.status.name == status])


def print_task(entities,
               repo,
               show_completed=False,
               custom_sort=None,
               history=None,
               comments=None):
    console = Console()
    table = Table(box=rich.box.SIMPLE)
    #TODO: Add printing for only a single task
    # if (entities[0].status.name == "DONE"):
    #     console.print(f"[green]task is completed on [/green]")
    # else:
    #     active_in_days = datetime.now() - entities[0].creation_date
    #     console.print(f"[blue]task is active {active_in_days.days} days[/blue]")
    for column in ("id", "name", "description", "status", "priority",
                   "project", "due_date"):
        table.add_column(column)
    entities = list(entities)
    completed_tasks = []
    if custom_sort:
        entities.sort(key=lambda c: getattr(c, custom_sort), reverse=False)
    else:
        entities.sort(key=lambda c: (c.status.value, c.priority.value),
                      reverse=True)
    printable_entities = 0
    for entity in entities:
        try:
            project_obj = services.lookup_project_name(entity.project, repo)
            project = project_obj.name
        except:
            project = None
        priority = entity.priority.name if hasattr(entity.priority,
                                                   "name") else "UNKNOWN"
        if entity.status.name in ("DELETED", "DONE"):
            completed_tasks.append(entity)
            continue
        printable_entities += 1
        if entity.due_date and entity.due_date <= date.today():
            table.add_row(f"[red]{entity.id}[/red]", entity.name,
                          entity.description, entity.status.name, priority,
                          project, str(entity.due_date))
        else:
            table.add_row(str(entity.id), entity.name, entity.description,
                          entity.status.name, priority, project,
                          str(entity.due_date))
    if show_completed:
        console.print(f"[green]****OPEN TASKS*****[/green]")
    if printable_entities:
        if printable_entities == 1:
            app = TerkaTask(entity=entity,
                            project=project,
                            history=history,
                            commentaries=comments)
            app.run()
        console.print(table)
    if show_completed:
        if show_completed:
            console.print(f"[green]****COMPLETED TASKS*****[/green]")
        table = Table(box=rich.box.SIMPLE)
        for column in ("id", "name", "description", "status", "priority",
                       "project", "due_date"):
            table.add_column(column)
        for entity in completed_tasks:
            table.add_row(str(entity.id), entity.name, entity.description,
                          entity.status.name, priority, project,
                          str(entity.due_date))
        console.print(table)
    if len(entities) == 1 and printable_entities == 0:
        table = Table(box=rich.box.SIMPLE)
        for column in ("id", "name", "description", "status", "priority",
                       "project", "due_date"):
            table.add_column(column)
        for entity in entities:
            app = TerkaTask(entity=entity,
                            project=project,
                            is_completed=True,
                            history=history,
                            commentaries=comments)
            app.run()
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


class Comment(Widget):
    value = reactive("text")

    def render(self) -> str:
        return f"Comment: {self.value}"


class TerkaTask(App):
    BINDINGS = [("q", "quit", "Quit")]
    CSS_PATH = "vertical_layout.css"

    def __init__(self,
                 entity,
                 project,
                 is_completed: bool = False,
                 history=None,
                 commentaries=None):
        super().__init__()
        self.entity = entity
        self.project = project
        self.is_completed = is_completed
        self.history = history
        self.commentaries = commentaries
        self.is_overdue = datetime.today().date(
        ) > entity.due_date if entity.due_date else False

    def compose(self) -> ComposeResult:
        yield Header()
        task_text = f"[bold]Task {self.entity.id}: {self.entity.name}[/bold]"
        if self.is_completed:
            yield Static(task_text, classes="header_completed", id="header")
        elif self.is_overdue:
            yield Static(task_text, classes="header_overdue", id="header")
        else:
            yield Static(task_text, classes="header_simple", id="header")
        yield Static(f"Project: [bold]{self.project}[/bold]", classes="transp")
        yield Static(f"Status: [bold]{self.entity.status.name}[/bold]",
                     classes="transp")
        yield Static(f"Priority: [bold]{self.entity.priority.name}[/bold]",
                     classes="transp")
        created_days_ago = (datetime.now() - self.entity.creation_date).days
        creation_message = f"{created_days_ago} days ago" if created_days_ago > 1 else "today"
        yield Static(f"Created {creation_message}", classes="header_simple")
        if self.is_completed:
            completion_date = self._get_completion_date()
            if completion_date:
                completed_days_ago = (datetime.now() - completion_date).days
                completion_message = f"{completed_days_ago} days ago" if completed_days_ago > 1 else "today"
                yield Static(
                    f"Completed {completion_message} ({completion_date.strftime('%Y-%m-%d')})",
                    classes="header_simple")
            else:
                yield Static("Completion date unknown", classes="header_simple")
        else:
            yield Static(f"Due date: {self.entity.due_date}", classes="header_simple")
        description_message = self.entity.description or ""
        if description_message:
            yield Static(
                f"[italic]Description...\n[/italic]{description_message}",
                classes="body",
                id="desc")
        else:
            yield Static("[italic]No description...[/italic]",
                         classes="body",
                         id="desc")
        if self.commentaries:
            comms = [
                f"[italic]{comment.date.date()}[/italic]: {comment.text}"
                for comment in self.commentaries
            ]
            comms_message = "\n".join(comms)
            yield Static(f"[italic]Comments...\n\n[/italic]{comms_message}",
                         classes="body",
                         id="history")
        else:
            yield Static("", classes="body", id="history")
        yield Input(placeholder="Add a comment", classes="body", id="comment")
        # yield Comment()

    def action_quit(self) -> None:
        App.action_quit()

    def on_input_changed(self, event: Input.Changed) -> None:
        self.query_one(Comment).text = event.value

    def _get_completion_date(self):
        for event in self.history:
            if event.new_value == "DONE":
                return event.date
