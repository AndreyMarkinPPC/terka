"""Works with workspaces."""

from typing import Optional

import typer
from typing_extensions import Annotated

from terka.service_layer import handlers

app = typer.Typer()

Workspace = Annotated[
  str,
  typer.Argument(
    help='Workspace name or id',
  ),
]


@app.command()
def list(ctx: typer.Context):
  """Lists all available workspaces."""
  cmd = {'command': 'list', 'entity': 'workspaces', 'task_dict': {}}
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def create(
  ctx: typer.Context,
  name: Annotated[str, typer.Option(help='Workspace name', prompt=True)],
  description: Annotated[
    Optional[str], typer.Option(help='Brief description of a workspace')
  ] = None,
):
  """Creates new workspace."""
  cmd = {
    'command': 'create',
    'entity': 'workspaces',
    'task_dict': {
      'name': name,
      'description': description,
    },
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def show(ctx: typer.Context, id: Workspace):
  """Shows workspace by name or ID."""
  cmd = {'command': 'show', 'entity': 'workspaces', 'task_dict': {'id': id}}
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.callback(invoke_without_command=True)
def main(
  ctx: typer.Context,
):
  list(ctx)
