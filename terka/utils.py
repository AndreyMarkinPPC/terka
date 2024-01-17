from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import re
import yaml

from terka.domain import commands
from terka.service_layer import exceptions, services
from terka.adapters.repository import AbsRepository


def create_task_dict(kwargs: list[str]) -> dict[str, str]:
    new_dict = {}
    for i, kwarg in enumerate(kwargs):
        if i == 0 and not kwarg.startswith("-"):
            new_dict["id"] = kwarg
        arr = kwarg.split("=")
        if len(arr) == 2:
            key = re.sub("^-+", "", arr[0])
            new_dict[key] = arr[1]
        else:
            key = arr[0]
            if i < len(kwargs) and key.startswith("-"):
                key = re.sub("^-+", "", key)
                try:
                    new_dict[key] = kwargs[i + 1]
                except IndexError:
                    new_dict[key] = True
    return new_dict


def format_task_dict(config: dict, entity: str,
                     kwargs: dict) -> dict | list[dict]:
    _new_dict = create_task_dict(kwargs)
    if file_path := _new_dict.get("f"):
        task_dicts: dict = []
        with open(file_path, "r") as f:
            lines = [line.rstrip() for line in f if line.rstrip()]
            for line in lines:
                entry = line.strip().split("::")
                if len(entry) == 3:
                    task_dict = {
                        "project": entry[0],
                        "name": entry[1],
                        "description": entry[2]
                    }
                elif len(entry) == 2:
                    task_dict = {
                        "project": entry[0],
                        "name": entry[1],
                    }
                elif len(entry) == 1:
                    task_dict = {"name": entry[0]}
                task_dicts.append(task_dict)
        return task_dicts
    if len(kwargs) > 1:
        new_dict = create_task_dict(kwargs)
        task_dict = {
            "id":
            new_dict.get("id") if entity != "commentaries" else None,
            "task_id":
            new_dict.get("task_id") or new_dict.get("task-id"),
            "name":
            new_dict.get("n") or new_dict.get("name"),
            "num_log_entries":
            new_dict.get("L") or new_dict.get("lines"),
            "status":
            new_dict.get("s") or new_dict.get("status"),
            "project":
            new_dict.get("p") or new_dict.get("project")
            or new_dict.get("project_name"),
            "workspace":
            new_dict.get("w") or new_dict.get("workspace")
            or new_dict.get("workspace_name") or config.get("workspace"),
            "assignee":
            new_dict.get("a") or new_dict.get("assignee"),
            "due_date":
            new_dict.get("d") or new_dict.get("due-date"),
            "description":
            new_dict.get("desc") or new_dict.get("description"),
            "text":
            new_dict.get("t") or new_dict.get("text"),
            "tag":
            new_dict.get("tag") or new_dict.get("tags"),
            "collaborator":
            new_dict.get("collaborator") or new_dict.get("collaborators"),
            "all":
            new_dict.get("all") or new_dict.get("show-completed"),
            "priority":
            new_dict.get("priority"),
            "overdue":
            new_dict.get("overdue"),
            "stale":
            new_dict.get("stale"),
            "goal":
            new_dict.get("goal"),
            "start_date":
            convert_date(new_dict.get("start-date")),
            "end_date":
            convert_date(new_dict.get("end-date")),
            "sprint":
            new_dict.get("to-sprint") or new_dict.get("from-sprint")
            or new_dict.get("sprint") or new_dict.get("sprints"),
            "story":
            new_dict.get("to-story") or new_dict.get("from-story")
            or new_dict.get("story") or new_dict.get("stories"),
            "epic":
            new_dict.get("to-epic") or new_dict.get("from-epic")
            or new_dict.get("epic") or new_dict.get("epics"),
            "story_points":
            new_dict.get("story-points"),
            "hours":
            new_dict.get("H"),
            "minutes":
            new_dict.get("M"),
            "show_history":
            new_dict.get("show-history"),
            "show_commentaries":
            new_dict.get("show-commentaries") or new_dict.get("show-comments"),
            "show_notes":
            new_dict.get("show-notes"),
            # "epics":
            # new_dict.get("epics"),
            # "stories":
            # new_dict.get("stories"),
            # "tasks":
            # new_dict.get("tasks"),
            "external_project":
            new_dict.get("external-project"),
            "external_task":
            new_dict.get("external-task"),
            "external_user":
            new_dict.get("external-user"),
            "show_viz":
            new_dict.get("show-viz"),
            "file":
            new_dict.get("file") or new_dict.get("f"),
            "columns":
            new_dict.get("columns") or new_dict.get("c"),
            "expand":
            new_dict.get("expand"),
            "no-expand":
            new_dict.get("no-expand"),
            "comment":
            new_dict.get("comment"),
        }
        if "--sort" in kwargs:
            sort_index = kwargs.index("--sort")
            sort_statement = kwargs[sort_index:sort_index + 2]
            task_dict.update(create_task_dict(sort_statement))
    elif len(kwargs) == 1:
        if "overdue" in kwargs[0]:
            task_dict = {"overdue": "overdue"}
        elif "stale" in kwargs[0]:
            task_dict = {"stale": 7}
        elif "all" in kwargs[0]:
            task_dict = {"all": "all"}
        elif kwargs[0] == "--expand":
            task_dict = {"expand": "True"}
        elif kwargs[0] == "--no-expand":
            task_dict = {"no-expand": "True"}
        elif "tasks" in kwargs[0]:
            task_dict = {"tasks": True}
        else:
            task_dict = {"id": kwargs[0]}
    else:
        task_dict = {}

    if task_dict and isinstance(task_dict, dict):
        task_dict = {k: v for k, v in task_dict.items() if v}

    if "status" in task_dict:
        task_dict["status"] = convert_status(task_dict["status"])
    if "due_date" in task_dict:
        task_dict["due_date"] = convert_date(task_dict["due_date"])
    if not task_dict.get("id"):
        if (id := config.get("task_id")):
            if entity != "commentaries":
                task_dict["id"] = str(config.get("task_id"))
            if entity == "commentaries":
                task_dict["task_id"] = str(config.get("task_id"))

    if not task_dict.get("project") and config.get("project_name"):
        task_dict["project"] = config.get("project_name")
    if any(key in task_dict.keys() for key in ("epics", "stories", "tasks")):
        task_dict["partial_project_view"] = True
    task_dict["expand_table"] = not task_dict.get("no-expand", False)
    task_dict["sync"] = not _new_dict.get("no-sync", False)
    task_dict["show_completed"] = task_dict.get("all", False)
    if tags := task_dict.get("tag"):
        task_dict["tags"] = tags
    return task_dict


