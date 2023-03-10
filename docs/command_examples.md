# terka commands and entities

## terka entities

* tasks
* projects
* users

## terka commands
* create
* show
* list
* update
* comment
* edit
* done
* delete
* tag
* collaborate

> When calling commands and entities you can use their first letters.
> I.e. if you want to create new task you can call `terka cre ta` or even `terka c t`.
To the typical command looks like this

```
terka <command> <entity> [options]
```

### Example commands

#### `create`

1. Create new task with a name "New task"

```
terka create tasks -n "New task"
```

2. Create new task with a name "New task" and assign it to a project "New project" with due date in 7 days

```
terka create tasks -n "New task" -p "New project" -d +7
```


#### `show`

1. Show task info for task with id 123

```
terka show tasks 123
```

2. Show project info for a project 8 (include project tasks)

```
terka show projects 8
```

#### `list`

1. List all projects with at least 1 active task

```
terka list projects
```

2. List all tasks
```
terka list tasks
```

`list` commands can be used with the multiple terka options (listed below).

3. List all tasks from project "My project" with TODO status

```
terka list tasks -p "My project" -s T
```

`list` commands support negation, i.e. to list all tasks from project "My project that are not in BACKLOG status you can run

```
terka list tasks -p "My project" -s NOT:BACKLOG
```

#### `update`

1. Update  status for a task 123 to "REVIEW" and set due day today

```
terka update tasks 123 -s R -d today
```

#### `comment`

1. Create a commentary for a task 123

```
terka comment task 123 -t "New commentary for a task"
```

2. Create a commentary for a task 1

```
terka comment project 1 -t "New commentary for a project"
```
#### `edit`

`edit` command allows you to change either name (`--name` CLI flag) or description (`--description` CLI flag) of the task in an editor of your choice (Vim by default)

1. Edit name of the task 123
```
terka edit tasks 123 --name
```

#### `done`

`done` commands is simple - it's just updates the status of the task to done state in a convenient manner.

```
terka done tasks 123
# is equivalent to
# terka update tasks 123 -s d
```

#### `delete`

`delete` updates the status of the task to `DELETED` state in a convenient manner.

```
terka delete tasks 123
# is equivalent to
# terka update tasks 123 -s DELETED
```

#### `tag`

`tag` assigns tag to a task or a project

```
terka tag tasks 123 -t "My tag"
terka tag project 1 -t "My tag"
```

#### `collaborate`

`collaborate` assigns collaborator to a task or a project

```
terka collaborate tasks 123 -n "user_name"
terka collaborate projects 1 -n "user_name"
```

## terka options
Options depend on a particular entity but there are some common one
* `--n|--name` - name of the entity
* `--desc|--description` - description of an entity
* `-s|--status` - status of an entity (can be one of "BACKLOG","TODO","IN_PROGRESS", "REVIEW", "DONE", "DELETED"). By default the status is BACKLOG.
* for status we can use short names - b for BACKLOG, t for TODO, i for IN_PROGRESS, r for REVIEW, d for DONE, and x for DELETED
 * `--priority` - priority of the task (can be one of "LOW", "NORMAL", "HIGH", "URGENT"). By default the priority is NORMAL
 * `-d|--due-date` - due date (applied for tasks only). Can be specified in the following format:
 * YYYY-MM-DD (i.e. 2023-01-01)
   * +7, -7 (in 7 days, 7 days ago)
   * today - to tasks that are due today
   * None (default value) - when we want to explicitly specify that task does not have due date.

 * `-p|--project` (applied to task only) - project name or project_id for a task


 ## Utility commands

 * `log` - show the last 10 executed commands
 * `calendar` - show all the tasks with due date (order by ascending due date)
 * `focus <entity> <entity_id>` - execute all commands using specified `entity_id`.
 * `unfocus` - remove focus (`terka` is returned to normal mode).
 * `count <entity> [options]` -  count number of entities that safisty condition(s) in `[options]`.

