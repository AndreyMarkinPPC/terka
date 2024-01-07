# Terka - Ter[minal] Ka[nban]
[![PyPI](https://img.shields.io/pypi/v/terka?logo=pypi&logoColor=white&style=flat-square)](https://pypi.org/project/terka)
[![Downloads](https://static.pepy.tech/badge/terka)](https://pypi.org/project/terka)

`terka` (pronounced *tyorka* or *Тёрка*) is a CLI tool that helps you manage your tasks
in the terminal. Create task, assign it to a project, update it status, write
comments and many more!

Key features:
* Manage tasks within projects with CLI and TUI interface
* Support for sprints (with story points assignment and time tracker)
* Manage meta-tasks with epics and stories
* Tag tasks and specify collaborators

## Installation

To install `terka` run the following command:

`pip install terka`

It will make `terka` command available in your shell.

After `terka` is installed run `terka init` to initialize necessary DB and
config files.

## Usage

The general structure of `terka` command goes as follows:

`terka <command> <entity> [options]`

`terka` exposes several commands (`create`, `update`, `show`, `list`, etc)
and entities (`tasks`, `projects`, `users`, `sprints`, `epics`, `stories`).
Please refer to the [list of commands](docs/command_examples.md) available in terka.
