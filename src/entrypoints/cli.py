import argparse
from datetime import datetime, date
from io import StringIO
import re
import os
from operator import attrgetter
import sys
import yaml
import logging

import rich
from rich.console import Console
from rich.table import Table
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, clear_mappers

from src.adapters.orm import metadata, start_mappers
from src.adapters.repository import SqlAlchemyRepository

from src.domain.commands import CommandHandler
from src.utils import format_task_dict, process_command, update_task_dict


def init_db(home_dir):
    engine = create_engine(f"sqlite:////{home_dir}/.terka/tasks.db")
    metadata.create_all(engine)
    return engine


class TerkaInitError(Exception): ...


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?")
    parser.add_argument("entity", nargs="?")
    parser.add_argument("--log",
                        "--loglevel",
                        dest="loglevel",
                        default="info")
    parser.add_argument("-v",
                        "--version",
                        dest="version",
                        action="store_true")
    args = parser.parse_known_args()
    args, kwargs = args
    if args.version:
        import pkg_resources
        version = pkg_resources.require("terka")[0].version
        print(f"terka version {version}")
        exit()
    home_dir = os.path.expanduser('~')
    logger = logging.getLogger(__name__)
    console = Console()

    engine = init_db(home_dir)
    start_mappers()
    Session = sessionmaker(engine)

    with Session() as session:
        file_handler = logging.FileHandler(filename=f"{home_dir}/.terka/terka.log")
        file_handler.setLevel(logging.DEBUG)
        stdout_handler = logging.StreamHandler(stream=sys.stdout)
        stdout_handler.setLevel(logging.WARNING)
        handlers = [file_handler, stdout_handler]
        logging.basicConfig(
            format="[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
            handlers=handlers,
            level=args.loglevel.upper(),
            datefmt="%Y-%m-%d %H:%M:%S")

        repo = SqlAlchemyRepository(session)
        command_handler = CommandHandler(repo)
        if args.command == "init":
            command_handler.execute("init")

        try:
            with open(f"{home_dir}/.terka/config.yaml", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            raise TerkaInitError("call `terka init` to initialize terka")

        task_id = config.get("task_id")
        project_name = config.get("project_name")
        if task_id or project_name:
            focus_type = "task" if task_id else "project"
            logger.warning("Using terka in focus mode")
            logger.warning(f"Current focus is {focus_type}: {task_id or project_name}")

        task_dict = format_task_dict(config, args, kwargs)
        task_dict = update_task_dict(task_dict, repo)
        logger.debug(task_dict)

        command, entity = args.command, args.entity
        is_interactive = False
        if not command and not entity:
            is_interactive = True
            console.print(f"[green]>>> Running terka in an interactive mode[/green]")
            command = input("enter command: ")
            command, entity, task_dict = process_command(command, config, repo)
        try:
            command_handler.execute(command, entity, task_dict)
        except ValueError as e:
            console.print(f"[red]{e}[/red]")

        while is_interactive:
            console.print(f"[green]>>> Running terka in an interactive mode[/green]")
            command = input("enter command: ")
            command, entity, task_dict = process_command(command, config, repo)
            if command[0] == "q":
                exit()
            command_handler.execute(command, entity, task_dict)


if __name__ == "__main__":
    main()
