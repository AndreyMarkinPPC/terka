"""Task management commands."""

from typing import Optional

import typer
from typing_extensions import Annotated

from terka.service_layer import handlers

app = typer.Typer(short_help='Create and assign tasks')

TaskId = Annotated[
  int,
  typer.Argument(
    help='Task id',
  ),
]

Hours = Annotated[
  Optional[float],
  typer.Option(
    help='Time spent on task (in hours)',
    prompt=True,
  ),
]

Comment = Annotated[
  Optional[str],
  typer.Option(
    help='Task specific comment',
    prompt=True,
  ),
]


@app.command()
def list(ctx: typer.Context):
  """Lists all the tasks."""
  cmd = {'command': 'list', 'entity': 'tasks', 'task_dict': {}}
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def create(
  ctx: typer.Context,
  name: Annotated[str, typer.Option(help='Task name', prompt=True)],
  description: Annotated[
    Optional[str], typer.Option(help='Brief description of a task')
  ] = None,
  project: Annotated[
    Optional[str],
    typer.Option(help='Project to add task to'),
  ] = None,
  due_date: Annotated[
    Optional[str],
    typer.Option(help='Task relative due date'),
  ] = None,
):
  """Creates a task."""
  cmd = {
    'command': 'create',
    'entity': 'tasks',
    'task_dict': {
      'name': name,
      'description': description,
      'project': project,
      'due_date': due_date,
    },
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def show(ctx: typer.Context, task_id: TaskId):
  """Shows a single task."""
  cmd = {'command': 'show', 'entity': 'tasks', 'task_dict': {'id': task_id}}
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def update(
  ctx: typer.Context,
  task_id: TaskId,
  name: Annotated[Optional[str], typer.Option(help='Task name')] = None,
  description: Annotated[
    Optional[str], typer.Option(help='Task description')
  ] = None,
  status: Annotated[Optional[str], typer.Option(help='Task Status')] = None,
  priority: Annotated[Optional[str], typer.Option(help='Task priority')] = None,
):
  """Updates task with provided options."""
  cmd = {
    'command': 'update',
    'entity': 'tasks',
    'task_dict': {
      'id': task_id,
      'name': name,
      'description': description,
      'status': status,
      'priority': priority,
    },
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def complete(ctx: typer.Context, task_id: TaskId, hours: Hours):
  """Completes task with optional hours spent."""
  cmd = {
    'command': 'complete',
    'entity': 'tasks',
    'task_dict': {'id': task_id, 'hours': hours},
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def delete(ctx: typer.Context, task_id: TaskId, comment: Comment):
  """Delete task with optional message."""
  cmd = {
    'command': 'delete',
    'entity': 'tasks',
    'task_dict': {'id': task_id, 'text': comment},
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def comment(
  ctx: typer.Context,
  task_id: TaskId,
  text: str,
):
  """Adds a comment to the task."""
  cmd = {
    'command': 'delete',
    'entity': 'tasks',
    'task_dict': {'id': task_id, 'text': text},
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def assign(
  ctx: typer.Context,
  task_id: TaskId,
  user: str,
):
  """Assigns task to a user."""
  cmd = {
    'command': 'assign',
    'entity': 'tasks',
    'task_dict': {'id': task_id, 'user': user},
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def tag(
  ctx: typer.Context,
  task_id: TaskId,
  tag: str,
):
  """Adds tag to a task."""
  cmd = {
    'command': 'tag',
    'entity': 'tasks',
    'task_dict': {'id': task_id, 'tag': tag},
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def collaborate(
  ctx: typer.Context,
  task_id: TaskId,
  user: str,
):
  """Adds collaborator to a task."""
  cmd = {
    'command': 'collaborate',
    'entity': 'tasks',
    'task_dict': {'id': task_id, 'collaborator': user},
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def track(
  ctx: typer.Context,
  task_id: TaskId,
  minutes: float,
):
  """Tracks minutes spent on a task."""
  cmd = {
    'command': 'track',
    'entity': 'tasks',
    'task_dict': {'id': task_id, 'minutes': minutes},
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def add(
  ctx: typer.Context,
  task_id: TaskId,
  to_sprint=Annotated[
    Optional[int],
    typer.Option(
      help='Sprint to add to',
      prompt=True,
    ),
  ],
):
  """Adds task to a sprint."""
  cmd = {
    'command': 'add',
    'entity': 'tasks',
    'task_dict': {'id': task_id, 'sprint': to_sprint},
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.callback(invoke_without_command=True)
def main(
  ctx: typer.Context,
):
  list(ctx)
