# Terka - Ter[minal] Ka[nban]
[![PyPI](https://img.shields.io/pypi/v/terka?logo=pypi&logoColor=white&style=flat-square)](https://pypi.org/project/terka)
[![Downloads](https://static.pepy.tech/badge/terka)](https://pepy.tech/project/terka)(https://pypi.org/project/terka)

`terka` (pronounced *tyorka* or *Тёрка*) is a CLI tool that helps you manage your tasks
in the terminal. Create task, assign it to a project, update it status, write
comments and many more!

## Installation

To install `terka` run the following command:

`pip install terka`

it will make `terka` command available in your shell.

## Usage

### Interactive mode

You can simply run `terka` command and this will launch the tool in an interactive
mode.

Please refer to the [list of commands](docs/command_examples.md) available in terka.
Special command `q` is used to exit interactive mode.

### Non-interactive mode

In non-interactive
`terka <command> <entity> [options]`

`terka` exposes several commands (`create`, `update`, `show`, `list`, etc) and entities (`tasks`, `projects`, `users`).
Please refer to the [list of commands](docs/command_examples.md) available in terka.
