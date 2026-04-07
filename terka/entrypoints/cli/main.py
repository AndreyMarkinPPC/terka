from __future__ import annotations

import os

import typer
from sqlalchemy import create_engine
from typing_extensions import Annotated

from terka import __version__, bootstrap
from terka.adapters.orm import metadata
from terka.entrypoints.cli import (
  epics,
  projects,
  sprints,
  stories,
  tags,
  tasks,
  users,
  workspaces,
)
from terka.service_layer import unit_of_work
from terka.utils import load_config

HOME_DIR = os.path.expanduser('~')
DB_URL = f'sqlite:////{HOME_DIR}/.terka/tasks.db'

typer_app = typer.Typer()
typer_app.add_typer(
  tasks.app,
  name='tasks',
)
typer_app.add_typer(
  projects.app, name='projects', short_help='Project management'
)
typer_app.add_typer(sprints.app, name='sprints')
typer_app.add_typer(
  workspaces.app, name='workspaces', short_help='Workspace management'
)
typer_app.add_typer(users.app, name='users', short_help='User management')
typer_app.add_typer(epics.app, name='epics', short_help='Work with epics')
typer_app.add_typer(stories.app, name='stories', short_help='Work with stories')
typer_app.add_typer(tags.app, name='tags', short_help='Work with tags')
LogLevel = Annotated[
  str,
  typer.Option(
    help='Level of logging',
  ),
]


def init_db(home_dir):
  engine = create_engine(f'sqlite:////{home_dir}/.terka/tasks.db')
  metadata.create_all(engine)
  return engine


@typer_app.command()
def version():
  """Display app version."""
  print(f'terka version {__version__}')
  raise typer.Exit()


@typer_app.callback()
def main(
  ctx: typer.Context,
):
  config = load_config(HOME_DIR)
  ctx.obj = {}
  ctx.obj['bus'] = bootstrap.bootstrap(
    start_orm=True, uow=unit_of_work.SqlAlchemyUnitOfWork(DB_URL), config=config
  )


if __name__ == '__main__':
  typer_app()
