from typing import Optional

import typer
from typing_extensions import Annotated

from terka.service_layer import handlers

app = typer.Typer()

Project = Annotated[
  str,
  typer.Argument(
    help='Project name or id',
  ),
]


@app.command()
def list(
  ctx: typer.Context,
  status: Annotated[str, typer.Option(help='Project status')] = 'ACTIVE',
):
  """Lists active projects."""
  cmd = {
    'command': 'list',
    'entity': 'projects',
    'task_dict': {'status': status},
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def create(
  ctx: typer.Context,
  name: Annotated[Optional[str], typer.Option(help='Project name')] = None,
  description: Annotated[
    Optional[str], typer.Option(help='Brief description of a project')
  ] = None,
  workspace: Annotated[
    Optional[str], typer.Option(help='Project workspace')
  ] = None,
):
  """Creates new project base on a provided short alias."""
  cmd = {
    'command': 'create',
    'entity': 'projects',
    'task_dict': {
      'name': name,
      'description': description,
      'workspace': workspace,
    },
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def show(ctx: typer.Context, project: Project):
  cmd = {'command': 'show', 'entity': 'projects', 'task_dict': {'id': project}}
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def complete(ctx: typer.Context, project: Project):
  cmd = {
    'command': 'complete',
    'entity': 'projects',
    'task_dict': {'id': project},
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.callback(invoke_without_command=True)
def main(
  ctx: typer.Context,
):
  list(ctx)
