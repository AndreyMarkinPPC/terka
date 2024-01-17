from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical
from textual_plotext import PlotextPlot
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.validation import Number
from textual.widget import Widget
from textual.widgets import (Button, Input, Header, Footer, Label, Tabs,
                             DataTable, TabbedContent, TabPane, Static,
                             Markdown, MarkdownViewer, Pretty, Rule, Select)

from terka.domain import commands, events, entities
from terka.service_layer import services, exceptions, ui_components, views
from terka.service_layer.formatter import Formatter


class SortingMixin:
    current_sorts = set()

    def sort_reverse(self, sort_type: str):
        """Determine if `sort_type` is ascending or descending."""
        reverse = sort_type in self.current_sorts
        if reverse:
            self.current_sorts.remove(sort_type)
        else:
            self.current_sorts.add(sort_type)
        return reverse

    def action_sort(self) -> None:
        table = self.query_one(f"#{self.selected_data_table}", DataTable)
        table.sort(
            self.selected_column,
            reverse=self.sort_reverse(self.selected_column),
        )


class SelectionMixin:

    def on_data_table_cell_selected(self, event: DataTable.CellSelected):
        selected_id = event.cell_key.row_key.value
        self.selected_task = selected_id
        self.selected_column = event.cell_key.column_key.value
        self.selected_data_table = event.data_table.id
        with self.bus.uow as uow:
            if "task" in self.selected_data_table:
                task_obj = uow.tasks.get_by_id(entities.task.Task, selected_id)
                self.query_one(ui_components.Title).text = task_obj.name
                self.query_one(
                    ui_components.Description).text = task_obj.description
                self.query_one(
                    ui_components.Status).value = task_obj.status.name
                self.query_one(
                    ui_components.Priority).value = task_obj.priority.name
                self.query_one(ui_components.Project).value = task_obj.project
                self.query_one(ui_components.Commentaries).values = [
                    (t.date.strftime("%Y-%m-%d %H:%M"), t.text)
                    for t in task_obj.commentaries
                ]
            if "epic" in self.selected_data_table:
                epic_obj = uow.tasks.get_by_id(entities.epic.Epic, selected_id)
                self.query_one(ui_components.Title).text = epic_obj.name
                self.query_one(
                    ui_components.Description).text = epic_obj.description
            if "story" in self.selected_data_table:
                story_obj = uow.tasks.get_by_id(entities.story.Story,
                                                selected_id)
                self.query_one(ui_components.Title).text = story_obj.name
                self.query_one(
                    ui_components.Description).text = story_obj.description


