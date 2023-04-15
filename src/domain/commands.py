from typing import Any, Dict, List, Tuple, Optional, Union

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
from src.domain.commentary import TaskCommentary, ProjectCommentary, EpicCommentary, StoryCommentary, SprintCommentary
from src.domain.tag import BaseTag, TaskTag, ProjectTag
from src.domain.collaborators import TaskCollaborator, ProjectCollaborator
from src.domain.event_history import TaskEvent, ProjectEvent
from src.domain.sprint import Sprint, SprintTask
from src.domain.time_tracker import TimeTrackerEntry
from src.domain.epic import Epic, EpicTask
from src.domain.story import Story, StoryTask

from src.service_layer import services, printer
from src.service_layer.ui import TerkaTask
from src.adapters.repository import AbsRepository
from src.utils import format_command, format_task_dict

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


class TagHandler(BaseHandler):

    def handle(self, entity):
        if "tags".startswith(entity):
            logger.debug("Handling tags")
            return BaseTag, "tags"
        return super().handle(entity)


class SprintHandler(BaseHandler):

    def handle(self, entity):
        if "sprints".startswith(entity):
            logger.debug("Handling sprints")
            return Sprint, "sprints"
        return super().handle(entity)


class SprintTaskHandler(BaseHandler):

    def handle(self, entity):
        if entity == "sprint_tasks":
            logger.debug("Handling sprint task")
            return SprintTask, "sprint_tasks"
        return super().handle(entity)


class TimeTrackerHandler(BaseHandler):

    def handle(self, entity):
        if entity == "time_entry":
            logger.debug("Handling time entry")
            return TimeTrackerEntry, "time_entries"
        return super().handle(entity)


class EpicHandler(BaseHandler):

    def handle(self, entity):
        if "epics".startswith(entity):
            logger.debug("Handling epics")
            return Epic, "epics"
        return super().handle(entity)


class EpicTaskHandler(BaseHandler):

    def handle(self, entity):
        if entity == "epic_tasks":
            logger.debug("Handling epic task")
            return EpicTask, "epic_tasks"
        return super().handle(entity)


class StoryHandler(BaseHandler):

    def handle(self, entity):
        if entity in ("story", "stories"):
            logger.debug("Handling stories")
            return Story, "stories"
        return super().handle(entity)


class StoryTaskHandler(BaseHandler):

    def handle(self, entity):
        if entity == "story_tasks":
            logger.debug("Handling epic task")
            return StoryTask, "story_tasks"
        return super().handle(entity)