def convert_status(status: str) -> str:
    conversion_dict = {
        "b": "BACKLOG",
        "t": "TODO",
        "i": "IN_PROGRESS",
        "r": "REVIEW",
        "d": "DONE",
        "x": "DELETED",
        "a": "ACTIVE",
        "p": "PLANNED",
        "c": "COMPLETED",
        "o": "ON_HOLD"
    }
    statuses = []
    for status in status.split(","):
        if status not in conversion_dict.values():
            statuses.append(conversion_dict.get(status[0].lower(), "BACKLOG"))
        else:
            statuses.append(status)
    return ",".join(statuses)


def convert_date(date: str):
    if not date:
        return date
    if date.startswith("+"):
        due_date = datetime.now().date() + timedelta(days=float(date[1:]))
        return due_date.strftime("%Y-%m-%d")
    if date.startswith("-"):
        due_date = datetime.now().date() - timedelta(days=float(date[1:]))
        return due_date.strftime("%Y-%m-%d")
    return date


def process_command(command: str, config: dict,
                    repo: AbsRepository) -> tuple[str, str, dict]:
    task_dict = {}
    task_list = []
    entity = None
    command, *rest = command.split(" ", maxsplit=2)
    if command[0] == "q":
        exit()
    if rest:
        entity, *task_dict = rest
        if task_dict:
            task_list = re.split(r'\s+(?=[^"]*(?:"[^"]*"[^"]*)*$)',
                                 task_dict[0])
            task_list = [
                re.sub("['|\"]", "", element) for element in task_list
            ]
        task_dict = format_task_dict(config, entity, task_list)
    else:
        task_dict = {}
    task_dict = update_task_dict(task_dict, repo)
    return command, entity, task_dict


