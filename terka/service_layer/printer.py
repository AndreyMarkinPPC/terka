from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from operator import attrgetter
import inspect
from copy import deepcopy

from collections import defaultdict
import itertools
from datetime import datetime, date, timedelta
import plotext as plt
import rich
import pandas as pd
import numpy as np
import matplotlib.pyplot
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from statistics import mean, median

from terka.service_layer import services, views, formatter
from terka.service_layer.ui import TerkaTask, TerkaProject, TerkaSprint


@dataclass
class PrintOptions:
    show_tasks: bool = True
    show_history: bool = False
    show_commentaries: bool = False
    show_completed: bool = False
    show_epics: bool = True
    show_stories: bool = True
    show_notes: bool = True
    show_viz: bool = False
    columns: str = ""
    expand_table: bool = True


class Printer:

    def __init__(self, repo, box=rich.box.SIMPLE, config = None) -> None:
        self.console = Console()
        self.box = box
        self.repo = repo
        self.config = config

    def print_new_object(self, obj, project=None):
        table = Table(box=self.box)
        attributes = self._get_attributes(obj)
        for column, value in attributes:
            if value:
                table.add_column(column)
        table.add_row(*list(zip(*attributes))[1])
        if table.row_count:
            self.console.print(f"Added new {obj.__class__.__name__}")
            self.console.print(table)

    def print_history(self, entities):
        table = Table(box=self.box)
        print("History:")
        for column in ("date", "type", "old_value", "new_value"):
            table.add_column(column)
        for event in entities:
            table.add_row(event.date.strftime("%Y-%m-%d %H:%M"),
                          event.type.name, event.old_value, event.new_value)
        if table.row_count:
            self.console.print(table)

    def print_commentaries(self, entities):
        table = Table(box=self.box)
        print("Comments:")
        for column in ("date", "text"):
            table.add_column(column)
        entities.sort(key=lambda c: c.date, reverse=False)
        for event in entities:
            table.add_row(event.date.strftime("%Y-%m-%d %H:%M"), event.text)
        if table.row_count:
            self.console.print(table)

    def print_entity(self,
                     task,
                     entity_type,
                     entities,
                     repo,
                     print_options: PrintOptions = PrintOptions(),
                     kwargs: Optional[Dict[str, Any]] = None):
        if entity_type == "sprints":
            if entities:
                self.print_sprint(entities, repo, print_options, kwargs)
            else:
                exit(f"No sprint with id '{task}' found!")
        if entity_type in ("epics", "stories"):
            if entities:
                self.print_composite(entities, repo, print_options,
                                     entity_type, kwargs)
            else:
                exit(f"No {entity_type} with id '{task}' found!")
        if entity_type == "projects":
            if entities:
                self.print_project(entities, print_options, kwargs)
            else:
                exit(f"No project '{task}' found!")
        if entity_type == "tasks":
            if entities:
                self.print_task(entities, repo, print_options)
            else:
                print(f"No task with id '{task}' found!")
        if entity_type == "notes":
            if entities:
                self.print_note(entities=entities,
                                association="task",
                                markdown=True)
            else:
                print(f"No notes with id '{task}' found!")

    def print_entities(self,
                       entities,
                       type,
                       repo,
                       custom_sort,
                       print_options=PrintOptions()):
        if type == "projects":
            entities.sort(key=self._sort_open_tasks, reverse=True)
            self.print_project(entities, print_options)
        elif type == "tasks":
            if custom_sort and custom_sort not in ("status", "priority"):
                entities.sort(key=lambda c: getattr(c, custom_sort),
                              reverse=False)
            elif custom_sort == "status":
                entities.sort(key=lambda c: c.status.value, reverse=True)
            elif custom_sort == "priority":
                entities.sort(key=lambda c: c.priority.value, reverse=True)
            else:
                entities.sort(key=lambda c: (c.status.value, c.priority.value),
                              reverse=True)
            self.print_task(entities=entities,
                            repo=repo,
                            print_options=print_options,
                            custom_sort=custom_sort)
        elif type == "tags":
            self.print_tag(entities=entities)
        elif type == "users":
            self.print_user(entities=entities)
        elif type == "sprints":
            self.print_sprint(entities=entities,
                              repo=repo,
                              print_options=print_options)
        elif type in ("epics", "stories"):
            if custom_sort == "project":
                entities.sort(key=lambda c: c.project, reverse=True)
            elif custom_sort == "tasks":
                entities.sort(key=lambda c: len(c.tasks), reverse=True)

            self.print_composite(entities=entities,
                                 repo=repo,
                                 print_options=print_options,
                                 composite_type=type)
        elif type == "notes":
            self.print_note(entities=entities, association="task")
        else:
            self.print_default_entity(self, entities)

    def print_user(self, entities):
        table = Table(box=self.box)
        for column in ("id", "name"):
            table.add_column(column)
        seen_users = set()
        for entity in entities:
            if entity.name not in seen_users:
                table.add_row(f"[red]{entity.id}[/red]", entity.name)
                seen_users.add(entity.name)
        if table.row_count:
            self.console.print(table)

    def print_tag(self, entities):
        table = Table(box=self.box)
        for column in ("id", "text"):
            table.add_column(column)
        seen_tags = set()
        for entity in entities:
            if entity.text not in seen_tags:
                table.add_row(f"[red]{entity.id}[/red]", entity.text)
                seen_tags.add(entity.text)
        if table.row_count:
            self.console.print(table)

    def print_note(self, entities, association: str, markdown=False) -> None:

        association = next(iter(entities)).__class__.__name__.replace(
            "Note", "").lower()
        table = Table(box=self.box, title="NOTES")
        for column in ("id", "name", "association"):
            table.add_column(column)
        for entity in entities:
            if markdown:
                if isinstance(entity.text, (bytes, bytearray)):
                    text = entity.text.decode("utf-8")
                else:
                    text = entity.text
                self.console.print(Markdown(text), width=80)
                exit()
            else:
                table.add_row(f"[red]{str(entity.id)}[/red]", entity.name,
                              str(getattr(entity, association)))
        if table.row_count:
            self.console.print(table)

    def print_default_entity(self, entities):
        table = Table(box=self.box)
        for column in ("id", "date", "text"):
            table.add_column(column)
        for entity in entities:
            table.add_row(f"[red]{entity.id}[/red]",
                          entity.date.strftime("%Y-%m-%d %H:%M"), entity.text)
        if table.row_count:
            self.console.print(table)

    def print_composite(self,
                        entities,
                        repo,
                        print_options,
                        composite_type,
                        kwargs=None):
        table = Table(box=self.box,
                      title=composite_type.upper(),
                      expand=print_options.expand_table)
        non_active_entities = Table(box=self.box,
                                    title=f"INACTIVE {composite_type.upper()}",
                                    expand=print_options.expand_table)
        default_columns = ("id", "name", "description", "status", "project",
                           "tasks")
        if print_options.columns:
            printable_columns = print_options.columns.split(",")
        else:
            printable_columns = default_columns
        for column in printable_columns:
            table.add_column(column, style="bold")
        for column in printable_columns:
            non_active_entities.add_column(column, style="bold")
        for i, entity in enumerate(entities):
            project = services.lookup_project_name(
                entity.project, repo)
            tasks = []
            completed_tasks = []
            for entity_task in entity.tasks:
                task = entity_task.tasks
                if task.status.name not in ("DONE", "DELETED"):
                    tasks.append(task)
                else:
                    completed_tasks.append(task)
            printable_row = {
                "id": f"{entity.id}",
                "name": str(entity.name),
                "description": entity.description,
                "status": entity.status.name,
                "project": project,
                "tasks": str(len(tasks))
            }
            printable_elements = [
                value for key, value in printable_row.items()
                if key in printable_columns
            ]
            table.add_row(*printable_elements)
            if entity.status.name == "COMPLETED":
                non_active_entities.add_row(*printable_elements)
                continue
            if len(completed_tasks) == len(entity.tasks):
                non_active_entities.add_row(*printable_elements)
                continue
            # if i == 0 or tasks or print_options.show_completed:
            # TODO: Uncomment
            # table.add_row(*printable_elements)
        if table.row_count:
            self.console.print(table)
        if non_active_entities.row_count and print_options.show_completed:
            self.console.print(non_active_entities)
        if print_options.show_tasks and tasks:
            self.print_task(entities=tasks,
                            repo=repo,
                            print_options=print_options,
                            show_window=False,
                            view_level=composite_type[:-1],
                            kwargs=kwargs)
        if print_options.show_tasks and completed_tasks:
            self.print_task(entities=completed_tasks,
                            repo=repo,
                            print_options=print_options,
                            show_window=False,
                            kwargs=kwargs)
        if i == 0 and print_options.show_commentaries and (
                commentaries := entity.commentaries):
            self.print_commentaries(commentaries)
        if viz := print_options.show_viz:
            if "time" in viz:
                time_entries = entity.daily_time_entries_hours()
                self._print_time_utilization(time_entries)

    def print_sprint(self, entities, repo, print_options, kwargs=None):
        table = Table(box=rich.box.SQUARE_DOUBLE_HEAD,
                      expand=print_options.expand_table)
        columns = ("id", "start_date", "end_date", "goal", "status",
                   "open tasks", "pct_completed", "velocity", "collaborators",
                   "time_spent", "utilization")
        if print_options.columns:
            printable_columns = print_options.columns.split(",")
        else:
            printable_columns = columns

        for column in printable_columns:
            table.add_column(column)
        for i, entity in enumerate(entities):
            story_points = []
            tasks = []
            collaborators = []
            collaborators_dict = defaultdict(int)
            for sprint_task in entity.tasks:
                story_points.append(sprint_task.story_points)
                task = sprint_task.tasks
                tasks.append(task)
                if task_collaborators := task.collaborators:
                    for collaborator in task.collaborators:
                        collaborators_dict[collaborator.users.
                                           name] += sprint_task.story_points
                else:
                    collaborators_dict["Unknown"] += sprint_task.story_points

            for user, story_point in sorted(collaborators_dict.items(),
                                            key=lambda x: x[1],
                                            reverse=True):
                collaborators.append(f"{user} ({round(story_point, 2)})")

            collaborators_string = ", ".join(collaborators)
            open_tasks = [
                task for task in tasks
                if task.status.name not in ("DONE", "DELETED")
            ]
            if (total_tasks := len(tasks)) > 0:
                pct_completed = round(
                    (len(tasks) - len(open_tasks)) / len(tasks) * 100)
            else:
                pct_completed = 0
            printable_row = {
                "id": str(entity.id),
                "start_date": str(entity.start_date),
                "end_date": str(entity.end_date),
                "goal": entity.goal,
                "status": entity.status.name,
                "open tasks": f"{len(entity.open_tasks)} ({len(entity.tasks)})",
                "pct_completed": f"{round(entity.pct_completed * 100, 2)}%",
                "velocity": str(round(entity.velocity, 2)),
                "collaborators": collaborators_string,
                "time_spent": str(formatter.Formatter.format_time_spent(entity.total_time_spent)),
                "utilization": f"{round(entity.utilization * 100)}%"
            }
            printable_elements = [
                value for key, value in printable_row.items()
                if key in printable_columns
            ]
            table.add_row(*printable_elements)
        if table.row_count:
            self.console.print(table)

        if print_options.show_tasks:
            task_print_options = deepcopy(print_options)
            task_print_options.show_commentaries = False
            task_print_options.show_viz = False
            self.print_task(entities=tasks,
                            repo=repo,
                            print_options=task_print_options,
                            story_points=story_points,
                            kwargs=kwargs,
                            show_window=False,
                            view_level="sprint")
        if i == 0 and print_options.show_commentaries and (
                commentaries := entities[0].commentaries):
            self.print_commentaries(commentaries)
        if viz := print_options.show_viz:
            if "cfd" in viz:
                dates = [
                    date.strftime("%Y-%m-%d") for date in pd.date_range(
                        entity.start_date,
                        entity.end_date).to_pydatetime().tolist()
                ]
                status_changes = views.status_changes(repo.session, 2)
                placeholders = pd.DataFrame(data=list(
                    itertools.product([task.id for task in tasks], dates)),
                                            columns=["task", "date"])
                history = self._restore_status_history(placeholders,
                                                       status_changes)
                # TODO: aggreggate history ty date and number of tasks within the state
                # plt.date_form('Y-m-d')
                # y = range(1, 10)
                # y2 = range(2, 20, 2)
                # y3 = range(3, 30, 3)
                # y4 = range(4, 40, 4)
                # y5 = range(5, 50, 5)
                # plt.plot(dates, y2,  fillx=True, color="green", label="TODO")
                # plt.plot(dates, y3,  fillx=False, color="blue", label="IN_PROGRESS")
                # plt.plot(dates, y4,  fillx=False, color="red", label="REVIEW")
                # plt.plot(dates, y5,  fillx=False, color="black", label="DONE")
                # plt.plot_size(50, 15)
                # plt.show()
            if "time" in viz:
                time_entries = entity.daily_time_entries_hours()
                self._print_time_utilization(time_entries)
        if len(entities) == 1:
            app = TerkaSprint(entity=entities[0], repo=self.repo, config=self.config)
            app.run()


    def print_project(self, entities, print_options, kwargs=None):
        table = Table(box=rich.box.SQUARE_DOUBLE_HEAD,
                      expand=print_options.expand_table)
        non_active_projects = Table(box=rich.box.SQUARE_DOUBLE_HEAD,
                                    expand=print_options.expand_table)
        default_columns = ("id", "name", "description", "status", "open_tasks",
                           "overdue", "stale", "backlog", "todo",
                           "in_progress", "review", "done", "median_task_age",
                           "time_spent")

        if print_options.columns:
            printable_columns = print_options.columns.split(",")
        else:
            printable_columns = default_columns
        for column in printable_columns:
            table.add_column(column)
        for column in printable_columns:
            if column in ("id", "name", "description", "status", "open_tasks"):
                non_active_projects.add_column(column)
        for entity in entities:
            # if entity.status.name != "ACTIVE":
            #     continue
            open_tasks = self._sort_open_tasks(entity)
            if open_tasks > 0 and entity.status.name == "ACTIVE":
                overdue_tasks = [
                    task for task in entity.tasks
                    if task.due_date and task.due_date <= datetime.now().date(
                    ) and task.status.name not in ("DELETED", "DONE")
                ]
                stale_tasks = []
                for task in entity.tasks:
                    if task.is_stale:
                        stale_tasks.append(task)
                stale_tasks = list(set(stale_tasks))
                median_task_age = round(
                    median([(datetime.now() - task.creation_date).days
                            for task in entity.tasks
                            if task.status.name not in ("DELETED", "DONE")]))
                backlog = self._count_task_status(entity.tasks, "BACKLOG")
                todo = self._count_task_status(entity.tasks, "TODO")
                in_progress = self._count_task_status(entity.tasks,
                                                      "IN_PROGRESS")
                review = self._count_task_status(entity.tasks, "REVIEW")
                done = self._count_task_status(entity.tasks, "DONE")

                if overdue_tasks:
                    entity_id = f"[red]{entity.id}[/red]"
                else:
                    entity_id = f"[green]{entity.id}[/green]"
                printable_row = {
                    "id":
                    f"{entity.id}",
                    "name":
                    str(entity.name),
                    "description":
                    entity.description,
                    "status":
                    entity.status.name,
                    "open_tasks":
                    str(open_tasks),
                    "overdue":
                    str(len(overdue_tasks)),
                    "stale":
                    str(len(stale_tasks)),
                    "backlog":
                    str(backlog),
                    "todo":
                    str(todo),
                    "in_progress":
                    str(in_progress),
                    "review":
                    str(review),
                    "done":
                    str(done),
                    "median_task_age":
                    str(median_task_age),
                    "time_spent":
                    formatter.Formatter.format_time_spent(entity.total_time_spent),
                }
                printable_elements = [
                    value for key, value in printable_row.items()
                    if key in printable_columns
                ]
                table.add_row(*printable_elements)
            else:
                printable_row = {
                    "id": f"{entity.id}",
                    "name": str(entity.name),
                    "description": entity.description,
                    "status": entity.status.name,
                    "open_tasks": str(open_tasks),
                }
                printable_elements = [
                    value for key, value in printable_row.items()
                    if key in printable_columns
                ]
                non_active_projects.add_row(*printable_elements)

        if table.row_count:
            self.console.print(table)
        if non_active_projects.row_count:
            self.console.print("[green]Inactive projects[/green]")
            self.console.print(non_active_projects)
        non_task_view_options = deepcopy(print_options)
        non_task_view_options.show_tasks = False
        non_task_view_options.show_viz = False
        if print_options.show_epics and (epics := entity.epics):
            self.console.print("")
            self.print_composite(epics, self.repo, non_task_view_options,
                                 "epics", kwargs)
        if print_options.show_stories and (stories := entity.stories):
            self.console.print("")
            self.print_composite(stories, self.repo, non_task_view_options,
                                 "stories", kwargs)
        if print_options.show_tasks and (tasks := entity.tasks):
            task_print_options = deepcopy(print_options)
            task_print_options.show_commentaries = False
            task_print_options.show_viz = False
            self.console.print("")
            self.print_task(entities=tasks,
                            repo=self.repo,
                            print_options=task_print_options,
                            show_window=False,
                            kwargs=kwargs)
        if print_options.show_commentaries and (commentaries :=
                                                entity.commentaries):
            self.print_commentaries(commentaries)
        if print_options.show_history and (history := entity.history):
            self.print_history(history)
        if print_options.show_notes and (notes := entity.notes):
            self.print_note(notes, "project")
        if viz := print_options.show_viz:
            if "time" in viz:
                time_entries = entity.daily_time_entries_hours()
                self._print_time_utilization(time_entries)
        if len(entities) == 1:
            collaborators = defaultdict(int)
            for task in entities[0].tasks:
                if task_collaborators := task.collaborators:
                    for collaborator in task.collaborators:
                        name = collaborator.users.name
                        collaborators[name] = +task.total_time_spent
                else:
                    collaborators["me"] = +task.total_time_spent

            app = TerkaProject(entity=entities[0], repo=self.repo, config=self.config)
            app.run()

    def print_task(self,
                   entities,
                   repo,
                   print_options,
                   custom_sort=None,
                   show_window=True,
                   story_points=None,
                   view_level="tasks",
                   kwargs=None):
        table = Table(box=self.box, title="TASKS")
        if story_points:
            default_columns = ("id", "name", "description", "story_points",
                               "status", "priority", "project", "due_date",
                               "tags", "collaborators", "time_spent")
        else:
            default_columns = ("id", "name", "description", "status",
                               "priority", "project", "due_date", "tags",
                               "collaborators", "time_spent")
        completed_tasks_default_columns = ("id", "name", "description",
                                           "status", "priority", "project",
                                           "completed_date", "tags",
                                           "collaborators", "time_spent")
        #TODO: Add printing for only a single task
        # if (entities[0].status.name == "DONE"):
        #     console.print(f"[green]task is completed on [/green]")
        # else:
        #     active_in_days = datetime.now() - entities[0].creation_date
        #     console.print(f"[blue]task is active {active_in_days.days} days[/blue]")
        if print_options.columns:
            printable_columns = print_options.columns.split(",")
        else:
            printable_columns = default_columns
        printable_completed_tasks_colums = printable_columns
        entities = list(entities)
        if kwargs:
            custom_sort = custom_sort or kwargs.pop("sort", None)
            entities = self._get_filtered_entities(entities, kwargs)
        else:
            custom_sort = None
        # if not story_points:
        #     if custom_sort and custom_sort not in ("status", "priority"):
        #         entities.sort(key=lambda c: getattr(c, custom_sort),
        #                       reverse=False)
        #     elif custom_sort == "status":
        #         entities.sort(key=lambda c: c.status.value, reverse=True)
        #     elif custom_sort == "priority":
        #         entities.sort(key=lambda c: c.priority.value, reverse=True)
        #     else:
        #         entities.sort(key=lambda c: (c.status.value, c.priority.value),
        #                       reverse=True)
        table, completed_tasks, completed_story_points = self._print_task(
            table=table,
            entities=entities,
            default_columns=printable_columns,
            repo=repo,
            story_points=story_points,
            show_window=show_window,
            view_level=view_level,
            custom_sort=custom_sort)
        if table.row_count:
            self.console.print(table)
        if print_options.show_completed and completed_tasks:
            table = Table(box=self.box)
            table, *rest = self._print_task(
                table=table,
                entities=completed_tasks,
                default_columns=printable_completed_tasks_colums,
                repo=repo,
                story_points=completed_story_points,
                show_window=show_window,
                all_tasks=False,
                view_level=view_level,
                custom_sort=custom_sort)
            if table.row_count:
                self.console.print(f"[green]****COMPLETED TASKS*****[/green]")
                self.console.print(table)
        if viz := print_options.show_viz:
            if "time" in viz:
                time_entries = entity.daily_time_entries_hours(last_n_days=14)
                self._print_time_utilization(time_entries)

    def _get_attributes(self, obj) -> List[Tuple[str, str]]:
        import inspect
        attributes = []
        for name, value in inspect.getmembers(obj):
            if not name.startswith("_") and not inspect.ismethod(value):
                if not value:
                    continue
                elif name in ("created_by", "assignee"):
                    attributes.append(
                        (name, services.lookup_user_name(value, self.repo)))
                elif name == "project":
                    project = services.lookup_project_name(value, self.repo)
                    attributes.append((name, project))
                elif hasattr(value, "name"):
                    attributes.append((name, value.name))
                elif isinstance(value, datetime):
                    attributes.append((name, value.strftime("%Y-%m-%d %H:%M")))
                elif isinstance(value, set):
                    values = value.pop()
                    attributes.append((name, str(values)))
                else:
                    attributes.append((name, str(value)))
        return attributes

    def _sort_open_tasks(self, entities):
        return len([
            task for task in entities.tasks
            if task.status.name not in ("DONE", "DELETED")
        ])

    def _count_task_status(self, tasks, status: str) -> int:
        return len([task for task in tasks if task.status.name == status])

    def _get_filtered_entities(self, entities, kwargs):
        if kwargs:
            filtering_attributes = set(list(kwargs))
            temp_entities = []
            attributes = [
                name for name, value in inspect.getmembers(entities[0])
                if not name.startswith("_") and not inspect.ismethod(value)
            ]
            filtering_attributes = filtering_attributes.intersection(
                set(attributes))
            attribute_getter = attrgetter(*filtering_attributes)
            filtered_entities = []
            for entity in entities:
                should_add = False
                for key, value in kwargs.items():
                    if key in filtering_attributes:
                        attribute_value = getattr(entity, key)
                        if hasattr(attribute_value, "name"):
                            if attribute_value.name != value:
                                should_add = False
                                break
                            else:
                                should_add = True
                                continue
                        elif attribute_value != value:
                            should_add = False
                            break
                        else:
                            should_add = True
                            continue
                if should_add:
                    filtered_entities.append(entity)
            entities = list(filtered_entities)
        return entities

    def _print_task(self,
                    table,
                    entities,
                    default_columns,
                    repo,
                    story_points=None,
                    all_tasks=True,
                    show_window=True,
                    view_level="tasks",
                    custom_sort=None):
        if all_tasks:
            completed_tasks = []
        else:
            completed_tasks = None
            completed_story_points = None
        if not custom_sort:
            custom_sort = "status"
            reverse = True
        elif custom_sort == "priority":
            reverse = True
        else:
            reverse = False
        sorting = attrgetter(custom_sort)

        def sorting_fn(x):
            if hasattr(sorting(x), "value"):
                return sorting(x).value
            return sorting(x)

        if story_points:
            completed_story_points = []
            entities = [(entity, story_point) for entity, story_point in
                        sorted(zip(entities, story_points),
                               key=lambda x: sorting_fn(x[0]),
                               reverse=reverse)]
        else:
            entities.sort(key=lambda x: sorting_fn(x), reverse=reverse)
            completed_story_points = None
        for column in default_columns:
            table.add_column(column)
        for entity in entities:
            if story_points:
                story_point = entity[1]
                entity = entity[0]
            else:
                story_point = None
            if tags := entity.tags:
                tag_texts = []
                for tag in list(tags):
                    tag_text = tag.base_tag.text
                    if not tag_text.startswith(view_level):
                        if tag_text.startswith("sprint"):
                            tag_texts.append(f"[yellow]{tag_text}[/yellow]")
                        elif tag_text.startswith("epic"):
                            tag_texts.append(f"[green]{tag_text}[/green]")
                        elif tag_text.startswith("story"):
                            tag_texts.append(f"[magenta]{tag_text}[/magenta]")
                        elif tag_text.startswith("bug"):
                            tag_texts.append(f"[red]{tag_text}[/red]")
                        else:
                            tag_texts.append(tag_text)
                tag_string = ",".join(sorted(tag_texts))
            else:
                tag_string = ""
            if collaborators := entity.collaborators:
                collaborators_texts = sorted([
                    collaborator.users.name
                    for collaborator in list(collaborators)
                    if collaborator.users
                ])
                collaborator_string = ",".join(collaborators_texts)
            else:
                collaborator_string = ""
            if comments := entity.commentaries:
                comments.sort(key=lambda c: c.date, reverse=False)
            if history := entity.history:
                history.sort(key=lambda c: c.date, reverse=False)
            project = services.lookup_project_name(
                entity.project, repo)
            priority = entity.priority.name if hasattr(entity.priority,
                                                       "name") else "UNKNOWN"
            time_spent = formatter.Formatter.format_time_spent(
                entity.total_time_spent)
            if entity.status.name in ("DELETED", "DONE") and all_tasks:
                completed_tasks.append(entity)
                if story_points:
                    completed_story_points.append(story_point)
                continue
            entity_name = f"{entity.name}" if not comments else f"{entity.name} [blue][{len(comments)}][/blue]"

            completed_date = None
            if event_history := entity.history:
                completed_events = [
                    event.date for event in event_history
                    if event.new_value in ("DONE", "DELETED")
                ]
                if completed_events:
                    completed_date = max(completed_events).strftime("%Y-%m-%d")
            if not all_tasks:
                entity_id = str(entity.id)
            elif entity.is_overdue:
                entity_id = f"[red]{entity.id}[/red]"
            elif entity.is_stale:
                entity_id = f"[yellow]{entity.id}[/yellow]"
            else:
                entity_id = str(entity.id)

            printable_row = {
                "id": entity_id,
                "name": entity_name,
                "description": entity.description,
                "story_points": str(story_point),
                "status": entity.status.name,
                "priority": priority,
                "project": project,
                "due_date": str(entity.due_date or completed_date),
                "tags": tag_string,
                "collaborators": collaborator_string,
                "time_spent": str(time_spent)
            }
            printable_elements = [
                value for key, value in printable_row.items()
                if key in default_columns
            ]
            if story_points:
                table.add_row(*printable_elements)
            else:
                table.add_row(*printable_elements)
        if table.row_count == 1 and show_window:
            app = TerkaTask(entity=entity,
                            project=project,
                            history=history,
                            commentaries=comments)
            app.run()
        # # TODO: not working
        # if print_options.show_commentaries and (commentaries :=
        #                                         entity.commentaries):
        #     self.print_commentaries(commentaries)
        # # TODO: not working
        # if print_options.show_history and (history := entity.history):
        #     self.print_history(history)
        return table, completed_tasks, completed_story_points

    def _restore_status_history(self, placeholders, status_history):
        partial_history = status_history[
            status_history["last_status_for_date"].notnull()]
        current_values = status_history[["task",
                                         "current_status"]].drop_duplicates()
        if not partial_history.empty:
            joined = pd.merge(placeholders,
                              partial_history,
                              on=["task", "date"],
                              how="left")
            joined = joined.replace({np.nan: None})
            joined["filled_backward"] = joined.groupby(
                "task")["first_status_for_date"].bfill()
            joined["filled_forward"] = joined.groupby(
                "task")["last_status_for_date"].ffill()
            joined["filled_forward"] = joined.groupby(
                "task")["filled_forward"].fillna(joined.pop("filled_backward"))
            joined = pd.merge(joined, current_values, on="task", how="left")
            joined["status"] = joined["filled_forward"]
        else:
            joined = pd.merge(placeholders,
                              current_values,
                              on="task",
                              how="left")
        return joined[["date", "task", "status"]]

    def _print_time_utilization(self, time_entries) -> None:
        plt.date_form('Y-m-d')
        plt.plot_size(100, 15)
        plt.title(f"Time tracker - {format_hour_minute(sum(time_entries.values()))} spent")
        plt.bar(time_entries.keys(), time_entries.values())
        plt.show()


def format_hour_minute(time_minutes: int) -> str:
    if time_minutes < 1:
        return f"00H: {round(time_minutes * 60)}M"
    else:
        return f"{round(time_minutes // 1)}H:{round(time_minutes % 1* 60)}M"
