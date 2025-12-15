from typing import Optional

import typer
from typing_extensions import Annotated

from terka.service_layer import handlers

app = typer.Typer()

EpicId = Annotated[
  int,
  typer.Argument(
    help='Epic id',
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
    help='Epic specific comment',
    prompt=True,
  ),
]


@app.command()
def list(ctx: typer.Context):
  """Lists all the epics."""
  cmd = {'command': 'list', 'entity': 'epics', 'task_dict': {}}
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def create(
  ctx: typer.Context,
  name: Annotated[str, typer.Option(help='Epic name', prompt=True)],
  project: Annotated[
    str,
    typer.Option(help='Project to add epic to', prompt=True),
  ],
  due_date: Annotated[
    Optional[str],
    typer.Option(help='Epic relative due date'),
  ] = None,
):
  """Creates new epic."""
  cmd = {
    'command': 'create',
    'entity': 'epics',
    'task_dict': {'name': name, 'project': project, 'due_date': due_date},
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def show(ctx: typer.Context, epic_id: EpicId):
  """Shows epic by id."""
  cmd = {'command': 'show', 'entity': 'epics', 'task_dict': {'id': epic_id}}
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def complete(ctx: typer.Context, epic_id: EpicId):
  """Completes selected epic."""
  cmd = {
    'command': 'complete',
    'entity': 'epics',
    'task_dict': {'id': epic_id},
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def delete(ctx: typer.Context, epic_id: EpicId):
  """Deletes selected epic."""
  cmd = {'command': 'delete', 'entity': 'epics', 'task_dict': {'id': epic_id}}
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def comment(
  ctx: typer.Context,
  epic_id: EpicId,
  text: Comment,
):
  """Adds comment to an epic."""
  cmd = {
    'command': 'delete',
    'entity': 'epics',
    'task_dict': {'id': epic_id, 'text': text},
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.callback(invoke_without_command=True)
def main(
  ctx: typer.Context,
):
  list(ctx)
