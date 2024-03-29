from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import rich
import yaml
from rich.console import Console
from rich.table import Table

from terka.adapters.repository import AbsRepository
from terka.domain import entities


def update_config(update_pair: dict):
    config = get_config()
    config.update(update_pair)
    with open(f'{home_dir}/.terka/config.yaml', 'w') as f:
        yaml.dump(config, f)


def get_config():
    home_dir = os.path.expanduser('~')
    with open(f'{home_dir}/.terka/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


def get_workplace_by_name(
        workspace_name: str,
        repo: AbsRepository) -> entities.workspace.Workspace | None:
    return repo.get(entities.workspace.Workspace, workspace_name)


class ServiceCommandHander:

    def __init__(self, home_dir, config, console=Console()):
        self.home_dir = home_dir
        self.config = config
        self.console = console

    def execute(self, command, entity, task_dict):
        is_service_command = True
        if command == 'init':
            self.init_terka()
        elif command == 'switch' and entity == 'workspace':
            self.switch(task_dict.get('id'))
        elif command == 'set' and entity == 'workspace':
            self.set(task_dict.get('id'))
        elif command == 'log':
            self.log(task_dict)
        else:
            is_service_command = False
        if is_service_command:
            exit()

    def init_terka(self,
                   terka_folder: str = '.terka',
                   default_user: str = 'admin',
                   default_config: str = 'config.yaml') -> None:
        path = os.path.join(self.home_dir, terka_folder)
        if not os.path.exists(path):
            answer = input(
                f'Do you want to init terka in this directory {path}? [Y/n]')
            if 'y' in answer.lower():
                Path(path).mkdir(parents=True, exist_ok=True)
                with open(os.path.join(path, 'config.yaml'), 'w') as f:
                    yaml.dump({'user': default_user}, f)
            elif 'n' in answer.lower():
                path = input('Specify full path to the terka directory: ')
                os.mkdirs(path)
            else:
                exit()
        elif not os.path.exists(os.path.join(path, default_config)):
            answer = input(
                f'Config.yaml not found in {path}, Create it? [Y/n]')
            if 'y' in answer.lower():
                with open(os.path.join(path, default_config), 'w') as f:
                    yaml.dump({'user': default_user}, f)
            else:
                exit()
        else:
            print('Terka directory already exist.')

    def log(self, kwargs):
        table = Table(box=rich.box.SIMPLE)
        with open(f'{self.home_dir}/.terka/terka.log', 'r') as f:
            head = f.readlines()
        for column in ('date', 'source', 'level', 'message'):
            table.add_column(column)
        num_log_entries = int(kwargs.get('num_log_entries', 10))
        tail = head[-num_log_entries:]
        for row in tail[::-1]:
            info, message = row.split('] ')
            date, source, level = info.split('][')
            table.add_row(re.sub('\[', '', date), source, level, message)
        self.console.print(table)

    def switch(self, workspace: str):
        if not self.config.get('workspace'):
            self.config['workspace'] = 'Default'  # Default workspace
        else:
            self.config['workspace'] = workspace
        with open(f'{self.home_dir}/.terka/config.yaml', 'w',
                  encoding='utf-8') as f:
            yaml.dump(self.config, f)
        logging.info('switched to workspace: %d', workspace)

    def set_workspace(self, workspace: str):
        self.config['workspace'] = workspace
        with open(f'{self.home_dir}/.terka/config.yaml', 'w',
                  encoding='utf-8') as f:
            yaml.dump(self.config, f)
        logging.info('set workspace: %d', workspace)
