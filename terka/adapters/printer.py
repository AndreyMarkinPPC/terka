from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import inspect
import rich
from rich.console import Console
from rich.table import Table


@dataclass
class PrintOptions:
    show_tasks: bool = True
    show_history: bool = False
    show_commentaries: bool = False
    show_completed: bool = False
    show_epics: bool = True
    show_stories: bool = True
    show_notes: bool = True
    show_viz: bool = False
    columns: str = ""
    expand_table: bool = True

    @classmethod
    def from_kwargs(cls, **kwargs: dict) -> "PrintOptions":
        return cls(**{k: kwargs[k] for k in kwargs if k in cls.__match_args__})


class Printer:

    def __init__(self):
        self.tui = None
        self.console = ConsolePrinter()


class ConsolePrinter:

    def __init__(self, box=rich.box.SIMPLE, config=None) -> None:
        self.console = Console()
        self.box = box
        self.config = config

    def print_new_object(self, obj, project=None):
        table = Table(box=self.box)
        attributes = self._get_attributes(obj)
        for column, value in attributes:
            if value:
                table.add_column(column)
        table.add_row(*list(zip(*attributes))[1])
        if table.row_count:
            self.console.print(f"Added new {obj.__class__.__name__}")
            self.console.print(table)

    def print_tag(self, entities):
        table = Table(box=self.box)
        for column in ("id", "text"):
            table.add_column(column)
        seen_tags = set()
        for entity in entities:
            text = entity.text
            if text and text not in seen_tags and not text.startswith(
                ("sprint:", "epic:", "story:")):
                table.add_row(f"[red]{entity.id}[/red]", entity.text)
                seen_tags.add(entity.text)
        if table.row_count:
            self.console.print(table)

    def print_user(self, entities):
        table = Table(box=self.box)
        for column in ("id", "name"):
            table.add_column(column)
        seen_users = set()
        for entity in entities:
            name = entity.name
            if name and name not in seen_users:
                table.add_row(f"[red]{entity.id}[/red]", name)
                seen_users.add(name)
        if table.row_count:
            self.console.print(table)

    def print_composite(self,
                        entities,
                        repo,
                        print_options,
                        composite_type,
                        kwargs=None):
        table = Table(box=self.box,
                      title=composite_type.upper(),
                      expand=print_options.expand_table)
        non_active_entities = Table(box=self.box,
                                    title=f"INACTIVE {composite_type.upper()}",
                                    expand=print_options.expand_table)
        default_columns = ("id", "name", "description", "status", "project",
                           "tasks")
        if print_options.columns:
            printable_columns = print_options.columns.split(",")
        else:
            printable_columns = default_columns
        for column in printable_columns:
            table.add_column(column, style="bold")
        for column in printable_columns:
            non_active_entities.add_column(column, style="bold")
        for i, entity in enumerate(entities):
            # TODO: Get project name
            # project = services.lookup_project_name(
            #     entity.project, repo)
            printable_row = {
                "id": f"{entity.id}",
                "name": str(entity.name),
                "description": entity.description,
                "status": entity.status.name,
                "project": f"{entity.project}",
                "tasks": str(len(entity.open_tasks))
            }
            printable_elements = [
                value for key, value in printable_row.items()
                if key in printable_columns
            ]
            if (entity.status.name == "ACTIVE"
                    or len(entity.completed_tasks) < len(entity.tasks)):
                table.add_row(*printable_elements)
            else:
                non_active_entities.add_row(*printable_elements)
        if table.row_count:
            self.console.print(table)
        if non_active_entities.row_count and print_options.show_completed:
            self.console.print(non_active_entities)
        if viz := print_options.show_viz:
            if "time" in viz:
                time_entries = entity.daily_time_entries_hours()
                self._print_time_utilization(time_entries)

    def _get_attributes(self, obj) -> list[tuple[str, str]]:
        import inspect
        attributes = []
        for name, value in inspect.getmembers(obj):
            if not name.startswith("_") and not inspect.ismethod(value):
                if not value:
                    continue
                elif name in ("created_by", "assignee"):
                    attributes.append(
                        # (name, services.lookup_user_name(value, self.repo)))
                        (name, str(value)))
                elif name == "project":
                    # project = services.lookup_project_name(value, self.repo)
                    attributes.append((name, str(value)))
                elif hasattr(value, "name"):
                    attributes.append((name, value.name))
                elif isinstance(value, datetime):
                    attributes.append((name, value.strftime("%Y-%m-%d %H:%M")))
                elif isinstance(value, set):
                    values = value.pop()
                    attributes.append((name, str(values)))
                else:
                    attributes.append((name, str(value)))
        return attributes

    def _print_time_utilization(self, time_entries) -> None:
        plt.date_form('Y-m-d')
        plt.plot_size(100, 15)
        plt.title(
            f"Time tracker - {format_hour_minute(sum(time_entries.values()))} spent"
        )
        plt.bar(time_entries.keys(), time_entries.values())
        plt.show()
