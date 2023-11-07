from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from rich.console import Console
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Input, Header, Footer, Label, Tabs, DataTable, TabbedContent, TabPane, Static, Markdown

from terka.service_layer.formatter import Formatter


class Comment(Widget):
    value = reactive("text")

    def render(self) -> str:
        return f"Comment: {self.value}"


class TerkaTask(App):
    BINDINGS = [("q", "quit", "Quit")]
    CSS_PATH = "vertical_layout.css"

    def __init__(self,
                 entity,
                 project,
                 is_completed: bool = False,
                 history=None,
                 commentaries=None):
        super().__init__()
        self.entity = entity
        self.project = project
        self.is_completed = True if entity.status.name in (
            "DONE", "DELETED") else False
        self.history = history
        self.commentaries = commentaries
        self.is_overdue = datetime.today().date(
        ) > entity.due_date if entity.due_date and entity.status.name not in (
            "DONE", "DELETED") else False

    def compose(self) -> ComposeResult:
        yield Header()
        task_text = f"[bold]Task {self.entity.id}: {self.entity.name}[/bold]"
        if self.is_completed:
            yield Static(task_text, classes="header_completed", id="header")
        elif self.is_overdue:
            yield Static(task_text, classes="header_overdue", id="header")
        else:
            yield Static(task_text, classes="header_simple", id="header")
        yield Static(f"Project: [bold]{self.project}[/bold]", classes="transp")
        yield Static(f"Status: [bold]{self.entity.status.name}[/bold]",
                     classes="transp")
        yield Static(f"Priority: [bold]{self.entity.priority.name}[/bold]",
                     classes="transp")
        created_days_ago = (datetime.now() - self.entity.creation_date).days
        creation_message = f"{created_days_ago} days ago" if created_days_ago > 1 else "today"
        yield Static(f"Created {creation_message}", classes="transp")
        if self.is_completed:
            completion_date = self.entity.completion_date
            if completion_date:
                completed_days_ago = (datetime.now() - completion_date).days
                completion_message = f"{completed_days_ago} days ago" if completed_days_ago > 1 else "today"
                yield Static(
                    f"Completed {completion_message} ({completion_date.strftime('%Y-%m-%d')})",
                    classes="transp")
            else:
                yield Static("Completion date unknown", classes="transp")
        else:
            yield Static(f"Due date: {self.entity.due_date}", classes="transp")
        if sprints := self.entity.sprints:
            sprint_id = ",".join(str(s.sprint) for s in sprints)
            story_points = sprints[-1].story_points
            yield Static(
                f"Sprints: [bold]{sprint_id}[/bold], "
                f"SP: [bold]{story_points}[/bold], "
                f"T: [bold]{Formatter.format_time_spent(self.entity.total_time_spent)}[/bold]",
                classes="transp")
        else:
            yield Static(f"Not in sprint", classes="transp")
        if epics := self.entity.epics:
            epic_ids = ",".join([str(e.epic) for e in epics])
            yield Static(f"Epics: [bold]{epic_ids}[/bold]", classes="transp")
        else:
            yield Static(f"Not in epic", classes="transp")
        if stories := self.entity.stories:
            story_ids = ",".join([str(s.story) for s in stories])
            yield Static(f"Story: [bold]{story_ids}[/bold]", classes="transp")
        else:
            yield Static(f"Not in story", classes="transp")
        if tags := self.entity.tags:
            tags = ",".join(
                t.base_tag.text for t in tags
                if not t.base_tag.text.startswith(("epic", "story", "sprint")))
            yield Static(f"Tags: [bold]{tags}[/bold]", classes="transp")
        else:
            yield Static(f"No tags", classes="transp")
        if collaborators := self.entity.collaborators:
            collaborators = ",".join(c.users.name for c in collaborators)
            yield Static(f"Collaborators: [bold]{collaborators}[/bold]",
                         classes="transp")
        else:
            yield Static(f"No collaborators", classes="transp")
        description_message = self.entity.description or ""
        if description_message:
            yield Static(
                f"[italic]Description...\n[/italic]{description_message}",
                classes="body",
                id="desc")
        else:
            yield Static("[italic]No description...[/italic]",
                         classes="body",
                         id="desc")
        if self.commentaries:
            comms = [
                f"[italic]{comment.date.date()}[/italic]: {comment.text}"
                for comment in self.commentaries
            ]
            comms_message = "\n".join(comms)
            yield Static(f"[italic]Comments...\n\n[/italic]{comms_message}",
                         classes="body",
                         id="history")
        else:
            yield Static("", classes="body", id="history")
        # yield Input(placeholder="Add a comment", classes="body", id="comment")
        # yield Comment()

    # def on_input_changed(self, event: Input.Changed) -> None:
    #     self.query_one(Comment).text = event.value


