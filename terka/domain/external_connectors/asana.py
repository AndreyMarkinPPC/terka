from __future__ import annotations
from datetime import datetime
from dataclasses import dataclass
import logging
import os

from terka.domain.entities.commentary import TaskCommentary
from terka.domain.entities.task import Task
from terka.service_layer import exceptions

try:
    import asana
except ImportError:
    raise exceptions.TerkaException(
        "Please install `terka[asana]` to connect to asana")


@dataclass
class AsanaTask:
    id: int
    project: int
    asana_task_id: str
    sync_date: datetime


@dataclass
class AsanaProject:
    id: int
    asana_project_id: str
    sync_date: datetime


@dataclass
class AsanaUser:
    id: int
    asana_user_id: str


class AsanaMigrator:

    status_mapping = {
        "BACKLOG": "Backlog",
        "TODO": "To Do",
        "IN_PROGRESS": "In progress",
        "REVIEW": "Waiting",
        "DONE": "Done",
        "DELETED": "Done"
    }

    reversed_status_mapping = {
        "Backlog": "BACKLOG",
        "To Do": "TODO",
        "In progress": "IN_PROGRESS",
        "Waiting": "Review",
        "Done": "DONE",
    }

    def __init__(
        self,
        client: asana.ApiClient,
        assignee: str | None = os.getenv("ASANA_USER")
    ) -> None:
        self.client = client
        self.assignee = assignee
        self.tasks = asana.TasksApi(client)
        self.sections = asana.SectionsApi(client)
        self.stories = asana.StoriesApi(client)

    def migrate_task(
            self,
            asana_project_id: str,
            task: Task,
            sync_info: dict[str, str] | None = None,
            mapped_external_users: dict[int, str] | None = None) -> str | None:
        try:
            if sync_info:
                asana_task_id = self.update_existing_asana_task(
                    asana_project_id, task, sync_info, mapped_external_users)
            else:
                asana_task_id = self.create_new_asana_task(
                    asana_project_id, task, sync_info, mapped_external_users)
            return asana_task_id
        except Exception as e:
            logging.error(
                f"Failed to migrate task {task.id} to Asana, context: {e}")
            return None

    def update_existing_asana_task(
            self, asana_project_id: str, task: Task, sync_info: dict[str, str],
            mapped_external_users: dict[int, str]) -> str:
        if not (asana_task_id := sync_info.get("asana_task_id")):
            raise exceptions.TerkaException(
                f"Task {task.id} is not sync with Asana")
        opts = {"opt_fields": "name,notes,due_on,assignee"}
        asana_task = self.tasks.get_task(task_gid=asana_task_id, opts=opts)
        update_dict = self._find_task_element_changes(asana_task, task,
                                                      mapped_external_users)
        self.tasks.update_task(task_gid=asana_task_id,
                               body={"data": update_dict},
                               opts=opts)
        self._update_task_status(asana_task_id, task)
        if commentaries := task.commentaries:
            self._migrate_comments_for_task(asana_task_id, commentaries,
                                            sync_info.get("sync_date"))
        logging.info(f"Task {task.id} is updated in Asana")
        return asana_task_id

    def create_new_asana_task(self, asana_project_id: str, task: Task,
                              sync_info: dict,
                              mapped_external_users: dict) -> str:
        asana_task_dict = {
            "name": task.name,
            "notes": task.description or "",
            "projects": [asana_project_id]
        }
        if assignee := task.assignee:
            asana_task_dict["assignee"] = mapped_external_users.get(
                assignee) or self.assignee
        elif self.assignee:
            asana_task_dict["assignee"] = self.assignee
        if due_date := task.due_date:
            asana_task_dict["due_on"] = due_date.strftime("%Y-%m-%d")
        opts = {"opt_fields": "name,projects,due_on,assignee"}
        asana_task = self.tasks.create_task(body={"data": asana_task_dict},
                                            opts=opts)
        asana_task_id = asana_task.get("gid")
        asana_task_status = self.status_mapping[task.status.name]
        self._update_task_status(asana_task_id, task)
        if commentaries := task.commentaries:
            self._migrate_comments_for_task(asana_task_id, commentaries)
        logging.info(f"Task {task.id} is migrated to Asana")
        return asana_task_id

    def _update_task_status(self, asana_task_id: str, task: Task) -> None:
        asana_task_status = self.status_mapping[task.status.name]
        opts = {"body": {"data": {"task": asana_task_id}}}
        self.sections.add_task_for_section(
            section_gid=self.task_statuses[asana_task_status], opts=opts)
        if task.status.name in ("DONE", "DELETED"):
            opts = {"opt_fields": "completed"}
            self.tasks.update_task(task_gid=asana_task_id,
                                   body={"data": {
                                       "completed": True
                                   }},
                                   opts=opts)

    def _migrate_comments_for_task(
            self,
            asana_task_id: str,
            comments: list[TaskCommentary],
            last_sync_date: datetime.datetime | None = None) -> None:
        if last_sync_date:
            comments = [c for c in comments if c.date > last_sync_date]
        else:
            last_sync_date = datetime.fromtimestamp(0)

        opts = {"opt_fields": "text"}
        for comment in comments:
            if comment and comment.date > last_sync_date:
                self.stories.create_story_for_task(
                    task_gid=asana_task_id,
                    body={"data": {
                        "text": comment.text
                    }},
                    opts=opts)

    def _find_task_element_changes(
            self, asana_task: dict, task: Task,
            mapped_external_users: dict) -> dict[str, str]:
        update_dict: dict[str, str] = {}
        if task.name != asana_task.get("name"):
            update_dict["name"] = task.name
        if task.description != asana_task.get("notes", None):
            update_dict["notes"] = task.description or ""
        if asana_assignee := mapped_external_users.get(task.assignee):
            if asana_assignee != asana_task.get("assignee"):
                update_dict["assignee"] = {
                    "gid": asana_assignee,
                    "resource_type": "user"
                }
        if not task.due_date:
            update_dict["due_on"] = None
        else:
            due_date = task.due_date.strftime("%Y-%m-%d")
            if due_date != asana_task.get("due_on"):
                update_dict["due_on"] = due_date
        return update_dict

    def load_task_statuses(self, asana_project_id: str) -> None:
        sections = self.sections.get_sections_for_project(
            asana_project_id, opts={"opt_fields": "name,gid"})
        statuses = {}
        for section in sections:
            statuses[section.get("name")] = section.get("gid")
        self.task_statuses = statuses
