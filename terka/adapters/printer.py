from __future__ import annotations
from collections import abc
from dataclasses import dataclass
from datetime import datetime
import inspect
import rich
from rich.console import Console
from rich.table import Table
from textual.app import App, ComposeResult
from textual import widgets

from terka.service_layer import exceptions, formatter, ui, views


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
    sort: str = "id"
    columns: str = ""
    expand_table: bool = True

    @classmethod
    def from_kwargs(cls, **kwargs: dict) -> "PrintOptions":
        return cls(**{k: kwargs[k] for k in kwargs if k in cls.__match_args__})


class Printer:

    def __init__(self, uow):
        self.console = ConsolePrinter(uow)
        self.tui = TextualPrinter(uow)


class TextualPrinter:

    def __init__(self, uow) -> None:
        self.uow = uow

    def show_note(self, note):

        class NoteMarkdownViewer(App):

            BINDINGS = [("q", "quit", "Quit")]

            def compose(self) -> ComposeResult:
                yield widgets.MarkdownViewer(str(note),
                                             show_table_of_contents=True)

        app = NoteMarkdownViewer()
        app.run()

    def print_project(self, project, bus):
        app = ui.TerkaProject(project, bus)
        app.run()
        if app.return_code == 4:
            raise exceptions.TerkaRefreshException


    def print_sprint(self, sprint, bus):
        app = ui.TerkaSprint(sprint, bus)
        app.run()
        if app.return_code == 4:
            raise exceptions.TerkaRefreshException

