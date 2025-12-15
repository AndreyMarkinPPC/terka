from typing import Optional

import typer
from typing_extensions import Annotated

from terka.service_layer import handlers

app = typer.Typer(short_help='Sprint management')

SprintId = Annotated[
  int,
  typer.Argument(
    help='Sprint Id',
  ),
]


@app.command()
def list(
  ctx: typer.Context,
  status: Annotated[list[str], typer.Option(help='Sprint status')] = [
    'PLANNED',
    'ACTIVE',
  ],
):
  """Lists all active or planned sprints."""
  cmd = {
    'command': 'list',
    'entity': 'sprints',
    'task_dict': {'status': status},
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def create(
  ctx: typer.Context,
  goal: Annotated[Optional[str], typer.Option(help='Goal of a sprint')] = None,
):
  """Creates new sprint with an optional goal."""
  cmd = {'command': 'create', 'entity': 'sprints', 'task_dict': {'goal': goal}}
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def show(ctx: typer.Context, id: SprintId):
  """Shows a single sprint."""
  cmd = {'command': 'show', 'entity': 'sprints', 'task_dict': {'id': id}}
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def start(ctx: typer.Context, id: SprintId):
  """Starts selected sprint."""
  cmd = {'command': 'start', 'entity': 'sprints', 'task_dict': {'id': id}}
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def complete(ctx: typer.Context, id: SprintId):
  """Completes selected sprint."""
  cmd = {'command': 'complete', 'entity': 'sprints', 'task_dict': {'id': id}}
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.callback(invoke_without_command=True)
def main(
  ctx: typer.Context,
):
  list(ctx)