class TerkaProject(App):

    CSS = """
    Tabs {
        dock: top;
    }
    Screen {
        align: center top;
    }
    .header {
        margin:1 1;
        width: 100%;
        height: 5%;
        background: $panel;
        border: tall $primary;
        content-align: center middle;
    }
    """

    BINDINGS = [("b", "backlog", "Backlog"), ("t", "tasks", "Tasks"),
                ("e", "epics", "Epics"), ("s", "stories", "Stories"),
                ("n", "notes", "Notes"), ("o", "overview", "Overview"),
                ("q", "quit", "Quit")]

    def __init__(self, entity) -> None:
        super().__init__()
        self.entity = entity

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"{self.entity.name}", classes="header")
        with TabbedContent(initial="tasks"):
            with TabPane("Backlog", id="backlog"):
                table = DataTable(id="backlog")
                for column in ("id", "name", "priority", "due_date", "created_at", "tags",
                               "collaborators", "time_spent"):
                    table.add_column(column, key=column)
                for task in sorted(self.entity.tasks,
                                   key=lambda x: x.id,
                                   reverse=True):
                    if task.status.name == "BACKLOG":
                        if tags := task.tags:
                            tags_text = ",".join(
                                [tag.base_tag.text for tag in list(tags)])
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
                        table.add_row(
                            task_id, task.name, task.priority.name,
                            task.due_date, task.creation_date.strftime("%Y-%m-%d"),
                            tags_text, collaborator_string,
                            Formatter.format_time_spent(task.total_time_spent))
                yield table
            with TabPane("Open Tasks", id="tasks"):
                table = DataTable(id="tasks")
                for column in ("id", "name", "status", "priority", "due_date",
                               "tags", "collaborators", "time_spent"):
                    table.add_column(column, key=column)
                for task in sorted(self.entity.tasks,
                                   key=lambda x: x.status.name,
                                   reverse=True):
                    if task.status.name in ("TODO", "IN_PROGRESS", "REVIEW"):
                        if tags := task.tags:
                            tags_text = ",".join(
                                [tag.base_tag.text for tag in list(tags)])
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
                        table.add_row(
                            task_id, task.name, task.status.name,
                            task.priority.name, task.due_date, tags_text,
                            collaborator_string,
                            Formatter.format_time_spent(task.total_time_spent))
                yield table
            with TabPane("Completed Tasks", id="completed_tasks"):
                table = DataTable(id="completed_tasks")
                for column in ("id", "name", "status", "priority",
                               "completion_date", "tags", "collaborators",
                               "time_spent"):
                    table.add_column(column, key=column)
                completed_tasks = [
                    e for e in self.entity.tasks if e.completion_date
                ]
                for task in sorted(completed_tasks,
                                   key=lambda x: x.completion_date,
                                   reverse=True):
                    if tags := task.tags:
                        tags_text = ",".join(
                            [tag.base_tag.text for tag in list(tags)])
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
                    table.add_row(
                        str(task.id), task.name, task.status.name,
                        task.priority.name,
                        task.completion_date.strftime("%Y-%m-%d"), tags_text,
                        collaborator_string,
                        Formatter.format_time_spent(task.total_time_spent))
                yield table
            with TabPane("Epics", id="epics"):
                table = DataTable(id="epics")
                table.add_columns("id", "name", "description", "status",
                                  "tasks")
                for epic in sorted(self.entity.epics,
                                   key=lambda x: len(x.tasks),
                                   reverse=True):
                    table.add_row(str(epic.id), shorten_text(epic.name),
                                  shorten_text(epic.description),
                                  epic.status.name, str(len(epic.tasks)))
                yield table
            with TabPane("Stories", id="stories"):
                table = DataTable(id="stories")
                table.add_columns("id", "name", "description", "status",
                                  "tasks")
                for story in self.entity.stories:
                    table.add_row(str(story.id), shorten_text(story.name),
                                  shorten_text(story.description),
                                  story.status.name, str(len(story.tasks)))
                yield table
            with TabPane("Notes", id="notes"):
                table = DataTable(id="notes")
                table.add_columns("id", "text")
                for task in self.entity.notes:
                    table.add_row(str(task.id), task.name)
                yield table
            with TabPane("Overview", id="overview"):
                collaborators = self.entity.task_collaborators
                sorted_collaborators = ""
                for name, value in sorted(collaborators.items(),
                                          key=lambda x: x[1],
                                          reverse=True):
                    sorted_collaborators += f"  * {name}: {Formatter.format_time_spent(value)} \n"
                yield Markdown(f"""
# Project details:
* Repo: {self.entity.description}
* Time spend: {Formatter.format_time_spent(self.entity.total_time_spent)}
* Collaborators:
{sorted_collaborators}
                """)

        yield Footer()

    def action_epics(self) -> None:
        """Add a new tab."""
        self.query_one(TabbedContent).active = "epics"

    def action_backlog(self) -> None:
        """Add a new tab."""
        self.query_one(TabbedContent).active = "backlog"

    def action_tasks(self) -> None:
        """Add a new tab."""
        self.query_one(TabbedContent).active = "tasks"

    def action_stories(self) -> None:
        """Add a new tab."""
        self.query_one(TabbedContent).active = "stories"

    def action_overview(self) -> None:
        """Add a new tab."""
        self.query_one(TabbedContent).active = "overview"

    def action_notes(self) -> None:
        """Add a new tab."""
        self.query_one(TabbedContent).active = "notes"


