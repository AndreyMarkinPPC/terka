from typing import Dict, List, Optional


def time_spent(session, start_date: str,
               end_date: str) -> List[Dict[str, str]]:
    results = session.execute(
        """
    SELECT
        STRFTIME("%Y-%m-%d", creation_date) AS date,
        ROUND(SUM(time_spent_minutes) / 60, 2) AS time_spent_hours
    FROM time_tracker_entries
    WHERE
        creation_date >= :start_date
        AND creation_date <= :end_date
    GROUP BY 1
    """, dict(start_date=start_date, end_date=end_date))
    return [dict(r) for r in results]


def sprint_task_ids(session,
                    sprint_id: Optional[int] = None) -> List[Dict[int, int]]:
    results = session.execute(
        """
    SELECT
        task, sprint
    FROM sprint_tasks
    WHERE
        sprint = :sprint_id
    """, dict(sprint_id=sprint_id))
    return [dict(r) for r in results]


def external_connectors_asana_projects(session) -> List[Dict[int, str]]:
    results = session.execute(
        """
    SELECT
        id, asana_project_id
    FROM 'external_connectors.asana.projects'
    """)
    return [dict(r) for r in results]


def external_connectors_asana_tasks(session, project_id: str) -> List[Dict[int, str]]:
    results = session.execute(
        """
    SELECT
        id, asana_task_id
    FROM 'external_connectors.asana.tasks'
    WHERE project = :project_id
    """, dict(project_id=project_id))
    return [dict(r) for r in results]
