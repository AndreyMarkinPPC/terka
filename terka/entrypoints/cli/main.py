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


def _version_callback(show_version: bool) -> None:
  if show_version:
    print(f'terka version {__version__}')
    raise typer.Exit()


@typer_app.callback()
def main(
  ctx: typer.Context,
  version: Annotated[
    bool,
    typer.Option(
      help='Display library version',
      callback=_version_callback,
      is_eager=True,
      expose_value=False,
    ),
  ] = False,
):
  config = load_config(HOME_DIR)
  ctx.obj = {}
  ctx.obj['bus'] = bootstrap.bootstrap(
    start_orm=True, uow=unit_of_work.SqlAlchemyUnitOfWork(DB_URL), config=config
  )


# parser = argparse.ArgumentParser()
# parser.add_argument('command', nargs='?')
# parser.add_argument('entity', nargs='?')
# parser.add_argument('--log', '--loglevel', dest='loglevel', default='info')
# parser.add_argument('-v', '--version', dest='version', action='store_true')
# args = parser.parse_known_args()
# args, kwargs = args
# console = Console()
# command, entity = args.command, args.entity
# home_dir = os.path.expanduser('~')
# if args.version:
#   print(f'terka version {__version__}')
#   exit()
# if args.command == 'config':
#   console.print(services.get_config())
#   exit()
# if args.command == 'init':
#   services.ServiceCommandHander(home_dir, None, None).execute(
#     command, None, None
#   )

# file_handler = logging.FileHandler(filename=f'{home_dir}/.terka/terka.log')
# stdout_handler = logging.StreamHandler(stream=sys.stdout)
# log_handlers = [file_handler, stdout_handler]
# logging.basicConfig(
#   format='[%(asctime)s][%(name)s][%(levelname)s] %(message)s',
#   handlers=log_handlers,
#   level=args.loglevel.upper(),
#   datefmt='%Y-%m-%d %H:%M:%S',
# )
# logger = logging.getLogger(__name__)

# config = load_config(home_dir)
# task_id = config.get('task_id')
# project_name = config.get('project_name')
# if task_id or project_name:
#   focus_type = 'task' if task_id else 'project'
#   logger.warning('Using terka in focus mode')
#   logger.warning(f'Current focus is {focus_type}: {task_id or project_name}')

# task_dict = format_task_dict(config, args, kwargs)
# logger.debug(task_dict)

# service_command_handler = services.ServiceCommandHander(
#   home_dir, config, console
# )
# service_command_handler.execute(command, entity, task_dict)

# bus = bootstrap.bootstrap(
#   start_orm=True, uow=unit_of_work.SqlAlchemyUnitOfWork(DB_URL), config=config
# )
# queue = []
# queue.append({'command': command, 'entity': entity, 'task_dict': task_dict})
# while queue:
#   cmd_dict = queue.pop()
#   try:
#     handlers.CommandHandler(bus).execute(**cmd_dict)
#   except exceptions.TerkaRefreshException:
#     queue.append(cmd_dict)


if __name__ == '__main__':
  typer_app()