def update_task_dict(task_dict: dict[str, str],
                     repo: AbsRepository) -> dict[str, str]:
    if (project := task_dict.get("project")):
        project_id = services.lookup_project_id(project, repo)
        task_dict["project"] = project_id
    if (workspace := task_dict.get("workspace")):
        workspace_id = services.lookup_workspace_id(workspace, repo)
        task_dict["workspace"] = workspace_id
    if (assignee := task_dict.get("assignee")):
        task_dict["assignee"] = services.lookup_user_id(assignee, repo)
    task_dict = convert_date_in_task_dict(task_dict)
    return task_dict


def convert_date_in_task_dict(task_dict):
    for key, value in task_dict.items():
        if key.endswith("date"):
            if value == "None":
                task_dict[key] = None
            elif value == "today":
                task_dict[key] = datetime.today()
            else:
                task_dict[key] = datetime.strptime(
                    value, "%Y-%m-%d") if isinstance(value, str) else value
    return task_dict


def format_command(command: str) -> str:
    if command == "d":
        command = input("specify: de[lete], do[ne]")
    if "list".startswith(command):
        return "list"
    if "show".startswith(command):
        return "show"
    if "create".startswith(command):
        return "create"
    if "update".startswith(command):
        return "update"
    if "delete".startswith(command):
        return "delete"
    if "edit".startswith(command):
        return "edit"
    if "comment".startswith(command):
        return "comment"
    return command


def create_command(command: str, entity: str,
                   task_dict: dict) -> commands.Command:
    command = format_command(command)
    entity = format_entity(entity)
    _command = f"{command.capitalize()}{entity.capitalize()}"
    try:
        return getattr(commands, _command).from_kwargs(**task_dict)
    except AttributeError as e:
        print(e)
        raise exceptions.TerkaCommandException(
            f"Unknown command: `terka {command} {entity}`")


def format_entity(entity: str) -> str:
    if entity in "tasks":
        return "task"
    if entity in "projects":
        return "project"
    if entity in "sprints":
        return "sprint"
    if entity in "notes":
        return "note"
    if entity in "epics":
        return "epic"
    if entity == "story" or entity in "stories":
        return "story"
    if entity in "users":
        return "user"
    if entity in "tags":
        return "tag"
    if entity in "workspaces":
        return "workspace"
    return entity


def load_config(home_dir: str) -> dict:
    try:
        with open(f"{home_dir}/.terka/config.yaml", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        raise exceptions.TerkaInitError(
            "call `terka init` to initialize terka")


@dataclass
class FilterOptions:
    id: str | None = None
    project: str | None = None
    status: str | None = None
    priority: str | None = None
    due_date: str | None = None
    created_days_ago: int | None = None
    assignee: str | None = None
    # TODO: Attributes below can be passed as ids after doing the prefiltering
    collaborator: str | None = None
    tags: str | None = None
    sprint: str | None = None
    story: str | None = None
    epic: str | None = None

    @classmethod
    def from_kwargs(cls, **kwargs: dict):
        cls_dict = {}
        for k, v in kwargs.items():
            if k in cls.__match_args__ and v:
                if len(multiple_conditions := v.split(",")) > 1:
                    v = multiple_conditions
                elif len(range_condition := v.split("..")) > 1:
                    start, end = range_condition
                    if not end:
                        end = int(start) + 100
                    v = list(range(int(start), int(end) + 1))
                cls_dict[k] = v
        return cls(**cls_dict)

    def __bool__(self) -> bool:
        return any(asdict(self).values())

    def get_only_set_attributes(self) -> dict:
        return {key: value for key, value in asdict(self).items() if value}