class TerkaSprint(App):

    CSS = """
    Tabs {
        dock: top;
    }
    Screen {
        align: center top;
    }
    .header {
        margin:1 1;
        width: 100%;
        height: 5%;
        background: $panel;
        border: tall $primary;
        content-align: center middle;
    }
    """

    BINDINGS = [("t", "tasks", "Tasks"), ("n", "notes", "Notes"),
                ("o", "overview", "Overview"), ("q", "quit", "Quit")]

    def __init__(self, entity) -> None:
        super().__init__()
        self.entity = entity

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(
            f"[bold]Sprint {self.entity.id}[/bold]: \n{self.entity.goal}",
            classes="header")
        with TabbedContent(initial="tasks"):
            with TabPane("Tasks", id="tasks"):
                table = DataTable(id="tasks")
                for column in ("id", "name", "status", "priority", "due_date",
                               "tags", "collaborators", "time_spent"):
                    table.add_column(column, key=column)
                for sprint_task in sorted(self.entity.tasks,
                                          key=lambda x: x.id,
                                          reverse=True):
                    task = sprint_task.tasks
                    if tags := task.tags:
                        tags_text = ",".join([
                            tag.base_tag.text for tag in list(tags)
                            if not tag.base_tag.text.startswith("sprint")
                        ])
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
                    if task.status.name not in ("DONE", "DELETED"):
                        table.add_row(
                            task_id, task.name, task.status.name,
                            task.priority.name, task.due_date, tags_text,
                            collaborator_string,
                            Formatter.format_time_spent(task.total_time_spent))
                yield table
            with TabPane("Completed Tasks", id="completed_tasks"):
                table = DataTable(id="completed_tasks")
                for column in ("id", "name", "completion_date", "tags",
                               "collaborators", "time_spent"):
                    table.add_column(column, key=column)
                for sprint_task in sorted(self.entity.tasks,
                                          key=lambda x: x.id,
                                          reverse=True):
                    task = sprint_task.tasks
                    if tags := task.tags:
                        tags_text = ",".join([
                            tag.base_tag.text for tag in list(tags)
                            if not tag.base_tag.text.startswith("sprint")
                        ])
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
                    if task.status.name in ("DONE", "DELETED"):
                        table.add_row(
                            str(task.id), task.name,
                            task.completion_date.strftime("%Y-%m-%d"),
                            tags_text, collaborator_string,
                            Formatter.format_time_spent(task.total_time_spent))
                yield table
            with TabPane("Notes", id="notes"):
                table = DataTable(id="notes")
                table.add_columns("id", "text")
                for task in self.entity.notes:
                    table.add_row(str(task.id), task.name)
                yield table
            with TabPane("Overview", id="overview"):
                collaborators = self.entity.collaborators
                sorted_collaborators = ""
                for name, value in sorted(collaborators.items(),
                                          key=lambda x: x[1],
                                          reverse=True):
                    sorted_collaborators += f"  * {name}: {Formatter.format_time_spent(value)} \n"
                yield Markdown(f"""
# Sprint details:
* Period: {self.entity.start_date} - {self.entity.end_date}
* Open tasks: {len(self.entity.open_tasks)} ({len(self.entity.tasks)}) 
* Pct Completed: {round(self.entity.pct_completed, 2) :.0%}
* Velocity: {self.entity.velocity}
* Time spend: {Formatter.format_time_spent(self.entity.total_time_spent)}
* Utilization: {round(self.entity.utilization, 2) :.0%}
* Collaborators:
{sorted_collaborators}
                """)

        yield Footer()

    def action_tasks(self) -> None:
        """Add a new tab."""
        self.query_one(TabbedContent).active = "tasks"

    def action_overview(self) -> None:
        """Add a new tab."""
        self.query_one(TabbedContent).active = "overview"

    def action_notes(self) -> None:
        """Add a new tab."""
        self.query_one(TabbedContent).active = "notes"


# TODO: implement
# class TerkaProjectScreen(TerkaProject):
#     ...

# class TerkaSprintScreen(TerkaSprint):
#     ...

# class Terka(App):
#     BINDINGS = [
#         ("1", "switch_mode('sprint')", "Sprint"),
#         ("2", "switch_mode('projects')", "Projects"),
#     ]
#     MODES = {"project": TerkaProjectScreen, "sprint": TerkaSprintScreen}

#     def on_mount(self) -> None:
#         self.switch_mode("project")


def shorten_text(text: str | None, limit: int = 80) -> str | None:
    if text and len(text) > limit:
        text = text[:limit]
    return text
