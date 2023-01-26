from typing import Dict, List, Optional

from datetime import datetime, timedelta
import re


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
                    new_dict[key] = kwargs[i+1]
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
            new_dict.get("id") if entity == "commentaries" else None,
            "name": new_dict.get("n") or new_dict.get("name"),
            "status": new_dict.get("s") or new_dict.get("status"),
            "project": new_dict.get("p") or new_dict.get("project"),
            "assignee": new_dict.get("a") or new_dict.get("assignee"),
            "due_date": new_dict.get("d") or new_dict.get("due-date"),
            "description": new_dict.get("desc") or new_dict.get("description"),
            "text": new_dict.get("t") or new_dict.get("text"),
            "priority": new_dict.get("priority"),
            "overdue": new_dict.get("overdue"),
            "stale": new_dict.get("stale")
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
            if entity ==  "commentaries":
                task_dict["task_id"] = str(config.get("task_id"))

    if not task_dict.get("project") and config.get("project_name"):
        task_dict["project"] = config.get("project_name")
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
    if date.startswith("+"):
        due_date = datetime.now().date() + timedelta(days = float(date[1:]))
        return due_date.strftime("%Y-%m-%d")
    if date.startswith("-"):
        due_date = datetime.now().date() - timedelta(days = float(date[1:]))
        return due_date.strftime("%Y-%m-%d")
    return date
