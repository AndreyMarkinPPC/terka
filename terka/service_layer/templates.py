from typing import Type
from datetime import datetime, timedelta
import re
from subprocess import run
import tempfile

from terka.domain import models, _commands
from terka.utils import convert_date, convert_status


def new_task_template() -> str:
    return f"""
        # You are creating a task, enter below:
        ---
        status: BACKLOG
        name: 
        description: 
        project: 
        due_date: 
        priority: NORMAL
        sprint: 
        epic: 
        story: 
        tags: 
        collaborators: 
        """


def new_composite_template(entity) -> str:
    return f"""
        # You are creating {entity.__name__}, enter below:
        ---
        name: 
        description: 
        project: 
        """


def new_project_template() -> str:
    return f"""
        # You are creating new project, enter below:
        ---
        name: 
        description: 
        workspace: 
        """


def new_sprint_template() -> str:
    today = datetime.now()
    next_monday = (today +
                   timedelta(days=(7 - today.weekday()))).strftime("%Y-%m-%d")
    next_sunday = (today +
                   timedelta(days=(13 - today.weekday()))).strftime("%Y-%m-%d")
    return f"""
        # You are creating a sprint, enter below:
        ---
        goal: 
        description: 
        start_date: {next_monday}
        end_date:  {next_sunday}
        """


def start_sprint_template(sprint: models.sprint.Sprint) -> str:
    ...


def edit_sprint_template(sprint: models.sprint.Sprint) -> str:
    return f"""
        # You are editing sprint {sprint.id}, enter below:
        ---
        goal: {sprint.goal}
        start_date: {sprint.start_date}
        end_date: {sprint.end_date}
        """


def edited_task_template(task: models.task.Task,
                         project: str | None = None) -> str:
    return f"""
        # You are editing task {task.id}, enter below:
        ---
        status: {task.status.name}
        name: {task.name}
        description: {task.description if task.description else ""}
        project: {project or ""}
        sprints: {task.sprints[-1].sprint if task.sprints else ""}
        epics: {task.epics[-1].epic if task.epics else ""}
        stories: {task.stories[-1].story if task.stories else ""}
        tags: {task.tags.pop() if task.tags else ""}
        collaborators: {task.collaborators.pop() if task.collaborators else ""}
        time_spent: 0 (task total_time_spent {task.total_time_spent})
        comment: 
        """


def edited_project_template(task: models.project.Project,
                            workspace: int) -> str:
    return f"""
        # You are editing project {task.id}, enter below:
        ---
        status: {task.status.name}
        name: {task.name}
        description: {task.description if task.description else ""}
        workspace: {workspace}
        tags: {task.tags.pop() if task.tags else ""}
        collaborators: {task.collaborators.pop() if task.collaborators else ""}
        comment: 
        """


def completed_task_template(task: models.task.Task,
                            project: str | None = None) -> str:
    return f"""
        # You are closing task {task.id}, enter below:
        ---
        status: DONE 
        time_spent: 0 (task total_time_spent {task.total_time_spent})
        comment: 
        name: {task.name}
        project: {project or ""}
        description: {task.description if task.description else ""}
        sprints: {task.sprints[-1].sprint if task.sprints else ""}
        epics: {task.epics[-1].epic if task.epics else ""}
        stories: {task.stories[-1].story if task.stories else ""}
        tags: {task.tags.pop() if task.tags else ""}
        collaborators: {task.collaborators.pop() if task.collaborators else ""}
        """


def generate_message_template(entity,
                              kwargs: dict[str, str] | None = None) -> str:
    if not isinstance(entity, type):
        if isinstance(
                entity,
            (models.task.Task, models.story.Story, models.epic.Epic)):
            project = entity.project
        elif isinstance(entity, models.project.Project):
            project = entity.name
            workspace = entity.workspace
        if isinstance(entity, models.sprint.Sprint):
            if not kwargs:
                message_template = new_sprint_template()
            else:
                message_template = edit_sprint_template(entity)
        elif isinstance(entity, models.project.Project):
            message_template = edited_project_template(entity, workspace)
        elif isinstance(entity, models.task.Task):
            message_template = edited_task_template(entity, project)
    else:
        if not kwargs:
            if entity == models.task.Task:
                message_template = new_task_template()
            if entity == models.project.Project:
                message_template = new_project_template()
            if entity == models.sprint.Sprint:
                message_template = new_sprint_template()
            if entity in (models.epic.Epic, models.story.Story):
                message_template = new_composite_template(entity)
        elif kwargs and kwargs.get("status"):
            message_template = completed_task_template(entity, project)
        else:
            message_template = edited_task_template(entity, project)
    return re.sub("\n +", "\n", message_template.lstrip())


def flush_message(entity):
    message_template = generate_message_template(entity)
    with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
        tf.write(message_template.encode("utf-8"))
        tf.flush()
        run(["vim", "+2", tf.name])
        tf.seek(0)
        new_entry = tf.read()
    return new_entry


def create_command_from_editor(
        entity, command) -> tuple[Type[_commands.Command], dict]:
    new_entry = flush_message(entity)
    new_entry = new_entry.decode("utf-8").rstrip()
    command_arguments: dict = {}
    if entity_id := entity.id:
        command_arguments.update({"id": entity_id})
    for i, row in enumerate(new_entry.split("\n")):
        if not row.startswith("#") and row:
            if row.startswith("--"):
                continue
            entry_type, *entry_value = row.split(": ", maxsplit=2)
            entry_value = ": ".join(entry_value)
            entry_value = entry_value.strip()
            if entry_type == "epics":
                command_arguments["epic_id"] = entry_value
            elif entry_type == "sprints":
                command_arguments["sprint_id"] = entry_value
            elif entry_type == "stories":
                command_arguments["story_id"] = entry_value
            if entry_type == "time_spent":
                time_spent = entry_value.split(" (")
                try:
                    time_spent = time_spent[0].strip()
                    time_spent_minutes = int(time_spent)
                    if time_spent_minutes:
                        command_arguments["hours"] = time_spent_minutes
                except Exception:
                    pass
            elif entry_type == "status":
                command_arguments["status"] = convert_status(entry_value)
            elif entry_type.endswith("date") and entry_value:
                entry_value = datetime.strptime(entry_value, "%Y-%m-%d")
                command_arguments[entry_type] = entry_value
            else:
                command_arguments[entry_type] = entry_value
    return command.from_kwargs(**command_arguments), command_arguments
