import typer

from terka.service_layer import handlers

app = typer.Typer()


@app.command()
def list(ctx: typer.Context):
  """Lists all users."""
  cmd = {'command': 'list', 'entity': 'users', 'task_dict': {}}
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.command()
def create(ctx: typer.Context, name: str):
  """Creates new user."""
  cmd = {'command': 'create', 'entity': 'users', 'task_dict': {'name': name}}
  handlers.CommandHandler(ctx.obj['bus']).execute(**cmd)


@app.callback(invoke_without_command=True)
def main(
  ctx: typer.Context,
):
  list(ctx)
