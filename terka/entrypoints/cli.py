from __future__ import annotations

import argparse
import logging
import os
import sys

from rich.console import Console
from sqlalchemy import create_engine

from terka import bootstrap
from terka import exceptions
from terka.adapters.orm import metadata
from terka.service_layer import handlers
from terka.service_layer import services
from terka.service_layer import unit_of_work
from terka.utils import format_task_dict
from terka.utils import load_config

HOME_DIR = os.path.expanduser('~')
DB_URL = f'sqlite:////{HOME_DIR}/.terka/tasks.db'


def init_db(home_dir):
    engine = create_engine(f'sqlite:////{home_dir}/.terka/tasks.db')
    metadata.create_all(engine)
    return engine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', nargs='?')
    parser.add_argument('entity', nargs='?')
    parser.add_argument('--log', '--loglevel', dest='loglevel', default='info')
    parser.add_argument('-v', '--version', dest='version', action='store_true')
    args = parser.parse_known_args()
    args, kwargs = args
    console = Console()
    command, entity = args.command, args.entity
    home_dir = os.path.expanduser('~')
    if args.version:
        import pkg_resources

        version = pkg_resources.require('terka')[0].version
        print(f'terka version {version}')
        exit()
    if args.command == 'config':
        console.print(services.get_config())
        exit()
    if args.command == 'init':
        services.ServiceCommandHander(home_dir, None,
                                      None).execute(command, None, None)

    file_handler = logging.FileHandler(filename=f'{home_dir}/.terka/terka.log')
    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    log_handlers = [file_handler, stdout_handler]
    logging.basicConfig(
        format='[%(asctime)s][%(name)s][%(levelname)s] %(message)s',
        handlers=log_handlers,
        level=args.loglevel.upper(),
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    logger = logging.getLogger(__name__)

    config = load_config(home_dir)
    task_id = config.get('task_id')
    project_name = config.get('project_name')
    if task_id or project_name:
        focus_type = 'task' if task_id else 'project'
        logger.warning('Using terka in focus mode')
        logger.warning(
            f'Current focus is {focus_type}: {task_id or project_name}')

    task_dict = format_task_dict(config, args, kwargs)
    logger.debug(task_dict)

    service_command_handler = services.ServiceCommandHander(
        home_dir, config, console)
    service_command_handler.execute(command, entity, task_dict)

    bus = bootstrap.bootstrap(start_orm=True,
                              uow=unit_of_work.SqlAlchemyUnitOfWork(DB_URL),
                              config=config)
    queue = []
    queue.append({
        'command': command,
        'entity': entity,
        'task_dict': task_dict
    })
    while queue:
        cmd_dict = queue.pop()
        try:
            handlers.CommandHandler(bus).execute(**cmd_dict)
        except exceptions.TerkaRefreshException:
            queue.append(cmd_dict)


if __name__ == '__main__':
    main()
