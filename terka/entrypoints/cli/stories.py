from typing import Optional

import typer
from typing_extensions import Annotated

from terka.service_layer import handlers

app = typer.Typer()

StoryId = Annotated[
  int,
  typer.Argument(
    help='Story id',
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
    help='Story specific comment',
    prompt=True,
  ),
]


@app.command()
def list(ctx: typer.Context):
  """Lists all the stories."""
  cmd = {'command': 'list', 'entity': 'stories', 'task_dict': {}}
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def create(
  ctx: typer.Context,
  name: Annotated[str, typer.Option(help='Story name', prompt=True)],
  project: Annotated[
    str,
    typer.Option(help='Project to add story to', prompt=True),
  ],
  due_date: Annotated[
    Optional[str],
    typer.Option(help='Story relative due date'),
  ] = None,
):
  """Creates new story."""
  cmd = {
    'command': 'create',
    'entity': 'stories',
    'task_dict': {'name': name, 'project': project, 'due_date': due_date},
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def show(ctx: typer.Context, story_id: StoryId):
  """Shows story by id."""
  cmd = {'command': 'show', 'entity': 'stories', 'task_dict': {'id': story_id}}
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def complete(ctx: typer.Context, story_id: StoryId):
  """Completes selected story."""
  cmd = {
    'command': 'complete',
    'entity': 'stories',
    'task_dict': {'id': story_id},
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def delete(ctx: typer.Context, story_id: StoryId):
  """Deletes selected story."""
  cmd = {
    'command': 'delete',
    'entity': 'stories',
    'task_dict': {'id': story_id},
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def comment(
  ctx: typer.Context,
  story_id: StoryId,
  text: Comment,
):
  """Adds comment to an story."""
  cmd = {
    'command': 'delete',
    'entity': 'stories',
    'task_dict': {'id': story_id, 'text': text},
  }
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.callback(invoke_without_command=True)
def main(
  ctx: typer.Context,
):
  list(ctx)
