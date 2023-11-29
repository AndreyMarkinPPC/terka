from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
from rich.console import Console
from rich.text import Text
import subprocess
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, Vertical
from textual_plotext import PlotextPlot
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.validation import Number
from textual.widget import Widget
from textual.widgets import Button, Input, Header, Footer, Label, Tabs, DataTable, TabbedContent, TabPane, Static, Markdown, Pretty, Select

from terka.domain import _commands, events, models
from terka.service_layer import services, views, exceptions, ui_components
from terka.service_layer.formatter import Formatter


class PopupsMixin:

    def __init__(self):
        ...

    def action_task_complete(self) -> None:
        self.push_screen(ui_components.TaskComplete(),
                         self.task_complete_callback)

    def task_complete_callback(self, result: _commands.CompleteTask):
        result.id = self.selected_task
        self.bus.handle(result)
        self.notify(f"Task: {self.selected_task} is completed!")

    def action_task_edit(self) -> None:
        self.push_screen(ui_components.TaskEdit(), self.task_edit_callback)

    def task_edit_callback(self, result: tuple[_commands.UpdateTask,
                                               _commands.CommentTask]):
        update, comment = result
        update.id = self.selected_task
        comment.id = self.selected_task
        self.bus.handle(update)
        self.bus.handle(comment)
        self.notify(f"Task: {self.selected_task} is updated!")

    def action_task_add(self) -> None:
        self.push_screen(ui_components.TaskAdd(), self.task_add_callback)

    def task_add_callback(self, result: _commands.AddTask):
        if epic := result.epic:
            try:
                self.bus.handle(
                    _commands.AddTask(
                        id=self.selected_task,
                        epic=int(epic),
                    ))
                self.notify(
                    f"Task: {self.selected_task} is added to epic {epic}!")
            except exceptions.EntityNotFound:
                self.notify(f"Epic {epic} not found!", severity="error")
        if sprint := result.sprint:
            cmd = _commands.AddTask(
                id=self.selected_task,
                sprint=sprint,
            )
            if story_points := result.story_points:
                cmd.story_points = story_points
            try:
                self.bus.handle(cmd)
            except exceptions.EntityNotFound:
                self.notify(f"Sprint {sprint} not found!", severity="error")
            except exceptions.TerkaSprintCompleted:
                self.notify(f"Cannot add task to completed sprint {sprint} !",
                            severity="error")
            if not story_points:
                self.notify(
                    f"Task: {self.selected_task} is added to sprint {sprint}!")
            else:
                self.notify(
                    f"Task: {self.selected_task} story points updated "
                    f"to {story_points}!"
                )
        if story := result.story:
            try:
                self.bus.handle(
                    _commands.AddTask(
                        id=self.selected_task,
                        story=story,
                    ))
                self.notify(
                    f"Task: {self.selected_task} is added to story {story}!")
            except exceptions.EntityNotFound:
                self.notify(f"Story {story} not found!", severity="error")

    def action_task_delete(self) -> None:
        self.push_screen(ui_components.TaskDelete(), self.task_delete_callback)

    def task_delete_callback(self, result: _commands.DeleteTask):
        result.id = self.selected_task
        is_sprint = False
        if hasattr(self, "sprint_id"):
            result.sprint = self.sprint_id
            is_sprint = True

        self.bus.handle(result)
        if is_sprint:
            self.notify(
                f"Task: {self.selected_task} is deleted from "
                f"sprint {self.sprint_id}!",
                severity="warning")
        else:
            self.notify(f"Task: {self.selected_task} is deleted!",
                        severity="warning")

    def action_task_update_context(self) -> None:
        if self.selected_column == "status":
            self.push_screen(ui_components.TaskStatusEdit(),
                             self.task_update_status_callback)
        if self.selected_column == "priority":
            self.push_screen(ui_components.TaskPriorityEdit(),
                             self.task_update_priority_callback)
        if self.selected_column == "story_points":
            self.push_screen(ui_components.TaskStoryPointsEdit(),
                             self.task_update_story_points_callback)
        if self.selected_column == "time_spent":
            self.push_screen(ui_components.TaskHoursSubmitted(),
                             self.task_update_hours_callback)

    def task_update_status_callback(self, result: str):
        self.bus.handle(
            _commands.UpdateTask(id=self.selected_task,
                                 status=models.task.TaskStatus[result]))
        self.notify(f"Task: {self.selected_task} status updated to {result}!")

    def task_update_priority_callback(self, result: str):
        self.bus.handle(
            _commands.UpdateTask(id=self.selected_task,
                                 priority=models.task.TaskPriority[result]))
        self.notify(
            f"Task: {self.selected_task} priority updated to {result}!")

    def task_update_story_points_callback(self, result: str):
        self.bus.handle(
            _commands.AddTask(id=self.selected_task,
                              sprint=self.sprint_id,
                              story_points=result))
        self.notify(
            f"Task: {self.selected_task} story points updated to {result}!")

    def task_update_hours_callback(self, result: str):
        self.bus.handle(
            _commands.TrackTask(id=self.selected_task, hours=result))
        self.notify(f"Tracked {result} minutes for task {self.selected_task}!")


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
        # TODO: implement during next release
        # yield Input(placeholder="Add a comment", classes="body", id="comment")
        # yield Pretty("")

    @on(Input.Submitted)
    def submit_input(self, event: Input.Submitted) -> None:
        self.query_one(Pretty).update("Comment added")
        input = self.query_one(Input)
        input.value = ""


