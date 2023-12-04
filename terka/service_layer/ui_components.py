from datetime import datetime
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Grid
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.validation import Number
from textual.widgets import Button, Input, Label, Select, Static

from terka.domain import _commands

class Text(Static):
    text = reactive("", layout=True)

    def render(self) -> str:
        return f"{self.__class__.__name__}: {self.text}"


class Value(Static):
    value = reactive("", layout=True)

    def render(self) -> str:
        return f"{self.__class__.__name__}: {self.value}"


class Title(Text):
    ...


class Description(Text):
    ...


class Status(Value):
    ...


class Priority(Value):
    ...


class Project(Value):
    ...


class Sidebar(Container):

    def compose(self) -> ComposeResult:
        yield Container(Title(classes="header"), Description(), Status(),
                        Priority(), Project())

class TerkaModalScreen(ModalScreen[str]):
    BINDINGS = [("escape", "quit", "Quit")]

    @on(Input.Submitted)
    def submit_input(self, event: Input.Submitted) -> None:
        self.app.pop_screen()

    def action_quit(self):
        self.app.pop_screen()


class NewTask(TerkaModalScreen):

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"New task", id="question"),
            Input(placeholder="Name", id="name", classes="text-input"),
            Input(placeholder="Description",
                  id="description",
                  classes="description-input"),
            Select(((line, line) for line in [
                "BACKLOG", "TODO", "IN_PROGRESS", "REVIEW", "DONE", "DELETED"
            ]),
                   prompt="status",
                   value="BACKLOG",
                   id="status"),
            Select(
                ((line, line) for line in ["LOW", "NORMAL", "HIGH", "URGENT"]),
                prompt="priority",
                value="NORMAL",
                id="priority"),
            Input(placeholder="Add due date", id="due_date"),
            Input(placeholder="sprint", id="sprint", validators=[Number()]),
            Input(placeholder="epic", id="epic", validators=[Number()]),
            Input(placeholder="story", id="story", validators=[Number()]),
            Input(placeholder="tags", id="tags"),
            Input(placeholder="collaborators", id="collaborators"),
            Button("Save", id="yes", variant="success"),
            Button("No", id="no"),
            id="new-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            name = self.query_one("#name", Input)
            description = self.query_one("#description", Input)
            status = self.query_one("#status", Select)
            priority = self.query_one("#priority", Select)
            due_date = self.query_one("#due_date", Input)
            if due_date := due_date.value:
                due_date = datetime.strptime(due_date, "%Y-%m-%d")
            else:
                due_date = None
            sprint = self.query_one("#sprint", Input)
            epic = self.query_one("#epic", Input)
            story = self.query_one("#story", Input)
            tags = self.query_one("#tags", Input)
            collaborators = self.query_one("#collaborators", Input)
            commands = []
            create_command = _commands.CreateTask(
                name=name.value,
                description=description.value,
                due_date=due_date,
                status=status.value,
                priority=priority.value)
            commands.append(create_command)
            if sprint.value or story.value or epic.value:
                add_command = _commands.AddTask(id=None,
                                                sprint=sprint.value,
                                                epic=epic.value,
                                                story=story.value)
                commands.append(add_command)
            if tags.value:
                tag_command = _commands.TagTask(id=None, tag=tags.value)
                commands.append(tag_command)
            if collaborators.value:
                collaborator_command = _commands.CollaborateTask(
                    id=None, collaborator=collaborators.value)
                commands.append(collaborator_command)
            self.dismiss(commands)
        else:
            self.app.pop_screen()


class NewEpic(TerkaModalScreen):

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"New epic", id="question"),
            Input(placeholder="Name", id="name", classes="text-input"),
            Input(placeholder="Description",
                  id="description",
                  classes="description-input"),
            Button("Save", id="yes", variant="success"),
            Button("No", id="no"),
            id="new-composite-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            name = self.query_one("#name", Input)
            description = self.query_one("#description", Input)
            self.dismiss(
                _commands.CreateEpic(name=name.value,
                                     description=description.value))
        else:
            self.app.pop_screen()


class NewStory(TerkaModalScreen):

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"New story", id="question"),
            Input(placeholder="Name", id="name", classes="text-input"),
            Input(placeholder="Description",
                  id="description",
                  classes="description-input"),
            Button("Save", id="yes", variant="success"),
            Button("No", id="no"),
            id="new-composite-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            name = self.query_one("#name", Input)
            description = self.query_one("#description", Input)
            self.dismiss(
                _commands.CreateStory(name=name.value,
                                      description=description.value))
        else:
            self.app.pop_screen()


class TaskAdd(TerkaModalScreen):

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"Add task", id="question"),
            Input(placeholder="To sprint", id="sprint", validators=[Number()]),
            Input(placeholder="To epic", id="epic", validators=[Number()]),
            Input(placeholder="To story", id="story", validators=[Number()]),
            Input(placeholder="Story points",
                  id="story-points",
                  validators=[Number()]),
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


class ShowTask(TerkaModalScreen):

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Task info", id="question"),
            Static(f"[b]Name:[/b] ", id="name"),
            Static("Description", id="description"),
            Static("status", id="status"),
            Static("priority", id="priority"),
            Static("due date", id="due_date"),
            id="edit-dialog",
        )


class TaskEdit(TerkaModalScreen):

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"Edit task", id="question"),
            Input(placeholder="Name", id="name"),
            Input(placeholder="Description",
                  id="description",
                  classes="description-input"),
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
            Button("Save", id="yes", variant="success"),
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


class TaskComplete(TerkaModalScreen):

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"Complete task", id="question"),
            Input(placeholder="Add comment", id="comment"),
            Input(placeholder="Add time spent",
                  validators=[Number()],
                  id="hours"),
            Button("Yes", id="yes", variant="success"),
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


class TaskDelete(TerkaModalScreen):

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"Delete task", id="question"),
            Input(placeholder="Add comment", id="comment"),
            Input(placeholder="Add time spent",
                  validators=[Number()],
                  id="hours"),
            Button("Yes", id="yes", variant="success"),
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


class TaskStatusEdit(TerkaModalScreen):

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"Change status", id="question"),
            Select(((line, line) for line in [
                "BACKLOG", "TODO", "IN_PROGRESS", "REVIEW", "DONE", "DELETED"
            ]),
                   classes="small-select",
                   prompt="status",
                   id="status"),
            Button("Confim", id="yes", variant="success"),
            Button("Cancel", id="no"),
            id="small-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            status = self.query_one("#status", Select)
            self.dismiss(status.value)
        else:
            self.app.pop_screen()


class TaskPriorityEdit(TerkaModalScreen):

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"Change priority", id="question"),
            Select(
                ((line, line) for line in ["LOW", "NORMAL", "HIGH", "URGENT"]),
                prompt="priority",
                classes="small-select",
                id="priority"),
            Button("Confim", id="yes", variant="success"),
            Button("Cancel", id="no"),
            id="small-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            priority = self.query_one("#priority", Select)
            self.dismiss(priority.value)
        else:
            self.app.pop_screen()


class TaskStoryPointsEdit(TerkaModalScreen):

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
