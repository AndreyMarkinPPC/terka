from typing import Any, Dict, List, Optional, Tuple

from datetime import datetime, timedelta
import re
from terka.service_layer import services
from terka.adapters.repository import AbsRepository


def create_task_dict(kwargs: List[str]) -> Dict[str, str]:
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


def format_task_dict(config, entity, kwargs) -> Dict[str, Optional[str]]:
    if len(kwargs) > 1:
        new_dict = create_task_dict(kwargs)
        task_dict = {
            "id":
            new_dict.get("id") if entity != "commentaries" else None,
            "task_id":
            new_dict.get("id") or new_dict.get("task_id") if entity == "commentaries" else None,
            "name":
            new_dict.get("n") or new_dict.get("name"),
            "num_log_entries": new_dict.get("L") or new_dict.get("lines"),
            "status":
            new_dict.get("s") or new_dict.get("status"),
            "project":
            new_dict.get("p") or new_dict.get("project") or new_dict.get("project_name"),
            "assignee":
            new_dict.get("a") or new_dict.get("assignee"),
            "due_date":
            new_dict.get("d") or new_dict.get("due-date"),
            "description":
            new_dict.get("desc") or new_dict.get("description"),
            "text":
            new_dict.get("t") or new_dict.get("text"),
            "tags":
            new_dict.get("tag") or new_dict.get("tags"),
            "collaborators":
            new_dict.get("collaborator") or new_dict.get("collaborators"),
            "all":
            new_dict.get("all"),
            "priority":
            new_dict.get("priority"),
            "overdue":
            new_dict.get("overdue"),
            "stale":
            new_dict.get("stale"),
            "goal": new_dict.get("goal"),
            "start_date":
            convert_date(new_dict.get("start-date")),
            "end_date":
            convert_date(new_dict.get("end-date")),
            "sprint_id": new_dict.get("to-sprint") or new_dict.get("from-sprint") or new_dict.get("sprint"),
            "story_id": new_dict.get("to-story") or new_dict.get("from-story") or new_dict.get("story"),
            "epic_id": new_dict.get("to-epic") or new_dict.get("from-epic") or new_dict.get("epic"),
            "story_points": new_dict.get("story-points"),
            "hours": new_dict.get("H"),
            "minutes": new_dict.get("M"),
            "show_history": new_dict.get("show-history"),
            "show_commentaries": new_dict.get("show-commentaries") or new_dict.get("show-comments"),
            "epics": new_dict.get("epics"),
            "stories": new_dict.get("stories"),
            "tasks": new_dict.get("tasks"),
            "external_project": new_dict.get("external-project"),
            "external_task": new_dict.get("external-task"),
        }
        if "--show-completed" in kwargs:
            task_dict.update({"show_completed": True})
        if "--sort" in kwargs:
            sort_statement = kwargs[kwargs.index("--sort"):]
            task_dict.update(create_task_dict(sort_statement))
    elif len(kwargs) == 1:
        if "overdue" in kwargs[0]:
            task_dict = {"overdue": "overdue"}
        elif "stale" in kwargs[0]:
            task_dict = {"stale": 7}
        elif "all" in kwargs[0]:
            task_dict = {"all": "all"}
        elif "show-completed" in kwargs[0]:
            task_dict = {"show_completed": True}
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
    return task_dict


def convert_status(status: str):
    conversion_dict = {
        "b": "BACKLOG",
        "t": "TODO",
        "i": "IN_PROGRESS",
        "r": "REVIEW",
        "d": "DONE",
        "x": "DELETED"
    }
    return conversion_dict.get(status[0].lower(), "BACKLOG")


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


def process_command(command: str, config: Dict[str, Any],
                    repo: AbsRepository) -> Tuple[str, str, Dict[Any, Any]]:
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


def update_task_dict(task_dict: Dict[str, str],
                     repo: AbsRepository) -> Dict[str, str]:
    if (project := task_dict.get("project")):
        project_id = services.lookup_project_id(project, repo)
        task_dict["project"] = project_id
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
                task_dict[key] = datetime.strptime(value, "%Y-%m-%d")
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
