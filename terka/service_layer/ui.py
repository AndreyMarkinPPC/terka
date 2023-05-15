from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Header, Static, Input


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
        self.is_completed = is_completed
        self.history = history
        self.commentaries = commentaries
        self.is_overdue = datetime.today().date(
        ) > entity.due_date if entity.due_date else False

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
        yield Static(f"Created {creation_message}", classes="header_simple")
        if self.is_completed:
            completion_date = self._get_completion_date()
            if completion_date:
                completed_days_ago = (datetime.now() - completion_date).days
                completion_message = f"{completed_days_ago} days ago" if completed_days_ago > 1 else "today"
                yield Static(
                    f"Completed {completion_message} ({completion_date.strftime('%Y-%m-%d')})",
                    classes="header_simple")
            else:
                yield Static("Completion date unknown", classes="header_simple")
        else:
            yield Static(f"Due date: {self.entity.due_date}", classes="header_simple")
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
        yield Input(placeholder="Add a comment", classes="body", id="comment")
        # yield Comment()

    # def on_input_changed(self, event: Input.Changed) -> None:
    #     self.query_one(Comment).text = event.value

    def _get_completion_date(self):
        for event in self.history:
            if event.new_value == "DONE":
                return event.date