class TerkaProject(App, PopupsMixin):

    CSS_PATH = "entities.css"

    BINDINGS = [
        ("b", "backlog", "Backlog"),
        ("t", "tasks", "Tasks"),
        ("e", "epics", "Epics"),
        ("s", "stories", "Stories"),
        ("n", "notes", "Notes"),
        ("o", "overview", "Overview"),
        ("T", "time", "Time"),
        ("q", "quit", "Quit"),
        ("E", "task_edit", "Edit"),
        ("r", "refresh", "Refresh"),
        ("a", "task_add", "Add"),
        ("d", "task_complete", "Done"),
        ("U", "task_update_context", "Update"),
        ("X", "task_delete", "Delete"),
    ]

    def __init__(self, repo, config, project_id, bus) -> None:
        super().__init__()
        self.repo = repo
        self.config = config
        self.bus = bus
        self.tasks = list()
        self.selected_task = None
        self.project_id = project_id
        self.entity = self.get_entity()

    def get_entity(self):
        return self.repo.get(models.project.Project, self.project_id)

    def action_refresh(self):
        self.entity = self.get_entity()

    def on_mount(self) -> None:
        self.title = f"Project: {self.entity.name}"
        self.sub_title = f'Workspace: {self.config.get("workspace")}'

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"{self.entity.name}", classes="header")
        with TabbedContent(initial="tasks"):
            with TabPane("Backlog", id="backlog"):
                table = DataTable(id="backlog")
                for column in ("id", "name", "priority", "due_date",
                               "created_at", "tags", "collaborators",
                               "time_spent"):
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
                        table.add_row(task_id,
                                      task.name,
                                      task.priority.name,
                                      task.due_date,
                                      task.creation_date.strftime("%Y-%m-%d"),
                                      tags_text,
                                      collaborator_string,
                                      Formatter.format_time_spent(
                                          task.total_time_spent),
                                      key=task.id)
                yield table
            with TabPane("Open Tasks", id="tasks"):
                table = DataTable(id="tasks")
                for column in ("id", "name", "status", "priority", "due_date",
                               "tags", "collaborators", "time_spent"):
                    table.add_column(column, key=column)
                for task in sorted(self.entity.tasks,
                                   key=lambda x: x.status.name,
                                   reverse=True):
                    # self.tasks.append(task)
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
                        table.add_row(task_id,
                                      task.name,
                                      task.status.name,
                                      task.priority.name,
                                      task.due_date,
                                      tags_text,
                                      collaborator_string,
                                      Formatter.format_time_spent(
                                          task.total_time_spent),
                                      key=task.id)
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
            with TabPane("Time", id="time"):
                plotext = PlotextPlot(classes="plotext")
                plt = plotext.plt
                n_days = 14
                time = self.entity.daily_time_entries_hours(last_n_days=n_days)
                plt.date_form('Y-m-d')
                plt.title(
                    f"Time tracker - {round(sum(time.values()))} hours spent"
                    f" for the last {n_days} days")
                plt.bar(time.keys(), time.values())
                yield plotext
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
        self.query_one(TabbedContent).active = "epics"

    def action_backlog(self) -> None:
        self.query_one(TabbedContent).active = "backlog"

    def action_tasks(self) -> None:
        self.query_one(TabbedContent).active = "tasks"

    def action_stories(self) -> None:
        self.query_one(TabbedContent).active = "stories"

    def action_overview(self) -> None:
        self.query_one(TabbedContent).active = "overview"

    def action_notes(self) -> None:
        self.query_one(TabbedContent).active = "notes"

    def action_time(self) -> None:
        self.query_one(TabbedContent).active = "time"

    def action_done(self):
        self.selected_task = 0

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted):
        self.selected_task = event.cell_key.row_key.value

    def on_data_table_cell_selected(self, event: DataTable.CellSelected):
        self.selected_task = event.cell_key.row_key.value
        self.selected_column = event.cell_key.column_key.value


