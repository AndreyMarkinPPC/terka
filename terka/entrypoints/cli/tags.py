import typer

from terka.service_layer import handlers

app = typer.Typer()


@app.command()
def list(ctx: typer.Context):
  """Lists all tags."""
  cmd = {'command': 'list', 'entity': 'tags', 'task_dict': {}}
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def create(ctx: typer.Context, tag: str):
  """Creates new tag."""
  cmd = {'command': 'create', 'entity': 'tags', 'task_dict': {'text': tag}}
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.callback(invoke_without_command=True)
def main(
  ctx: typer.Context,
):
  list(ctx)
