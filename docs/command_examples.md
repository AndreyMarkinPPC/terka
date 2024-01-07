# terka commands and entities

## terka entities

* `task`
* `project`
* `user`
* `sprint`
* `epic`
* `story`
* `workspace`
* `note`

## terka commands
* `create`
* `show`
* `list`
* `update`
* `complete`
* `delete`
* `comment`
* `tag`
* `collaborate`
* `add`
* `start` (available only for `sprint`)
* `track` (available only for `task`)
* `sync` (available only for `project`)

To the typical command looks like this

```
terka <command> <entity> [options]
```

### Example commands

#### `create`

1. Create new task with a name "New task"

```
terka create task -n "New task"
```
> When launched without arguments `terka create task` will launch Vim to enter
> necessary task details

2. Create new task with a name "New task" and assign it to a project "New project" with due date in 7 days

```
terka create task -n "New task" -p "New project" -d +7
```

3. Create new sprint with goal "Sample sprint" and plan it to start "2023-04-01" and end "2023-04-14"

```
terka create sprint --goal "Sample sprint" --start-date 2023-04-01 --end-date 2023-04-14
```


#### `show`

`show` launches a terminal UI when you can interact with the task


1. Show project info for project *my-project*

```
terka show project my-project
```

2. Show sprint info for a sprint 1

```
terka show sprint 1
```

#### `list`

1. List all projects with at least 1 active task

```
terka list projects
```
> Add `--all` flag to show all projects.

2. List all tasks

```
terka list tasks
```
> Add `--all` flag to show all tasks.

`list` commands can be used with the multiple terka options (listed below).

3. List all tasks with TODO status

```
terka list tasks -s T
```
> Show all projects including deleted, completed on on hold with `--all` flag.

`list` commands support negation, i.e. to list all tasks with status other than BACKLOG and URGENT priority you can run:

```
terka list tasks -s NOT:BACKLOG --priority URGENT
```

##### Sorting with `list`

`list` supports sorting by visible columns

1. Sort projects by `open_tasks`:

```
terka list projects --sort open_tasks
```

1. Sort projects by `overdue` tasks:

```
terka list projects --sort overdue
```

#### `update`

1. Update  status for a task 123 to "REVIEW" and set due day today

```
terka update task 123 -s R -d today
```
> running `terka update task 123` will launch Vim where you can make updates in bulk

2. Update goal for sprint 1 to "New Goal"

```
terka update sprint 1 --goal "New goal"
```
> running `terka update sprint 1` will launch Vim where you can make updates in bulk


#### `comment`

1. Create a commentary for a task 123

```
terka comment task 123 -t "New commentary for a task"
```

2. Create a commentary for a task 1

```
terka comment project 1 -t "New commentary for a project"
```

#### `complete`

`complete` commands is simple - it's just updates the status of the task to done state in a convenient manner.

```
terka complete task 123
# is equivalent to
# terka update task 123 -s D
```

#### `delete`

`delete` updates the status of the task to `DELETED` state in a convenient manner.

```
terka delete task 123
# is equivalent to
# terka update tasks 123 -s DELETED
```

#### `tag`

`tag` assigns tag to a task or a project

```
terka tag task 123 -t "My tag"
terka tag project 1 -t "My tag"
```

#### `collaborate`

`collaborate` assigns collaborator to a task or a project

```
terka collaborate task 123 -n "user_name"
terka collaborate project 1 -n "user_name"
```

#### `add`

`add` command allows you to work within sprint:

1. Add tasks 1, 2, and 3 to sprint 1

```
terka add task 1,2,3 --to-sprint 1
```

2. Add one story point to task 1

```
terka add task 1 --story-points 1
```

#### `start`

`start` sets status of a sprint to `ACTIVE`, changes all tasks with status `BACKLOG` to `TODO`
and set due_date of each task to sprint's end_date (unless the task's due_date is earlier than
sprint's end_date).

1. Start sprint 1
```
terka start sprint 1
```
#### `track`

Tracks time spend on the task; can be in hours or minutes

1. Track 10 minutes spent on task 1

```
terka track task 1 -M 10
```
1. Track 1 hour spent on task 1
```
terka track task 1 -H 1
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
