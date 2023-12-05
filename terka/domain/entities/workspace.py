from collections import defaultdict
from datetime import date


class Workspace:

    def __init__(self,
                 name: str,
                 description: str | None = None,
                 created_by: str | None = None) -> None:
        self.name = name
        self.description = description
        self.created_by = created_by

    @property
    def total_time_spent(self) -> int:
        total_time_spent = 0
        for project in self.project:
            total_time_spent += project.total_time_spent
        return total_time_spent

    def daily_time_entries_hours(
            self,
            start_date: str | date | None = None,
            end_date: str | date | None = None,
            last_n_days: int | None = None) -> dict[str, float]:
        entries: dict[str, float] = defaultdict(float)
        for project in self.projects:
            project_entries = project.daily_time_entries_hours(
                start_date, end_date, last_n_days)
            for day, hours in project_entries.items():
                entries[day] += hours
        return entries

    def __str__(self):
        return f"<Workspace {self.id}>: {self.name}"