class PopupsMixin:

    def __init__(self):
        ...

    def _process_commands_chain(self,
                                result: tuple[commands.Command, ...],
                                project: str | None = None) -> int | None:
        main_command, *rest = result
        main_command.id = self.selected_task
        if project:
            main_command.project = project
        object_id = self.bus.handle(main_command)
        for cmd in rest:
            cmd.id = object_id or self.selected_task
            if cmd:
                self.bus.handle(cmd)
                self.notify(f"command {cmd}!")
        return object_id

    def action_task_complete(self) -> None:
        self.push_screen(ui_components.TaskComplete(),
                         self.task_complete_callback)

    def task_complete_callback(self, result: tuple[commands.CompleteTask,
                                                   commands.CommentTask,
                                                   commands.TrackTask]):
        self._process_commands_chain(result)
        self.notify(f"Task: {self.selected_task} is completed!")

    def action_task_comment(self) -> None:
        self.push_screen(ui_components.TaskComment(),
                         self.task_comment_callback)

    def task_comment_callback(self, result: commands.CommentTask):
        result.id = self.selected_task
        self.bus.handle(result)
        self.notify(f"Task: {self.selected_task} is commented!")

    def action_task_edit(self) -> None:
        self.push_screen(ui_components.TaskEdit(), self.task_edit_callback)

    def task_edit_callback(self, result: tuple[commands.UpdateTask,
                                               commands.CommentTask]):
        self._process_commands_chain(result)
        self.notify(f"Task: {self.selected_task} is updated!")

    def action_task_add(self) -> None:
        self.push_screen(ui_components.TaskAdd(), self.task_add_callback)

    def task_add_callback(self, result: commands.AddTask):
        if epic := result.epic:
            try:
                self.bus.handle(
                    commands.AddTask(
                        id=self.selected_task,
                        epic=int(epic),
                    ))
                self.notify(
                    f"Task: {self.selected_task} is added to epic {epic}!")
            except exceptions.EntityNotFound:
                self.notify(f"Epic {epic} not found!", severity="error")
        if sprint := result.sprint:
            cmd = commands.AddTask(
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
                self.notify(f"Task: {self.selected_task} story points updated "
                            f"to {story_points}!")
        if story := result.story:
            try:
                self.bus.handle(
                    commands.AddTask(
                        id=self.selected_task,
                        story=story,
                    ))
                self.notify(
                    f"Task: {self.selected_task} is added to story {story}!")
            except exceptions.EntityNotFound:
                self.notify(f"Story {story} not found!", severity="error")

    def action_task_delete(self) -> None:
        if self.selected_column == "due_date":
            self.push_screen(ui_components.TaskDeleteDueDate(),
                             self.task_delete_due_date_callback)
        else:
            self.push_screen(ui_components.TaskDelete(),
                             self.task_delete_callback)

    def task_delete_callback(self, result: tuple[commands.CompleteTask,
                                                 commands.CommentTask,
                                                 commands.TrackTask]):
        delete, *rest = result
        delete.id = self.selected_task
        is_sprint = False
        if hasattr(self, "sprint_id"):
            delete.sprint = self.sprint_id
            is_sprint = True

        self.bus.handle(delete)
        for cmd in rest:
            cmd.id = self.selected_task
            if cmd:
                self.bus.handle(cmd)
                self.notify(f"command {cmd}!")
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
        if self.selected_column == "tags":
            self.push_screen(ui_components.TaskTagEdit(),
                             self.task_update_tag_callback)
        if self.selected_column == "collaborators":
            self.push_screen(ui_components.TaskCollaboratorEdit(),
                             self.task_update_collaborator_callback)

    def task_update_status_callback(self, result: str):
        if result:
            self.bus.handle(
                commands.UpdateTask(id=self.selected_task, status=result))
            self.notify(
                f"Task: {self.selected_task} status updated to {result}!")

    def task_update_priority_callback(self, result: str):
        if result:
            self.bus.handle(
                commands.UpdateTask(id=self.selected_task, priority=result))
            self.notify(
                f"Task: {self.selected_task} priority updated to {result}!")

    def task_update_story_points_callback(self, result: str):
        if result:
            self.bus.handle(
                commands.AddTask(id=self.selected_task,
                                 sprint=self.sprint_id,
                                 story_points=result))
            self.notify(
                f"Task: {self.selected_task} story points updated to {result}!"
            )

    def task_update_hours_callback(self, result: str):
        if result:
            self.bus.handle(
                commands.TrackTask(id=self.selected_task, hours=result))
            self.notify(
                f"Tracked {result} minutes for task {self.selected_task}!")

    def task_update_tag_callback(self, result: str):
        if result:
            self.bus.handle(commands.TagTask(id=self.selected_task,
                                             tag=result))
            self.notify(
                f"Tagged task {self.selected_task} with tag(s): {result}!")

    def task_update_collaborator_callback(self, result: str):
        if result:
            self.bus.handle(
                commands.CollaborateTask(id=self.selected_task,
                                         collaborator=result))
            self.notify(
                f"Added collaborator {result} for task {self.selected_task}!")

    def task_delete_due_date_callback(self, result: bool):
        if result:
            self.bus.handle(
                commands.UpdateTask(id=self.selected_task, due_date="Remove"))
            self.notify(f"Removed due date for task {self.selected_task}")

    def action_show_info(self) -> None:
        if "task" in self.selected_data_table:
            sidebar = self.query_one(ui_components.Sidebar)
            # elif "epic" in self.selected_data_table:
            #     sidebar = self.query_one(ui_components.EpicSidebar)
            # elif "story" in self.selected_data_table:
            #     sidebar = self.query_one(ui_components.Sidebar)
            self.set_focus(None)
            if sidebar.has_class("-hidden"):
                sidebar.remove_class("-hidden")
            else:
                if sidebar.query("*:focus"):
                    self.screen.set_focus(None)
                sidebar.add_class("-hidden")


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


class TerkaProject(App, PopupsMixin, SelectionMixin, SortingMixin):

    CSS_PATH = "entities.css"

    BINDINGS = [
        ("n", "new_task", "New Task"),
        ("b", "backlog", "Backlog"),
        ("t", "tasks", "Tasks"),
        ("s", "sort", "Sort"),
        ("S", "sync", "Sync"),
        ("o", "overview", "Overview"),
        ("T", "time", "Time"),
        ("q", "quit", "Quit"),
        ("E", "task_edit", "Edit"),
        ("r", "refresh", "Refresh"),
        ("i", "show_info", "Info"),
        ("a", "task_add", "Add"),
        ("d", "task_complete", "Done"),
        ("C", "task_comment", "Comment"),
        ("U", "task_update_context", "Update"),
        ("X", "task_delete", "Delete"),
        ("Enter", "task_show", "Show"),
    ]

    show_sidebar = reactive(False)

    def __init__(self, entity, bus) -> None:
        super().__init__()
        self.entity = entity
        self.bus = bus
        self.tasks = list()
        self.selected_task = None
        self.selected_column = None
        self.project_id = entity.id
        if _last_synced := self.entity.last_synced:
            self.last_synced = _last_synced[0].sync_date.strftime(
                "%Y-%m-%d %H:%M:%S")
        else:
            self.last_synced = None

    def action_refresh(self):
        self.exit(return_code=4)

    @work(thread=True)
    def action_sync(self) -> None:
        self.notify("syncing project...")
        self.bus.handle(commands.SyncProject(self.project_id))
        self.notify("project synced")

    def on_mount(self) -> None:
        self.title = f"Project: {self.entity.name}"
        self.sub_title = f'Workspace: {self.bus.config.get("workspace")}, last synced: {self.last_synced}'

    def compose(self) -> ComposeResult:
        yield ui_components.Sidebar(classes="-hidden")
        yield Header()
        yield Static(f"{self.entity.name}", classes="header")
        with TabbedContent(initial="tasks"):
            with TabPane("Backlog", id="backlog"):
                yield Button("+Task",
                             id="new_task",
                             variant="success",
                             classes="new_entity")
                table = DataTable(id="project_tasks_backlog_table")
                for column in ("id", "name", "priority", "due_date",
                               "created_at", "assignee", "tags",
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
                        if len(commentaries := task.commentaries) > 0:
                            task_name = f"{task.name} [blue][{len(task.commentaries)}][/blue]"
                        else:
                            task_name = task.name
                        table.add_row(task_id,
                                      task_name,
                                      task.priority.name,
                                      task.due_date,
                                      task.creation_date.strftime("%Y-%m-%d"),
                                      str(task.assigned_to.name)
                                      if task.assigned_to else "",
                                      tags_text,
                                      collaborator_string,
                                      Formatter.format_time_spent(
                                          task.total_time_spent),
                                      key=task.id)
                yield table
            with TabPane("Open Tasks", id="tasks"):
                table = DataTable(id="project_open_tasks")
                for column in ("id", "name", "status", "priority", "due_date",
                               "assignee", "tags", "collaborators",
                               "time_spent"):
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
                        if len(commentaries := task.commentaries) > 0:
                            task_name = f"{task.name} [blue][{len(task.commentaries)}][/blue]"
                        else:
                            task_name = task.name
                        table.add_row(task_id,
                                      task_name,
                                      task.status.name,
                                      task.priority.name,
                                      task.due_date,
                                      str(task.assigned_to.name)
                                      if task.assigned_to else "",
                                      tags_text,
                                      collaborator_string,
                                      Formatter.format_time_spent(
                                          task.total_time_spent),
                                      key=task.id)
                yield table
            with TabPane("Completed Tasks", id="completed_tasks"):
                table = DataTable(id="project_completed_tasks_table")
                for column in ("id", "name", "status", "priority",
                               "completion_date", "assignee", "tags",
                               "collaborators", "time_spent"):
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
                    if len(commentaries := task.commentaries) > 0:
                        task_name = f"{task.name} [blue][{len(task.commentaries)}][/blue]"
                    else:
                        task_name = task.name
                    table.add_row(
                        str(task.id),
                        task_name,
                        task.status.name,
                        task.priority.name,
                        task.completion_date.strftime("%Y-%m-%d"),
                        str(task.assigned_to.name) if task.assigned_to else "",
                        tags_text,
                        collaborator_string,
                        Formatter.format_time_spent(task.total_time_spent),
                        key=task.id)
                yield table
            with TabPane("Epics", id="epics"):
                yield Button("+Epic",
                             id="new_epic",
                             variant="success",
                             classes="new_entity")
                table = DataTable(id="project_epics_table")
                inactive_table = DataTable(id="project_inactive_epics_table")
                for column in ("id", "name", "description", "status",
                               "open_tasks", "completed_tasks"):
                    table.add_column(column, key=f"epic_{column}")
                    inactive_table.add_column(column,
                                              key=f"inactive_epic_{column}")
                for epic in sorted(self.entity.epics,
                                   key=lambda x: len(x.tasks),
                                   reverse=True):
                    if epic.open_tasks:
                        table.add_row(str(epic.id),
                                      shorten_text(epic.name),
                                      shorten_text(epic.description),
                                      epic.status.name,
                                      str(len(epic.open_tasks)),
                                      str(len(epic.completed_tasks)),
                                      key=epic.id)
                    else:
                        inactive_table.add_row(str(epic.id),
                                               shorten_text(epic.name),
                                               shorten_text(epic.description),
                                               epic.status.name,
                                               str(len(epic.open_tasks)),
                                               str(len(epic.completed_tasks)),
                                               key=epic.id)
                if table.row_count:
                    yield Label("Active epics")
                    yield table
                if inactive_table.row_count:
                    yield Rule(line_style="heavy")
                    yield Label("Inactive epics")
                    yield inactive_table
            with TabPane("Stories", id="stories"):
                yield Button("+Story",
                             id="new_story",
                             variant="success",
                             classes="new_entity")
                table = DataTable(id="project_stories_table")
                inactive_table = DataTable(id="project_inactive_stories_table")
                for column in ("id", "name", "description", "status",
                               "open_tasks", "completed_tasks"):
                    table.add_column(column, key=f"story_{column}")
                    inactive_table.add_column(column,
                                              key=f"inactive_story_{column}")
                for story in sorted(self.entity.stories,
                                    key=lambda x: len(x.tasks),
                                    reverse=True):
                    if story.open_tasks:
                        table.add_row(str(story.id),
                                      shorten_text(story.name),
                                      shorten_text(story.description),
                                      story.status.name,
                                      str(len(epic.open_tasks)),
                                      str(len(epic.completed_tasks)),
                                      key=story.id)
                    else:
                        inactive_table.add_row(str(story.id),
                                               shorten_text(story.name),
                                               shorten_text(story.description),
                                               story.status.name,
                                               str(len(epic.open_tasks)),
                                               str(len(epic.completed_tasks)),
                                               key=story.id)
                if table.row_count:
                    yield Label("Active stories")
                    yield table
                if inactive_table.row_count:
                    yield Rule(line_style="heavy")
                    yield Label("Inactive stories")
                    yield inactive_table
            with TabPane("Notes", id="notes"):
                yield Button("+Note",
                             id="new_note",
                             variant="success",
                             classes="new_entity")
                table = DataTable(id="project_notes_table")
                for column in ("id", "text"):
                    table.add_column(column, key=f"note_{column}")
                for note in self.entity.notes:
                    table.add_row(str(note.id), note.name, key=note.id)
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

    def action_new_task(self):
        self.push_screen(ui_components.NewTask(), self.task_new_callback)

    def action_task_show(self):
        self.push_screen(ui_components.ShowTask())

    @on(Button.Pressed)
    def open_new_element_window(self, event: Button.Pressed) -> None:
        if event.button.id == "new_task":
            self.push_screen(ui_components.NewTask(), self.task_new_callback)
        elif event.button.id == "new_epic":
            self.push_screen(ui_components.NewEpic(), self.epic_new_callback)
        elif event.button.id == "new_story":
            self.push_screen(ui_components.NewStory(), self.story_new_callback)

    def task_new_callback(self, result: list[commands.Command]):
        object_id = self._process_commands_chain(result,
                                                 project=self.project_id)
        self.notify(f"New task created with id {object_id}!")

    def epic_new_callback(self, result: commands.CreateEpic):
        result.project = self.entity.name
        epic = self.bus.handle(result)
        self.notify(f"New epic created: {epic}!")

    def story_new_callback(self, result: commands.CreateStory):
        result.project = self.entity.name
        story = self.bus.handle(result)
        self.notify(f"New story created: {story}!")


class TerkaSprint(App, PopupsMixin, SelectionMixin, SortingMixin):

    CSS_PATH = "entities.css"

    BINDINGS = [("n", "new_task", "New Task"), ("t", "tasks", "Tasks"),
                ("N", "notes", "Notes"), ("i", "show_info", "Info"),
                ("o", "overview", "Overview"), ("q", "quit", "Quit"),
                ("s", "sort", "Sort"), ("E", "task_edit", "Edit"),
                ("r", "refresh", "Refresh"), ("d", "task_complete", "Done"),
                ("X", "task_delete", "Delete"), ("a", "task_add", "Add"),
                ("C", "task_comment", "Comment"),
                ("U", "task_update_context", "Update"), ("T", "time", "Time")]

    def __init__(self, entity, bus) -> None:
        super().__init__()
        self.entity = entity
        self.bus = bus
        self.sprint_id = entity.id
        self.tasks = self.get_tasks()
        self.selected_task = None
        self.selected_column = None

    def get_tasks(self, all: bool = False):
        for sprint_task in self.entity.tasks:
            if all:
                yield sprint_task.tasks
            elif sprint_task.tasks.status.name not in ("DONE", "DELETED"):
                yield sprint_task.tasks

    def action_refresh(self):
        self.exit(return_code=4)

    def on_mount(self) -> None:
        self.title = "Sprint"
        self.sub_title = (
            f'Workspace: {self.bus.config.get("workspace")}; '
            f'Time spent today - {Formatter.format_time_spent(self.entity.time_spent_today)}'
        )

    def compose(self) -> ComposeResult:
        yield ui_components.Sidebar(classes="-hidden")
        if self.entity.status.name == "COMPLETED":
            yield Header(classes="completed_sprint")
        elif self.entity.status.name == "ACTIVE":
            yield Header(classes="active_sprint")
        else:
            yield Header(classes="planned_sprint")
        yield Static(
            f"[bold]Sprint {self.entity.id}[/bold]: \n{self.entity.goal}",
            classes="header")
        with TabbedContent(initial="tasks"):
            with TabPane("Tasks", id="tasks"):
                if self.entity.status.name != "COMPLETED":
                    yield Button("+Task",
                                 id="new_task",
                                 variant="success",
                                 classes="new_entity")
                table = DataTable(id="sprint_open_tasks_table")
                for column in ("id", "name", "status", "priority",
                               "story_points", "project", "due_date",
                               "assignee", "tags", "collaborators",
                               "time_spent"):
                    table.add_column(column, key=column)
                for sprint_task in sorted(self.entity.tasks,
                                          key=lambda x: x.tasks.status.value,
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
                    if len(commentaries := task.commentaries) > 0:
                        task_name = f"{task.name} [blue][{len(task.commentaries)}][/blue]"
                    else:
                        task_name = task.name
                    if task.status.name not in ("DONE", "DELETED"):
                        table.add_row(task_id,
                                      task_name,
                                      task.status.name,
                                      task.priority.name,
                                      str(sprint_task.story_points),
                                      task.project_.name,
                                      task.due_date,
                                      str(task.assigned_to.name)
                                      if task.assigned_to else "",
                                      tags_text,
                                      collaborator_string,
                                      Formatter.format_time_spent(
                                          task.total_time_spent),
                                      key=task.id)
                yield table
            with TabPane("Completed Tasks", id="completed_tasks"):
                table = DataTable(id="sprint_completed_tasks_table")
                for column in ("id", "name", "project", "completion_date",
                               "assignee", "tags", "collaborators",
                               "story_points", "time_spent"):
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
                    if len(commentaries := task.commentaries) > 0:
                        task_name = f"{task.name} [blue][{len(task.commentaries)}][/blue]"
                    else:
                        task_name = task.name
                    if task.status.name in ("DONE", "DELETED"):
                        table.add_row(
                            str(task.id),
                            task_name,
                            task.project_.name,
                            task.completion_date.strftime("%Y-%m-%d")
                            if task.completion_date else "",
                            str(task.assigned_to.name)
                            if task.assigned_to else "",
                            tags_text,
                            collaborator_string,
                            Formatter.format_time_spent(
                                round(sprint_task.story_points * 60)),
                            Formatter.format_time_spent(task.total_time_spent),
                            key=task.id)
                yield table
            with TabPane("Notes", id="notes"):
                table = DataTable(id="sprint_notes_table")
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
                    with self.bus.uow as uow:
                        workspace = services.get_workplace_by_name(
                            self.bus.config.get("workspace"), uow.repo)
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
                project_split = defaultdict(int)
                for task in self.get_tasks(all=True):
                    project = task.project_.name
                    project_split[project] += task.total_time_spent
                collaborators = self.entity.collaborators
                sorted_collaborators = ""
                for name, value in sorted(collaborators.items(),
                                          key=lambda x: x[1],
                                          reverse=True):
                    sorted_collaborators += f"  * {name}: {Formatter.format_time_spent(value)} \n"
                sorted_projects = ""
                for name, value in sorted(project_split.items(),
                                          key=lambda x: x[1],
                                          reverse=True):
                    sorted_projects += f"  * {name}: {Formatter.format_time_spent(value)} \n"
                yield MarkdownViewer(f"""
# Sprint details:
* Period: {self.entity.start_date} - {self.entity.end_date}
* Open tasks: {len(self.entity.open_tasks)} ({len(self.entity.tasks)})
* Pct Completed: {round(self.entity.pct_completed, 2) :.0%}
* Velocity: {self.entity.velocity}
* Time spend: {Formatter.format_time_spent(self.entity.total_time_spent)}
* Utilization: {round(self.entity.utilization, 2) :.0%}
## Collaborator split:
{sorted_collaborators}
## Project split:
{sorted_projects}
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

    def action_new_task(self):
        if self.entity.status.name != "COMPLETED":
            self.push_screen(ui_components.NewTask(), self.task_new_callback)

    def task_new_callback(self, result: list[commands.Command]):
        object_id = self._process_commands_chain(result)
        self.notify(f"New task created with id {object_id}!")

    @on(Button.Pressed)
    def open_new_element_window(self, event: Button.Pressed) -> None:
        if event.button.id == "new_task":
            self.push_screen(ui_components.NewTask(), self.task_new_callback)


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
