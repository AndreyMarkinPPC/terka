import argparse
from datetime import datetime, date
from io import StringIO
import re
import os
from pathlib import Path
from operator import attrgetter
import sys
import yaml
import logging
from pprint import pprint

import rich
from rich.console import Console
from rich.table import Table
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, clear_mappers

from terka.adapters.orm import metadata, start_mappers
from terka.adapters.repository import SqlAlchemyRepository

from terka import bootstrap
from terka.domain import commands
from terka.domain import _commands
from terka.domain.commands import CommandHandler
from terka.utils import (
    format_task_dict,
    process_command,
    update_task_dict,
    create_task_dict,
)
from terka.service_layer import exceptions, services, unit_of_work
from terka.service_layer.ui import TerkaTask, TerkaProject, TerkaSprint
from terka.utils import format_command, format_entity

HOME_DIR = os.path.expanduser("~")
DB_URL = f"sqlite:////{HOME_DIR}/.terka/tasks.db"


def init_db(home_dir):
    engine = create_engine(f"sqlite:////{home_dir}/.terka/tasks.db")
    metadata.create_all(engine)
    return engine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?")
    parser.add_argument("entity", nargs="?")
    parser.add_argument("--log", "--loglevel", dest="loglevel", default="info")
    parser.add_argument("-v", "--version", dest="version", action="store_true")
    args = parser.parse_known_args()
    args, kwargs = args
    console = Console()
    command, entity = args.command, args.entity
    if args.version:
        import pkg_resources

        version = pkg_resources.require("terka")[0].version
        print(f"terka version {version}")
        exit()
    if args.command == "config":
        console.print(services.get_config())
        exit()

    home_dir = os.path.expanduser("~")
    file_handler = logging.FileHandler(filename=f"{home_dir}/.terka/terka.log")
    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    handlers = [file_handler, stdout_handler]
    logging.basicConfig(
        format="[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
        handlers=handlers,
        level=args.loglevel.upper(),
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger(__name__)

    config = load_config(home_dir)
    task_id = config.get("task_id")
    project_name = config.get("project_name")
    if task_id or project_name:
        focus_type = "task" if task_id else "project"
        logger.warning("Using terka in focus mode")
        logger.warning(
            f"Current focus is {focus_type}: {task_id or project_name}")

    task_dict = format_task_dict(config, args, kwargs)
    logger.debug(task_dict)

    service_command_handler = services.ServiceCommandHander(
        home_dir, config, console)
    service_command_handler.execute(command, entity, task_dict)

    bus = bootstrap.bootstrap(start_orm=True,
                              uow=unit_of_work.SqlAlchemyUnitOfWork(DB_URL),
                              config=config)
    engine = init_db(home_dir)
    Session = sessionmaker(engine)
    with Session() as session:
        repo = SqlAlchemyRepository(session)
        if command == "show":
            if entity == "sprint":
                app = TerkaSprint(repo=repo,
                                  sprint_id=task_dict.get("id"),
                                  bus=bus)
                app.run()
            if entity == "project":
                app = TerkaProject(repo=repo,
                                   project_id=task_dict.get("id"),
                                   bus=bus)
                app.run()
            exit()
    _CommandHandler(bus).execute(command, entity, task_dict)


class _CommandHandler:

    def __init__(self, bus) -> None:
        self.bus = bus

    def execute(self, command: str, entity: str,
                task_dict: dict | list[dict]) -> None:
        if isinstance(task_dict, list):
            for _task_dict in task_dict:
                self.execute(command, entity, _task_dict)
        else:
            command = format_command(command)
            entity = format_entity(entity)
            _command = f"{command.capitalize()}{entity.capitalize()}"
            try:
                self.bus.handle(getattr(_commands,
                                        _command).from_kwargs(**task_dict),
                                context=task_dict)
            except AttributeError as e:
                print(e)
                raise exceptions.TerkaCommandException(
                    f"Unknown command: `terka {command} {entity}`")


def load_config(home_dir):
    try:
        with open(f"{home_dir}/.terka/config.yaml", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        raise exceptions.TerkaInitError(
            "call `terka init` to initialize terka")


if __name__ == "__main__":
    main()