class CommandHandler:

    def __init__(self, repo: AbsRepository):
        self.repo = repo
        self.handler = self._init_handlers()
        self.home_dir = os.path.expanduser('~')
        self.printer = printer.Printer(repo)
        self.console = Console()
        self.config = self._read_config()

    def _init_handlers(self):
        handler_chain = BaseHandler(None)
        for handler in [
                TaskHandler, ProjectHandler, UserHandler, TagHandler,
                SprintHandler, SprintTaskHandler, TimeTrackerHandler,
                EpicHandler, StoryHandler
        ]:
            new_handler = handler(handler_chain)
            handler_chain = new_handler
        return handler_chain

    def handle(self, entity):
        return self.handler.handle(entity)

    def execute(self,
                command,
                entity_type=None,
                kwargs: Dict[str, Any] = None):
        session = self.repo.session
        if entity_type:
            entity, entity_type = self.handle(entity_type)
        else:
            entity = None
        if not entity and command not in ("init", "unfocus", "log", "calendar",
                                          "help"):
            raise ValueError(f"Entity *{entity_type}* is not a valid entity")
        command = format_command(command)
        if command == "list":
            print_options = printer.PrintOptions(
                show_tasks=False,
                show_history=bool(kwargs.get("show_history")),
                show_commentaries=bool(kwargs.get("show_commentaries")),
                show_completed=bool(kwargs.get("show_completed"))
            )
            if entity_type == "tasks":
                if "status" not in kwargs and "all" not in kwargs:
                    kwargs["status"] = "BACKLOG,TODO,IN_PROGRESS,REVIEW"
                else:
                    if "all" in kwargs:
                        del kwargs["all"]
                    show_completed = True
            if entity_type == "sprints":
                if "all" in kwargs:
                    kwargs["status"] = "PLANNED,ACTIVE,COMPLETED"
                    del kwargs["all"]
                else:
                    kwargs["status"] = "PLANNED,ACTIVE"
            if entity_type == "projects":
                if "all" in kwargs:
                    kwargs["status"] = "DELETED,ACTIVE,ON_HOLD,COMPLETED"
                    del kwargs["all"]
                    show_completed = True
                else:
                    kwargs["status"] = "ACTIVE"

            if (custom_sort := kwargs.get("sort")):
                del kwargs["sort"]
            else:
                custom_sort = None
            if entity_type == "projects" and "project_id" in kwargs:
                kwargs["id"] = kwargs.pop("project_id")
            if "collaborators" in kwargs:
                collaborator_name = kwargs["collaborators"]
                collaborator = self.repo.list(User,
                                              {"name": collaborator_name})
                if collaborator:
                    task_collaborators = self.repo.list(
                        TaskCollaborator, {"collaborator": collaborator[0].id})
                    if task_collaborators:
                        kwargs["id"] = ",".join([
                            str(task_collaborator.task)
                            for task_collaborator in task_collaborators
                        ])
                        del kwargs["collaborators"]
                    else:
                        self.console.print(
                            f"[red]No task with collaborator '{colaborator_name}' found![/red]"
                        )
                        exit()
                else:
                    self.console.print(
                        f"[red]No user '{collaborator_name}' found![/red]")
                    exit()
            if "tags" in kwargs:
                tag_text = kwargs["tags"]
                tag = self.repo.list(BaseTag, {"text": tag_text})
                if tag:
                    task_tags = self.repo.list(TaskTag, {"tag": tag[0].id})
                    if task_tags:
                        kwargs["id"] = ",".join(
                            [str(task_tag.task) for task_tag in task_tags])
                        del kwargs["tags"]
                    else:
                        self.console.print(
                            f"[red]No tasks with tag '{tag_text}' found![/red]"
                        )
                        exit()
                else:
                    self.console.print(
                        f"[red]No tag '{tag_text}' found![/red]")
                    exit()
            entities = self.repo.list(entity, kwargs)
            # if entity_type == "sprints":
            #     self.printer.print_sprint(entities=entities,
            #                               repo=self.repo,
            #                               show_tasks=False)
            #     exit()
            # if entity_type == "epics":
            #     self.printer.print_epic(entities=entities,
            #                             repo=self.repo,
            #                             show_tasks=False)
            #     exit()
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
            self.printer.print_entities(entities,
                                        entity_type,
                                        self.repo,
                                        custom_sort,
                                        print_options=print_options)
            logger.info("<list> %s", entity_type)
            return entities, None, None
        elif command == "help":
            print("""
            available commands: 'list', 'show', 'create', 'update', 'done', 'calendar', 'log', 'edit'
            available entities: 'tasks', 'projects', 'commentaries'
            """)
        elif command == "init":
            home_dir = os.path.expanduser('~')
            path = os.path.join(home_dir, ".terka")
            if not os.path.exists(path):
                answer = input(
                    f"Do you want to init terka in this directory {path}? [Y/n]"
                )
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
                answer = input(
                    f"Config.yaml not found in {path}, Create it? [Y/n]")
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
            self.console.print(table)
        elif command == "focus":
            if entity_type == "tasks":
                self.config["task_id"] = kwargs["id"]
                if "project_name" in self.config.keys():
                    del self.config["project_name"]
            if entity_type == "projects":
                self.config["project_name"] = kwargs["id"]
                if "task_id" in self.config.keys():
                    del self.config["task_id"]
            with open(f"{self.home_dir}/.terka/config.yaml",
                      "w",
                      encoding="utf-8") as f:
                yaml.dump(self.config, f)
            logger.info("<focus> %s: %s", entity_type, "")
        elif command == "unfocus":
            if "task_id" in self.config.keys():
                del self.config["task_id"]
            if "project_name" in self.config.keys():
                del self.config["project_name"]
            with open(f"{self.home_dir}/.terka/config.yaml",
                      "w",
                      encoding="utf-8") as f:
                yaml.dump(self.config, f)
            logger.info("<unfocus> %s: %s", entity_type, "")
        elif command == "count":
            entities = self.repo.list(entity, kwargs)
            print(len(entities))
            logger.info("<count> tasks")
        elif command == "collaborate":
            if entity_type == "tasks":
                task_id = kwargs["id"]
                existing_task = self.repo.list(Task, {"id": task_id})
                if not existing_task:
                    raise ValueError(f"Task with id {task_id} is not found!")
                user = self.repo.list(User, {"name": kwargs["name"]})
                if not user:
                    user = User(**kwargs)
                    self.repo.add(user)
                    session.commit()
                    user_id = user.id
                else:
                    user_id = user[0].id
                existing_task_collaborator = self.repo.list(
                    TaskCollaborator, {
                        "task": task_id,
                        "collaborator": user_id
                    })
                if not existing_task_collaborator:
                    task_ids = get_ids(task_id)
                    for task_id in task_ids:
                        obj = TaskCollaborator(id=task_id,
                                               collaborator_id=user_id)
                        self.repo.add(obj)
                    session.commit()
            elif entity_type == "projects":
                project_id = kwargs["id"]
                existing_project = self.repo.list(Project, {"id": project_id})
                if not existing_project:
                    raise ValueError(
                        f"Project with id {project_id} is not found!")
                user = self.repo.list(User, {"name": kwargs["name"]})
                if not user:
                    user = User(**kwargs)
                    self.repo.add(user)
                    session.commit()
                    user_id = user.id
                else:
                    user_id = user[0].id
                existing_project_collaborator = self.repo.list(
                    ProjectCollaborator, {
                        "project": project_id,
                        "collaborator": user_id
                    })
                if not existing_project_collaborator:
                    project_ids = get_ids(project_id)
                    for project_id in project_ids:
                        obj = ProjectCollaborator(id=project_id,
                                                  collaborator_id=user_id)
                        self.repo.add(obj)
                        session.commit()
        elif command == "tag":
            if entity_type == "tasks":
                task_id = kwargs["id"]
                existing_task = self.repo.list(Task, {"id": task_id})
                if not existing_task:
                    raise ValueError(f"Task with id {task_id} is not found!")
                tag_text = kwargs.get("text") or kwargs.get("tags")
                tag_info = {"text": tag_text}
                tag = self.repo.list(BaseTag, tag_info)
                if not tag:
                    tag = BaseTag(**tag_info)
                    self.repo.add(tag)
                    session.commit()
                    tag_id = tag.id
                else:
                    tag_id = tag[0].id
                existing_task_tag = self.repo.list(TaskTag, {
                    "task": task_id,
                    "tag": tag_id
                })
                if not existing_task_tag:
                    task_ids = get_ids(task_id)
                    for task_id in task_ids:
                        obj = TaskTag(id=task_id, tag_id=tag_id)
                        self.repo.add(obj)
                    session.commit()
            elif entity_type == "projects":
                project_id = kwargs["id"]
                existing_project = self.repo.list(Project, {"id": project_id})
                if not existing_project:
                    raise ValueError(
                        f"Project with id {project_id} is not found!")
                tag = self.repo.list(BaseTag, {"text": kwargs["text"]})
                if not tag:
                    tag = BaseTag(**kwargs)
                    self.repo.add(tag)
                    session.commit()
                    tag_id = tag.id
                else:
                    tag_id = tag[0].id

                existing_project_tag = self.repo.list(ProjectTag, {
                    "project": project_id,
                    "tag": tag_id
                })
                if not existing_project_tag:
                    project_ids = get_ids(project_id)
                    for project_id in project_ids:
                        obj = ProjectTag(id=project_id, tag_id=tag_id)
                        self.repo.add(obj)
                    session.commit()
        elif command == "comment":
            if entity_type == "tasks":
                existing_task = self.repo.list(Task, {"id": kwargs["id"]})
                if not existing_task:
                    raise ValueError(
                        f"Task with id {kwargs['id']} is not found!")
                obj = TaskCommentary(**kwargs)
                self.repo.add(obj)
                session.commit()
            elif entity_type == "projects":
                existing_project = self.repo.list(Project,
                                                  {"id": kwargs["id"]})
                if not existing_project:
                    raise ValueError(
                        f"Project with id {kwargs['id']} is not found!")
                obj = ProjectCommentary(**kwargs)
                self.repo.add(obj)
                session.commit()
            elif entity_type == "epics":
                epic = self.repo.list(Epic, {"id": kwargs["id"]})
                if not epic:
                    raise ValueError(
                        f"Epic with id {kwargs['id']} is not found!")
                obj = EpicCommentary(**kwargs)
                self.repo.add(obj)
                session.commit()
            elif entity_type == "stories":
                epic = self.repo.list(Story, {"id": kwargs["id"]})
                if not epic:
                    raise ValueError(
                        f"Story with id {kwargs['id']} is not found!")
                obj = StoryCommentary(**kwargs)
                self.repo.add(obj)
                session.commit()
            elif entity_type == "sprints":
                sprint = self.repo.list(Sprint, {"id": kwargs["id"]})
                if not sprint:
                    raise ValueError(
                        f"Sprint with id {kwargs['id']} is not found!")
                obj = SprintCommentary(**kwargs)
                self.repo.add(obj)
                session.commit()
        elif command == "delete":
            if entity not in (Task, ):
                raise ValueError("'delete' operation only allowed for tasks!")
            task_ids = get_ids(kwargs.get("id"))
            for task_id in task_ids:
                if not self.repo.list(Task, {"id": task_id}):
                    exit(f"Task id {task_id} is not found")
                if epic_id := kwargs.get("epic_id"):
                    epic = self.repo.list(Epic, {"id": epic_id})
                    if not epic:
                        exit(f"Epic id {epic_id} is not found")
                    if not (epic_task := self.repo.list(
                            EpicTask, {
                                "task": task_id,
                                "epic": epic_id
                            })):
                        exit("task is not in epic")
                    self.repo.delete(EpicTask, epic_task[0].id)
                if story_id := kwargs.get("story_id"):
                    story = self.repo.list(Story, {"id": story_id})
                    if not story:
                        exit(f"Story id {story_id} is not found")
                    if not (story_task := self.repo.list(
                            StoryTask, {
                                "task": task_id,
                                "story": story_id
                            })):
                        exit("task is not in story")
                    self.repo.delete(StoryTask, story_task[0].id)
                if sprint_id := kwargs.get("sprint_id"):
                    sprint = self.repo.list(Sprint, {"id": sprint_id})
                    if not sprint:
                        exit(f"Sprint id {sprint_id} is not found")
                    if sprint[0].status.name == "COMPLETED":
                        exit("Cannot add task to a finished sprint")
                    if not (sprint_task := self.repo.list(
                            SprintTask, {
                                "task": task_id,
                                "sprint": sprint_id
                            })):
                        exit("task is not in sprint")
                    self.repo.delete(SprintTask, sprint_task[0].id)
            session.commit()
        elif command == "add":
            if entity not in (Task, ):
                raise ValueError("'add' operation only allowed for tasks!")
            task_ids = get_ids(kwargs.get("id"))
            for task_id in task_ids:
                if not self.repo.list(Task, {"id": task_id}):
                    exit(f"Task id {task_id} is not found")

                if epic_id := kwargs.get("epic_id"):
                    epic = self.repo.list(Epic, {"id": epic_id})
                    if not epic:
                        exit(f"Epic id {epic_id} is not found")
                    obj = EpicTask(task=task_id, epic=epic_id)
                    if self.repo.list(EpicTask, {
                            "task": obj.task,
                            "epic": obj.epic
                    }):
                        exit("task already added to epic")
                    self.repo.add(obj)
                if story_id := kwargs.get("story_id"):
                    story = self.repo.list(Story, {"id": story_id})
                    if not story:
                        exit(f"Story id {story_id} is not found")
                    obj = StoryTask(task=task_id, story=story_id)
                    if self.repo.list(StoryTask, {
                            "task": obj.task,
                            "story": obj.story
                    }):
                        exit("task already added to story")
                    self.repo.add(obj)
                if sprint_id := kwargs.get("sprint_id"):
                    sprint = self.repo.list(Sprint, {"id": sprint_id})
                    if not sprint:
                        exit(f"Sprint id {sprint_id} is not found")
                    if sprint[0].status.name == "COMPLETED":
                        exit("Cannot add task to a finished sprint")
                    obj = SprintTask(task=task_id,
                                     sprint=sprint_id,
                                     is_active_link=True)
                    if self.repo.list(SprintTask, {
                            "task": obj.task,
                            "sprint": obj.sprint
                    }):
                        exit("task already added to sprint")
                    self.repo.add(obj)
                    sprint_task_id = obj.id
                else:
                    sprint_task_id = None
                if story_points := kwargs.get("story_points"):
                    if not sprint_task_id:
                        sprint_task = self.execute("get", "sprint_tasks",
                                                   {"task": task_id})
                        if not sprint_task:
                            exit(
                                f"Task id {task_id} is not part of any sprint")
                        else:
                            sprint_task_id = sprint_task[0].id
                    self.repo.update(SprintTask, sprint_task_id,
                                     {"story_points": story_points})
            session.commit()
        elif command == "create":
            kwargs["created_by"] = services.lookup_user_id(
                self.config.get("user"), self.repo)
            obj = entity(**kwargs)
            if entity in (Task, Project):
                if (existing_obj := self.repo.list(entity,
                                                   {"name": obj.name})):
                    print("Found existing entity\n")
                    existing_id = str(existing_obj[0].id)
                    self.execute("show", entity_type, {"id": existing_id})
                    answer = input(
                        "Do you want to create entity anyway? [Y/n] ")
                    if answer.lower() != "y":
                        exit()
            self.repo.add(obj)
            session.commit()
            if tag_text := kwargs.get("tags"):
                self.execute("tag", entity_type, {
                    "id": obj.id,
                    "text": tag_text
                })
            if collaborator_name := kwargs.get("collaborators"):
                self.execute("collaborate", entity_type, {
                    "id": obj.id,
                    "name": collaborator_name
                })
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
                            if entity_type in ("tasks", "projects"):
                                for key, value in new_kwargs.items():
                                    try:
                                        old_value = old_settings[key].name
                                    except:
                                        old_value = old_settings[key]
                                    if entity_type == "projects":
                                        event = ProjectEvent
                                    elif entity_type == "tasks":
                                        event = TaskEvent
                                    self.repo.add(
                                        event(task, key, old_value, value,
                                              now))
                        else:
                            print(
                                "No changes were proposed to the existing entity"
                            )
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
        elif command == "start":
            sprint_id = kwargs.get("id")
            kwargs.update({"status": "ACTIVE"})
            self.execute("update", "sprints", kwargs)
            [sprint] = self.execute("get", "sprints", {"id": sprint_id})
            for sprint_task in sprint.sprint_tasks:
                task = sprint_task.tasks
                task_params = {"id": task.id}
                if task.status.name == "BACKLOG":
                    task_params.update({"status": "TODO"})
                if not task.due_date or task.due_date > sprint.end_date:
                    task_params.update({"due_date": sprint.end_date})
                self.execute("update", "tasks", task_params)
        elif command == "show":
            print_options = printer.PrintOptions(
                show_history=bool(kwargs.get("show_history")),
                show_commentaries=bool(kwargs.get("show_commentaries")),
                show_completed=bool(kwargs.get("show_completed"))
            )
            if not (task_id := kwargs.get("id")):
                if entity_type == "sprints":
                    active_sprint = self.repo.list(Sprint, {"status": "ACTIVE"})
                    if len(active_sprint) == 1:
                        task_id = active_sprint[0].id
                    else:
                        exit("More than 1 active sprint, please specify the sprint_id")
            tasks = get_ids(task_id)
            for task in tasks:
                if task.isdigit():
                    entities = self.repo.list(entity, {"id": task})
                else:
                    entities = self.repo.list(entity, {"name": task})
                self.printer.print_entity(
                    task, entity_type, entities, self.repo, print_options)
                logger.info("<show> %s: %s", entity_type, task_id)
            return entities, None, None
        elif command == "done":
            if entity_type not in ("tasks", "sprints"):
                raise ValueError("can complete only tasks and sprints")
            elif entity_type == "tasks":
                kwargs.update({"status": "DONE"})
                self.execute("update", entity_type, kwargs)
                self.console.print(
                    "[green]Yay! You've just completed a task![/green]")
            elif entity_type == "sprints":
                kwargs.update({"status": "COMPLETED"})
                [sprint] = self.execute("get", "sprints",
                                        {"id": kwargs.get("id")})
                sprint.complete(sprint.sprint_tasks)
                self.execute("update", entity_type, kwargs)
        elif command == "track":
            if entity_type != "tasks":
                raise ValueError("can track only tasks")
            if "hours" in kwargs and "minutes" in kwargs:
                exit("specify only -H (hours) or -M (minutes) value")
            if "hours" in kwargs or "minutes" in kwargs:
                if "hours" in kwargs:
                    kwargs["time_spent_minutes"] = float(kwargs["hours"]) * 60
                    del kwargs["hours"]
                else:
                    kwargs["time_spent_minutes"] = float(kwargs["minutes"])
                    del kwargs["minutes"]
                kwargs["task"] = kwargs["id"]
                del kwargs["id"]
                self.execute("create", "time_entry", kwargs)
            else:
                exit("tracking missing -H (hours) or -M (minutes) value")
        else:
            raise ValueError(f"Uknown command: {command}")

    def _read_config(self) -> Dict[str, Any]:
        with open(f"{self.home_dir}/.terka/config.yaml", "r",
                  encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config


def get_ids(ids: Union[str, int]) -> List[Union[int, str]]:
    id_string = str(ids)
    if "," in id_string:
        ids = id_string.split(",")
    elif ".." in id_string:
        task_range = id_string.split("..")
        ids = range(int(task_range[0]), int(task_range[1]) + 1)
    else:
        ids = [id_string]
    return ids
