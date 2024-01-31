from __future__ import annotations
from datetime import datetime

from terka.domain import entities


def projects(uow) -> list[dict]:
    with uow:
        return [t.to_dict() for t in uow.tasks.list(entities.project.Project)]


def project(uow, project_id: int) -> dict:
    with uow:
        if not (project := uow.tasks.get_by_id(entities.project.Project,
                                               project_id)):
            return {}
        result = project.to_dict()
        for column in ("open_tasks", "backlog", "overdue_tasks", "review",
                       "in_progress", "done"):
            result[column] = len(getattr(project, column))
        result["workspace"] = project.workspace_.name
        return result


def project_tasks(uow, project_id: int) -> list[dict]:
    with uow:
        if not (project := uow.tasks.get_by_id(entities.project.Project,
                                               project_id)):
            return []
        if tasks := project.tasks:
            return [task.to_dict() for task in project.tasks]
        return []


def tasks(uow) -> list[dict]:
    with uow:
        return [t.to_dict() for t in uow.tasks.list(entities.task.Task)]


def task(uow, task_id: int) -> dict:
    with uow:
        if not (task := uow.tasks.get_by_id(entities.task.Task, task_id)):
            return {}
        result = task.to_dict()
        if commentaries := task.commentaries:
            commentaries = [comment.to_dict() for comment in commentaries]
        result["commentaries"] = commentaries
        return result


def task_commentaries(uow, task_id: int) -> list[dict]:
    with uow:
        if not (task := uow.tasks.get_by_id(entities.task.Task, task_id)):
            return []
        if commentaries := task.commentaries:
            return [comment.to_dict() for comment in commentaries]
        return []


def workspaces(uow) -> list[dict]:
    with uow:
        return [
            t.to_dict() for t in uow.tasks.list(entities.workspace.Workspace)
        ]


def workspace(uow, workspace_id: int) -> dict:
    with uow:
        if not (workspace := uow.tasks.get_by_id(entities.workspace.Workspace,
                                                 workspace_id)):
            return {}
        if projects := workspace.projects:
            projects = [project.to_dict() for project in workspace.projects]
            result = workspace.to_dict()
        result["projects"] = projects
        return result


def workspace_projects(uow, workspace_id: int) -> list[dict]:
    with uow:
        if not (workspace := uow.tasks.get_by_id(entities.workspace.Workspace,
                                                 workspace_id)):
            return []
        if projects := workspace.projects:
            return [project.to_dict() for project in workspace.projects]
        return []


def epics(uow) -> list[dict]:
    with uow:
        return [t.to_dict() for t in uow.tasks.list(entities.epic.Epic)]


def epic(uow, epic_id: int) -> dict:
    with uow:
        if not (epic := uow.tasks.get_by_id(entities.epic.Epic, epic_id)):
            return {}
        if tasks := epic.tasks:
            tasks = [task.tasks.to_dict() for task in epic.tasks]
            result = epic.to_dict()
        result["tasks"] = tasks
        return result


def epic_tasks(uow, epic_id: int) -> list[dict]:
    with uow:
        if not (epic := uow.tasks.get_by_id(entities.epic.Epic, epic_id)):
            return []
        if tasks := epic.tasks:
            return [task.tasks.to_dict() for task in epic.tasks]
        return []


def stories(uow) -> list[dict]:
    with uow:
        return [t.to_dict() for t in uow.tasks.list(entities.story.Story)]


def story(uow, story_id: int) -> dict:
    with uow:
        if not (story := uow.tasks.get_by_id(entities.story.Story, story_id)):
            return {}
        if tasks := story.tasks:
            tasks = [task.tasks.to_dict() for task in story.tasks]
            result = story.to_dict()
        result["tasks"] = tasks
        return result


def story_tasks(uow, story_id: int) -> list[dict]:
    with uow:
        if not (story := uow.tasks.get_by_id(entities.story.Story, story_id)):
            return []
        if tasks := story.tasks:
            return [task.tasks.to_dict() for task in story.tasks]
        return []


def sprints(uow) -> list[dict]:
    with uow:
        return [t.to_dict() for t in uow.tasks.list(entities.sprint.Sprint)]


def sprint(uow, sprint_id: int) -> dict:
    with uow:
        if not (sprint := uow.tasks.get_by_id(entities.sprint.Sprint,
                                              sprint_id)):
            return {}
        if tasks := sprint.tasks:
            tasks = [task.tasks.to_dict() for task in sprint.tasks]
            result = sprint.to_dict()
        result["tasks"] = tasks
        return result


def sprint_tasks(uow, sprint_id: int) -> list[dict]:
    with uow:
        if not (sprint := uow.tasks.get_by_id(entities.sprint.Sprint,
                                              sprint_id)):
            return []
        if tasks := sprint.tasks:
            return [task.tasks.to_dict() for task in sprint.tasks]
        return []


def users(uow) -> list[dict]:
    with uow:
        return [t.to_dict() for t in uow.tasks.list(entities.user.User)]


def user(uow, user_id: int) -> dict:
    with uow:
        if not (user := uow.tasks.get_by_id(entities.user.User, user_id)):
            return {}
        return user.to_dict()


def tags(uow) -> list[dict]:
    with uow:
        return [t.to_dict() for t in uow.tasks.list(entities.tag.BaseTag)]


def tag(uow, tag_id: int) -> dict:
    with uow:
        if not (tag := uow.tasks.get_by_id(entities.tag.BaseTag, tag_id)):
            return {}
        return tag.to_dict()


def sprint_task_ids(session,
                    sprint_id: int | None = None) -> list[dict[int, int]]:
    results = session.execute(
        """
    SELECT
        task, sprint
    FROM sprint_tasks
    WHERE
        sprint = :sprint_id
    """, dict(sprint_id=sprint_id))
    return [dict(r) for r in results]


def external_connectors_asana_projects(session) -> list[dict[int, str]]:
    results = session.execute("""
    SELECT
        id, asana_project_id, sync_date
    FROM 'external_connectors.asana.projects'
    """)
    return [dict(r) for r in results]


def external_connectors_asana_users(session) -> dict[int, str]:
    results = session.execute("""
    SELECT
        id, asana_user_id
    FROM 'external_connectors.asana.users'
    """)
    return {r.id: r.asana_user_id for r in results}


def external_connectors_asana_tasks(
        session,
        project_id: str) -> dict[int, dict[str, str | datetime | None]]:
    results = session.execute(
        """
    SELECT
        id, asana_task_id, sync_date
    FROM 'external_connectors.asana.tasks'
    WHERE project = :project_id
    """, dict(project_id=project_id))
    return {
        r.id: {
            "asana_task_id":
            r.asana_task_id,
            "sync_date":
            datetime.strptime(r.sync_date, "%Y-%m-%d %H:%M:%S.%f")
            if r.sync_date else None
        }
        for r in results
    }
