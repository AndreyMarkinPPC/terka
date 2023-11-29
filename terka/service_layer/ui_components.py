from datetime import datetime
from textual import on
from textual.app import ComposeResult
from textual.containers import Grid
from textual.screen import ModalScreen
from textual.validation import Number
from textual.widgets import Button, Input, Label, Select

from terka.domain import _commands


class TaskAdd(ModalScreen[str]):

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"Add task", id="question"),
            Input(placeholder="To sprint", id="sprint", validators=[Number()]),
            Input(placeholder="To epic", id="epic", validators=[Number()]),
            Input(placeholder="To story", id="story", validators=[Number()]),
            Input(placeholder="Story points", id="story-points", validators=[Number()]),
            Button("Confirm", id="yes"),
            Button("Cancel", id="no"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            sprint = self.query_one("#sprint", Input)
            epic = self.query_one("#epic", Input)
            story = self.query_one("#story", Input)
            story_points = self.query_one("#story-points", Input)
            self.dismiss(
                _commands.AddTask(id=None,
                                  sprint=sprint.value,
                                  epic=epic.value,
                                  story=story.value,
                                  story_points=story_points.value))
        else:
            self.app.pop_screen()

    @on(Input.Submitted)
    def submit_input(self, event: Input.Submitted) -> None:
        exit(self)


class TaskEdit(ModalScreen[str]):

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"Edit task", id="question"),
            Input(placeholder="Name", id="name"),
            Input(placeholder="Description", id="description"),
            Select(((line, line) for line in [
                "BACKLOG", "TODO", "IN_PROGRESS", "REVIEW", "DONE", "DELETED"
            ]),
                   prompt="status",
                   id="status"),
            Select(
                ((line, line) for line in ["LOW", "NORMAL", "HIGH", "URGENT"]),
                prompt="priority",
                id="priority"),
            Input(placeholder="Add due date", id="due_date"),
            Input(placeholder="Add time spent",
                  validators=[Number()],
                  id="hours"),
            Input(placeholder="Comment", id="comment"),
            Button("Yes", id="yes"),
            Button("No", id="no"),
            id="edit-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            name = self.query_one("#name", Input)
            description = self.query_one("#description", Input)
            status = self.query_one("#status", Select)
            priority = self.query_one("#priority", Select)
            due_date = self.query_one("#due_date", Input)
            comment = self.query_one("#comment", Input)
            if due_date := due_date.value:
                due_date = datetime.strptime(due_date, "%Y-%m-%d")
            self.dismiss((_commands.UpdateTask(id=None,
                                               name=name.value,
                                               description=description.value,
                                               due_date=due_date,
                                               status=status.value,
                                               priority=priority.value),
                          _commands.CommentTask(id=None, text=comment.value)))
        else:
            self.app.pop_screen()

    @on(Input.Submitted)
    def submit_input(self, event: Input.Submitted) -> None:
        exit(self)


class TaskComplete(ModalScreen[str]):

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"Complete task", id="question"),
            Input(placeholder="Add comment", id="comment"),
            Input(placeholder="Add time spent",
                  validators=[Number()],
                  id="hours"),
            Button("Yes", id="yes"),
            Button("No", id="no"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            comment = self.query_one("#comment", Input)
            hours = self.query_one("#hours", Input)
            self.dismiss(
                _commands.CompleteTask(id=None,
                                       comment=comment.value,
                                       hours=hours.value))
        else:
            self.app.pop_screen()

    @on(Input.Submitted)
    def submit_input(self, event: Input.Submitted) -> None:
        exit(self)


class TaskDelete(ModalScreen[str]):

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"Delete task", id="question"),
            Input(placeholder="Add comment", id="comment"),
            Input(placeholder="Add time spent",
                  validators=[Number()],
                  id="hours"),
            Button("Yes", id="yes"),
            Button("No", id="no"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            comment = self.query_one("#comment", Input)
            hours = self.query_one("#hours", Input)
            self.dismiss(
                _commands.DeleteTask(id=None,
                                     comment=comment.value,
                                     hours=hours.value))
        else:
            self.app.pop_screen()

    @on(Input.Submitted)
    def submit_input(self, event: Input.Submitted) -> None:
        exit(self)


class TaskStatusEdit(ModalScreen[str]):

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"Change status", id="question"),
            Select(((line, line) for line in [
                "BACKLOG", "TODO", "IN_PROGRESS", "REVIEW", "DONE", "DELETED"
            ]),
                   prompt="status",
                   id="status"),
            Button("Confim", id="yes"),
            Button("Cancel", id="no"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            status = self.query_one("#status", Select)
            self.dismiss(status.value)
        else:
            self.app.pop_screen()

    @on(Input.Submitted)
    def submit_input(self, event: Input.Submitted) -> None:
        exit(self)


class TaskPriorityEdit(ModalScreen[str]):

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"Change priority", id="question"),
            Select(
                ((line, line) for line in ["LOW", "NORMAL", "HIGH", "URGENT"]),
                prompt="priority",
                id="priority"),
            Button("Confim", id="yes"),
            Button("Cancel", id="no"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            priority = self.query_one("#priority", Select)
            self.dismiss(priority.value)
        else:
            self.app.pop_screen()

    @on(Input.Submitted)
    def submit_input(self, event: Input.Submitted) -> None:
        exit(self)


class TaskStoryPointsEdit(ModalScreen[str]):

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"Add story points", id="question"),
            Input(placeholder="Story points",
                  id="story-points",
                  validators=[Number()]),
            Button("Confim", id="yes"),
            Button("Cancel", id="no"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            story_points = self.query_one("#story-points", Input)
            self.dismiss(story_points.value)
        else:
            self.app.pop_screen()

    @on(Input.Submitted)
    def submit_input(self, event: Input.Submitted) -> None:
        exit(self)


class TaskHoursSubmitted(ModalScreen[str]):

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"Add time spent", id="question"),
            Input(placeholder="Time spent in minutes",
                  id="hours",
                  validators=[Number()]),
            Button("Confim", id="yes"),
            Button("Cancel", id="no"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            story_points = self.query_one("#hours", Input)
            self.dismiss(story_points.value)
        else:
            self.app.pop_screen()

    @on(Input.Submitted)
    def submit_input(self, event: Input.Submitted) -> None:
        exit(self)