class TerkaSprint(App, PopupsMixin):

    CSS_PATH = "entities.css"

    BINDINGS = [("t", "tasks", "Tasks"), ("n", "notes", "Notes"),
                ("o", "overview", "Overview"), ("q", "quit", "Quit"),
                ("P", "sort_by_project", "Sort by Project"),
                ("S", "sort_by_status", "Sort by Status"),
                ("E", "task_edit", "Edit"), ("r", "refresh", "Refresh"),
                ("d", "task_complete", "Done"), ("X", "task_delete", "Delete"),
                ("a", "task_add", "Add"),
                ("U", "task_update_context", "Update"), ("T", "time", "Time")]

    current_sorts: set = set()

    def __init__(self, repo, config, sprint_id, bus) -> None:
        super().__init__()
        self.repo = repo
        self.config = config
        self.bus = bus
        self.selected_task = None
        self.sprint_id = sprint_id
        self.entity = self.get_entity()
        self.tasks = self.get_tasks()

    def get_entity(self):
        return self.repo.get_by_id(models.sprint.Sprint, self.sprint_id)

    def get_tasks(self):
        for sprint_task in self.entity.tasks:
            if sprint_task.tasks.status.name not in ("DONE", "DELETED"):
                yield sprint_task.tasks

    def action_refresh(self):
        self.entity = self.get_entity()
        previous_tasks = list(self.tasks)
        self.tasks = list(self.get_tasks())
        new_tasks = list(self.tasks)
        exit(f"{len(new_tasks)}, {len(previous_tasks)}")
        self.notify("Refreshing data...")

    def sort_reverse(self, sort_type: str):
        """Determine if `sort_type` is ascending or descending."""
        reverse = sort_type in self.current_sorts
        if reverse:
            self.current_sorts.remove(sort_type)
        else:
            self.current_sorts.add(sort_type)
        return reverse

    def action_sort_by_project(self) -> None:
        table = self.query_one("#tasks_table", DataTable)
        table.sort(
            "project",
            reverse=self.sort_reverse("project"),
        )

    def action_sort_by_status(self) -> None:
        table = self.query_one("#tasks_table", DataTable)
        table.sort(
            "status",
            reverse=self.sort_reverse("status"),
        )

    def on_mount(self) -> None:
        self.title = "Sprint"
        self.sub_title = f'Workspace: {self.config.get("workspace")}'

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(
            f"[bold]Sprint {self.entity.id}[/bold]: \n{self.entity.goal}",
            classes="header")
        with TabbedContent(initial="tasks"):
            with TabPane("Tasks", id="tasks"):
                table = DataTable(id="tasks_table")
                for column in ("id", "name", "status", "priority",
                               "story_points", "project", "due_date", "tags",
                               "collaborators", "time_spent"):
                    table.add_column(column, key=column)
                for sprint_task in sorted(self.entity.tasks,
                                          key=lambda x: x.tasks.status.value,
                                          reverse=True):
                    task = sprint_task.tasks
                    # self.tasks.append(task)
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
                    project = services.lookup_project_name(
                        task.project, self.repo)
                    if task.status.name not in ("DONE", "DELETED"):
                        table.add_row(task_id,
                                      task.name,
                                      task.status.name,
                                      task.priority.name,
                                      str(sprint_task.story_points),
                                      project,
                                      task.due_date,
                                      tags_text,
                                      collaborator_string,
                                      Formatter.format_time_spent(
                                          task.total_time_spent),
                                      key=task.id)
                yield table
            with TabPane("Completed Tasks", id="completed_tasks"):
                table = DataTable(id="completed_tasks")
                for column in ("id", "name", "project", "completion_date",
                               "tags", "collaborators", "story_points",
                               "time_spent"):
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
                    project = services.lookup_project_name(
                        task.project, self.repo)
                    if task.status.name in ("DONE", "DELETED"):
                        table.add_row(
                            str(task.id),
                            task.name,
                            project,
                            task.completion_date.strftime("%Y-%m-%d")
                            if task.completion_date else "",
                            tags_text,
                            collaborator_string,
                            Formatter.format_time_spent(
                                round(sprint_task.story_points * 60)),
                            Formatter.format_time_spent(task.total_time_spent),
                            key=task.id)
                yield table
            with TabPane("Notes", id="notes"):
                table = DataTable(id="notes")
                table.add_columns("id", "text")
                for task in self.entity.notes:
                    table.add_row(str(task.id), task.name)
                yield table
            with TabPane("Time", id="time"):
                plotext = PlotextPlot(classes="plotext")
                plt = plotext.plt
                if not (sprint_time := self.entity.daily_time_entries_hours()):
                    yield Static("No time tracked")
                else:
                    workspace = services.get_workplace_by_name(
                        self.config.get("workspace"), self.repo)
                    all_workspace_time = workspace.daily_time_entries_hours(
                        start_date=self.entity.start_date,
                        end_date=self.entity.end_date)
                    non_sprint_times = [
                        all_times - sprint_times
                        for all_times, sprint_times in zip(
                            all_workspace_time.values(), sprint_time.values())
                    ]

                    plt.date_form('Y-m-d')
                    plt.title(
                        f"Time tracker - {Formatter.format_time_spent(self.entity.total_time_spent)} spent"
                    )
                    plt.stacked_bar(sprint_time.keys(),
                                    [sprint_time.values(), non_sprint_times],
                                    label=["sprint", "non-sprint"])
                    yield plotext
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
        self.query_one(TabbedContent).active = "tasks"

    def action_time(self) -> None:
        self.query_one(TabbedContent).active = "time"

    def action_overview(self) -> None:
        self.query_one(TabbedContent).active = "overview"

    def action_notes(self) -> None:
        self.query_one(TabbedContent).active = "notes"

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted):
        self.selected_task = event.cell_key.row_key.value

    def on_data_table_cell_selected(self, event: DataTable.CellSelected):
        self.selected_task = event.cell_key.row_key.value
        self.selected_column = event.cell_key.column_key.value

    def on_data_table_cell_selected(self, event: DataTable.CellHighlighted):
        self.selected_task = event.cell_key.row_key.value
        self.selected_column = event.cell_key.column_key.value


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


def get_times(dates: list[str],
              time_entries: list[dict[str, str | int]]) -> list[float]:
    times: list[float] = []
    for date in dates:
        value_for_date = 0
        for entry in time_entries:
            if entry.get("date") == date:
                value_for_date = entry.get("time_spent_hours") / 60
                break
        times.append(value_for_date)
    return times
