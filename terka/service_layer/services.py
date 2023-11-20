from typing import Any, Dict, Optional
import logging
import rich
from rich.console import Console
from rich.table import Table
import os
import re
import yaml

from terka.adapters.repository import AbsRepository
from terka.domain import models
# import terka.domain._commands as commands


def update_config(update_pair: Dict[str, Any]):
    config = get_config()
    config.update(update_pair)
    with open(f"{home_dir}/.terka/config.yaml", "w") as f:
        yaml.dump(config, f)


def get_config():
    home_dir = os.path.expanduser('~')
    with open(f"{home_dir}/.terka/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def lookup_project_id(project_name: str, repo: AbsRepository) -> int:
    projects = project_name.split(",")
    if project_name.startswith("NOT"):
        projects = [
            f"NOT:{project}"
            for project in project_name.replace("NOT:", "").split(",")
        ]
        negate = True
    else:
        projects = project_name.split(",")
        negate = False
    returned_projects = []
    returned_projects_set = set()
    for project_name in projects:
        if not (project := repo.list(models.project.Project, project_name)):
            print(
                f"Creating new project: {project_name}. Do you want to continue (Y/n)?"
            )
            answer = input()
            while answer.lower() != "y":
                print("Provide a project name: ")
                project_name = input()
                print(
                    f"Creating new project: {project_name}. Do you want to continue (Y/n)?"
                )
                answer = input()
            project = models.project.Project(project_name)
            repo.add(project)
            repo.session.commit()
        if isinstance(project, list):
            project_ids = [project.id for project in project]
            if negate:
                if returned_projects_set:
                    returned_projects_set = returned_projects_set.intersection(
                        set(project_ids))
                else:
                    returned_projects_set = returned_projects_set.union(
                        set(project_ids))

            else:
                returned_projects.extend(project_ids)
        else:
            returned_projects.append(project.id)
    if returned_projects_set:
        return list(returned_projects_set)
    if len(returned_projects) == 1:
        return returned_projects[0]
    return returned_projects


def lookup_user_id(user_name: str, repo: AbsRepository) -> int | None:
    if user := repo.get(models.user.User, user_name):
        return user.id
    return None


def lookup_user_name(user_id: str, repo: AbsRepository) -> str | None:
    if user := repo.get_by_id(models.user.User, user_id):
        return user.name
    return None


def lookup_project_name(project_id: int, repo: AbsRepository) -> str | None:
    if project := repo.get_by_id(models.project.Project, project_id):
        return project.name
    return None


def lookup_workspace_id(workspace_name: str,
                        repo: AbsRepository) -> int | None:
    if workspace := repo.get(models.workspace.Workspace, workspace_name):
        return workspace.id
    return None


def get_workplace_by_name(
        workspace_name: str,
        repo: AbsRepository) -> models.workspace.Workspace | None:
    return repo.get(models.workspace.Workspace, workspace_name)


def get_workplace_by_id(
        workspace_id: int,
        repo: AbsRepository) -> models.workspace.Workspace | None:
    return repo.get_by_id(models.workspace.Workspace, workspace_id)


def get_project_by_name(project_name: str,
                        repo: AbsRepository) -> models.project.Project | None:
    return repo.get(models.project.Project, project_name)


def get_project_by_id(project_id: int,
                      repo: AbsRepository) -> models.project.Project | None:
    return repo.get_by_id(models.project.Project, project_id)


# class CommandHander:

#     def __init__(self, home_dir, config, console=Console()):
#         self.home_dir = home_dir
#         self.config = config
#         self.console =  console

#     def execute(self, command: commands.Command, entity, task_dict):
#         # TODO: create registry of commands
#         handler = commands_registry[command]
#         handler.handle(entity, task_dict)


class ServiceCommandHander:

    def __init__(self, home_dir, config, console=Console()):
        self.home_dir = home_dir
        self.config = config
        self.console = console

    def execute(self, command, entity, task_dict):
        is_service_command = True
        if command == "init":
            self.init_terka()
        elif command == "focus":
            self.focus(entity, task_dict)
        elif command == "unfocus":
            self.unfocus()
        elif command == "switch" and entity == "workspace":
            self.switch(task_dict.get("id"))
        elif command == "set" and entity == "workspace":
            self.set(task_dict.get("id"))
        elif command == "log":
            self.log(task_dict)
        else:
            is_service_command = False
        if is_service_command:
            exit()

    def init_terka(self,
                   terka_folder: str = ".terka",
                   default_user: str = "admin",
                   default_config: str = "config.yaml") -> None:
        path = os.path.join(self.home_dir, terka_folder)
        if not os.path.exists(path):
            answer = input(
                f"Do you want to init terka in this directory {path}? [Y/n]")
            if "y" in answer.lower():
                Path(path).mkdir(parents=True, exist_ok=True)
                with open(os.path.join(path, "config.yaml"), "w") as f:
                    yaml.dump({"user": default_user}, f)
            elif "n" in answer.lower():
                path = input("Specify full path to the terka directory: ")
                os.mkdirs(path)
            else:
                exit()
        elif not os.path.exists(os.path.join(path, default_config)):
            answer = input(
                f"Config.yaml not found in {path}, Create it? [Y/n]")
            if "y" in answer.lower():
                with open(os.path.join(path, default_config), "w") as f:
                    yaml.dump({"user": default_user}, f)
            else:
                exit()
        else:
            print("Terka directory already exist.")

    def focus(self, entity_type, kwargs):
        if entity_type == "tasks":
            self.config["task_id"] = kwargs["id"]
            if "project_name" in self.config.keys():
                del self.config["project_name"]
        if entity_type == "projects":
            self.config["project_name"] = kwargs["id"]
            if "task_id" in self.config.keys():
                del self.config["task_id"]
        with open(f"{self.home_dir}/.terka/config.yaml", "w",
                  encoding="utf-8") as f:
            yaml.dump(self.config, f)
        logging.info("<focus> %s: %s", entity_type, "")

    def unfocus(self):
        if "task_id" in self.config.keys():
            del self.config["task_id"]
        if "project_name" in self.config.keys():
            del self.config["project_name"]
        with open(f"{self.home_dir}/.terka/config.yaml", "w",
                  encoding="utf-8") as f:
            yaml.dump(self.config, f)
        loging.info("<unfocus> %s: %s", "", "")

    def log(self, kwargs):
        table = Table(box=rich.box.SIMPLE)
        with open(f"{self.home_dir}/.terka/terka.log", "r") as f:
            head = f.readlines()
        for column in ("date", "source", "level", "message"):
            table.add_column(column)
        num_log_entries = int(kwargs.get("num_log_entries", 10))
        tail = head[-num_log_entries:]
        for row in tail[::-1]:
            info, message = row.split("] ")
            date, source, level = info.split("][")
            table.add_row(re.sub("\[", "", date), source, level, message)
        self.console.print(table)

    def switch(self, workspace: str):
        if not self.config.get("workspace"):
            self.config["workspace"] = "Default"  # Default workspace
        else:
            self.config["workspace"] = workspace
        with open(f"{self.home_dir}/.terka/config.yaml", "w",
                  encoding="utf-8") as f:
            yaml.dump(self.config, f)
        logging.info("switched to workspace: %d", workspace)

    def set_workspace(self, workspace: str):
        self.config["workspace"] = workspace
        with open(f"{self.home_dir}/.terka/config.yaml", "w",
                  encoding="utf-8") as f:
            yaml.dump(self.config, f)
        logging.info("set workspace: %d", workspace)