class ConsolePrinter:

    def __init__(self, uow, box=rich.box.SIMPLE, config=None) -> None:
        self.uow = uow
        self.box = box
        self.config = config
        self.console = Console()

    def print_new_object(self, obj, mappings: dict | None = None):
        table = Table(box=self.box)
        if not mappings:
            mappings = {
                "project_mapping": views.projects_id_to_name_mapping(self.uow),
                "user_mapping": views.users_id_to_name_mapping(self.uow),
                "workspace_mapping": views.workspaces_id_to_name_mapping(self.uow)

            }
        attributes = self._get_attributes(obj, mappings)
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

    def print_composite(
            self,
            entities,
            print_options,
            composite_type,
            kwargs=None):
        if not entities:
            self.console.print(f"[red]No {composite_type} found[/red]")
            exit()
        project_mapping = views.projects_id_to_name_mapping(self.uow)
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
            project = project_mapping.get(entity.project)
            printable_row = {
                "id": f"{entity.id}",
                "name": str(entity.name),
                "description": entity.description,
                "status": entity.status.name,
                "project": project,
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

    def print_project(self, entities, print_options, kwargs=None):
        if not entities:
            self.console.print("[red]No projects found[/red]")
            exit()
        table = Table(box=rich.box.SQUARE_DOUBLE_HEAD,
                      expand=print_options.expand_table)
        non_active_projects = Table(box=rich.box.SQUARE_DOUBLE_HEAD,
                                    expand=print_options.expand_table)
        default_columns = ("id", "name", "description", "status", "open_tasks",
                           "overdue", "stale", "backlog", "todo",
                           "in_progress", "review", "done", "median_task_age",
                           "time_spent")

        if print_options.columns:
            printable_columns = print_options.columns.split(",")
        else:
            printable_columns = default_columns
        for column in printable_columns:
            table.add_column(column)
        for column in printable_columns:
            if column in ("id", "name", "description", "status", "open_tasks"):
                non_active_projects.add_column(column)
        try:
            reverse = True
            sorting_field = getattr(entities[0], print_options.sort)
            if isinstance(sorting_field, abc.MutableSequence):
                sort_fn = lambda x: len(getattr(x, print_options.sort))
            else:
                sort_fn = lambda x: getattr(x, print_options.sort)
        except AttributeError:
            sort_fn = lambda x: "id"
        if print_options.sort == "id":
            reverse = False
        entities.sort(key=sort_fn, reverse=reverse)
        for entity in entities:
            if len(open_tasks :=
                   entity.open_tasks) > 0 and entity.status.name == "ACTIVE":

                if overdue_tasks := entity.overdue_tasks:
                    entity_id = f"[red]{entity.id}[/red]"
                else:
                    entity_id = f"[green]{entity.id}[/green]"
                printable_row = {
                    "id":
                    f"{entity.id}",
                    "name":
                    str(entity.name),
                    "description":
                    entity.description,
                    "status":
                    entity.status.name,
                    "open_tasks":
                    str(len(open_tasks)),
                    "overdue":
                    str(len(overdue_tasks)),
                    "stale":
                    str(len(entity.stale_tasks)),
                    "backlog":
                    str(len(entity.backlog)),
                    "todo":
                    str(len(entity.todo)),
                    "in_progress":
                    str(len(entity.in_progress)),
                    "review":
                    str(len(entity.review)),
                    "done":
                    str(len(entity.done)),
                    "median_task_age":
                    str(entity.median_task_age),
                    "time_spent":
                    formatter.Formatter.format_time_spent(
                        entity.total_time_spent),
                }
                printable_elements = [
                    value for key, value in printable_row.items()
                    if key in printable_columns
                ]
                table.add_row(*printable_elements)
            else:
                printable_row = {
                    "id": f"{entity.id}",
                    "name": str(entity.name),
                    "description": entity.description,
                    "status": entity.status.name,
                    "open_tasks": str(len(open_tasks)),
                }
                printable_elements = [
                    value for key, value in printable_row.items()
                    if key in printable_columns
                ]
                non_active_projects.add_row(*printable_elements)

        if table.row_count:
            self.console.print(table)
        if non_active_projects.row_count and print_options.show_completed:
            self.console.print("[green]Inactive projects[/green]")
            self.console.print(non_active_projects)

    def print_task(self, entities, print_options):
        table = Table(box=rich.box.SQUARE_DOUBLE_HEAD,
                      expand=print_options.expand_table)
        columns = ("id", "name", "description", "status", "priority",
                   "project", "due_date", "tags", "collaborators",
                   "time_spent")
        completed_tasks_default_columns = ("id", "name", "description",
                                           "status", "priority", "project",
                                           "completed_date", "tags",
                                           "collaborators", "time_spent")
        if print_options.columns:
            printable_columns = print_options.columns.split(",")
        else:
            printable_columns = columns

        for column in printable_columns:
            table.add_column(column)

        for task in sorted(entities, key=lambda x: x.id, reverse=True):
            if tags := task.tags:
                tags_text = ",".join([tag.base_tag.text for tag in list(tags)])
            else:
                tags_text = ""
            if collaborators := task.collaborators:
                collaborators_texts = sorted([
                    collaborator.users.name
                    for collaborator in list(collaborators)
                    if collaborator.users
                ])
                collaborator_string = ",".join(collaborators_texts)
            else:
                collaborator_string = ""
            if task.is_overdue:
                task_id = f"[red]{task.id}[/red]"
            elif task.is_stale:
                task_id = f"[yellow]{task.id}[/yellow]"
            else:
                task_id = str(task.id)
            printable_row = {
                "id":
                task_id,
                "name":
                task.name,
                "description":
                task.description,
                "status":
                task.status.name,
                "priority":
                task.priority.name,
                "project":
                str(task.project),
                "due_date":
                str(task.due_date),
                "tags":
                tags_text,
                "collaborators":
                collaborator_string,
                "time_spent":
                formatter.Formatter.format_time_spent(task.total_time_spent),
            }
            printable_elements = [
                value for key, value in printable_row.items()
                if key in printable_columns
            ]
            table.add_row(*printable_elements)
        self.console.print(table)

    def print_sprint(self, entities, print_options, kwargs=None):
        if not entities:
            self.console.print("[red]No sprints found[/red]")
            exit()
        table = Table(box=rich.box.SQUARE_DOUBLE_HEAD,
                      expand=print_options.expand_table)
        all_sprints = Table(box=rich.box.SQUARE_DOUBLE_HEAD,
                            expand=print_options.expand_table)
        columns = ("id", "start_date", "end_date", "goal", "status",
                   "open tasks", "pct_completed", "velocity", "collaborators",
                   "time_spent", "utilization")
        if print_options.columns:
            printable_columns = print_options.columns.split(",")
        else:
            printable_columns = columns

        for column in printable_columns:
            table.add_column(column)
            all_sprints.add_column(column)
        for entity in entities:
            printable_row = {
                "id":
                str(entity.id),
                "start_date":
                str(entity.start_date),
                "end_date":
                str(entity.end_date),
                "goal":
                entity.goal,
                "status":
                entity.status.name,
                "open tasks":
                f"{len(entity.open_tasks)} ({len(entity.tasks)})",
                "pct_completed":
                f"{round(entity.pct_completed * 100, 2)}%",
                "velocity":
                str(round(entity.velocity, 2)),
                "collaborators":
                entity.collaborators_as_string,
                "time_spent":
                str(
                    formatter.Formatter.format_time_spent(
                        entity.total_time_spent)),
                "utilization":
                f"{round(entity.utilization * 100)}%"
            }
            printable_elements = [
                value for key, value in printable_row.items()
                if key in printable_columns
            ]
            if entity.status.name in ("ACTIVE", "PLANNED"):
                table.add_row(*printable_elements)
            all_sprints.add_row(*printable_elements)

        if print_options.show_completed:
            self.console.print(all_sprints)
        elif table.row_count:
            self.console.print(table)

    def _get_attributes(
            self, obj, mappings: dict[dict[int,
                                           str]]) -> list[tuple[str, str]]:
        attributes = []
        for name, value in inspect.getmembers(obj):
            if not name.startswith("_") and not inspect.ismethod(value):
                if not value:
                    continue
                elif name in ("created_by", "assignee"):
                    user = mappings.get("user_mapping").get(value)
                    attributes.append((name, user))
                elif name == "project":
                    project = mappings.get("project_mapping").get(value)
                    attributes.append((name, project))
                elif name == "workspace":
                    workspace = mappings.get("workspace_mapping",
                                             {}).get(value)
                    attributes.append((name, workspace))
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
