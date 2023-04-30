from typing import Dict, List, Optional
import pandas as pd
import numpy as np


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
    results = session.execute("""
    SELECT
        id, asana_project_id
    FROM 'external_connectors.asana.projects'
    """)
    return [dict(r) for r in results]


def external_connectors_asana_tasks(session,
                                    project_id: str) -> List[Dict[int, str]]:
    results = session.execute(
        """
    SELECT
        id, asana_task_id
    FROM 'external_connectors.asana.tasks'
    WHERE project = :project_id
    """, dict(project_id=project_id))
    return [dict(r) for r in results]


def status_changes(session, sprint_id: int):
    query = f"""
        SELECT DISTINCT T.id AS task,
        T.status AS current_status,
        STRFTIME("%Y-%m-%d", E.date) AS date,
        FIRST_VALUE(E.old_value) OVER (PARTITION BY T.id, STRFTIME("%Y-%m-%d", E.date) ORDER by E.date RANGE BETWEEN UNBOUNDED PRECEDING AND
                UNBOUNDED FOLLOWING) AS first_status_for_date,
        LAST_VALUE(E.new_value) OVER (PARTITION BY T.id, STRFTIME("%Y-%m-%d", E.date) ORDER by E.date RANGE BETWEEN UNBOUNDED PRECEDING AND
                UNBOUNDED FOLLOWING) AS last_status_for_date
        FROM tasks AS T
        LEFT JOIN (SELECT * FROM task_events WHERE type = "STATUS") AS E
            ON T.id = E.task
        WHERE T.id IN (SELECT task FROM sprint_tasks WHERE sprint = {sprint_id})

        """
    return pd.read_sql_query(query, session.get_bind()).replace({np.nan: None})
