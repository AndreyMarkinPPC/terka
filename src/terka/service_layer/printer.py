from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from operator import attrgetter
import inspect
from copy import deepcopy

from collections import defaultdict
from datetime import datetime, date, timedelta
import plotext as plt
import rich
from rich.console import Console
from rich.table import Table
from statistics import mean, median

from terka.service_layer import services, views
from terka.service_layer.ui import TerkaTask


@dataclass
class PrintOptions:
    show_tasks: bool = True
    show_history: bool = False
    show_commentaries: bool = False
    show_completed: bool = False
    show_epics: bool = True
    show_stories: bool = True


class Printer:

    def __init__(self, repo, box=rich.box.SIMPLE) -> None:
        self.console = Console()
        self.box = box
        self.repo = repo

    def print_new_object(self, obj, project):
        table = Table(box=self.box)
        attributes = self._get_attributes(obj)
        for column, value in attributes:
            if value:
                table.add_column(column)
        table.add_row(*list(zip(*attributes))[1])
        if table.row_count:
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
        if entity_type == "epics":
            if entities:
                self.print_epic(entities, repo, print_options)
            else:
                exit(f"No epic with id '{task}' found!")
        if entity_type == "stories":
            if entities:
                self.print_story(entities, repo, print_options)
            else:
                exit(f"No story with id '{task}' found!")
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

    def print_entities(self, entities, type, repo, custom_sort, print_options):
        if type == "projects":
            entities.sort(key=self._sort_open_tasks, reverse=True)
            self.print_project(entities, print_options)
        elif type == "tasks":
            if custom_sort:
                entities.sort(key=lambda c: getattr(c, custom_sort),
                              reverse=False)
            else:
                entities.sort(key=lambda c:
                              (c.status.value, c.priority.value
                               if hasattr(c.priority, "value") else 0),
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
        elif type == "epics":
            self.print_epic(entities=entities,
                            repo=repo,
                            print_options=print_options)
        elif type == "stories":
            self.print_story(entities=entities,
                             repo=repo,
                             print_options=print_options)
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

    def print_default_entity(self, entities):
        table = Table(box=self.box)
        for column in ("id", "date", "text"):
            table.add_column(column)
        for entity in entities:
            table.add_row(f"[red]{entity.id}[/red]",
                          entity.date.strftime("%Y-%m-%d %H:%M"), entity.text)
        if table.row_count:
            self.console.print(table)

    def print_epic(self, entities, repo, print_options):
        table = Table(box=self.box, title="EPICS", expand=True)
        for column in ("id", "name", "description", "project", "tasks"):
            table.add_column(column, style="bold")
        for i, entity in enumerate(entities):
            tasks = []
            for epic_task in entity.epic_tasks:
                task = epic_task.tasks
                tasks.append(task)
            try:
                project_obj = services.lookup_project_name(
                    entity.project, repo)
                project = project_obj.name
            except:
                project = None
            table.add_row(f"E{entity.id}", str(entity.name),
                          entity.description, project, str(len(tasks)))
        if table.row_count:
            self.console.print(table)
        if print_options.show_tasks:
            self.print_task(entities=tasks,
                            repo=repo,
                            print_options=print_options,
                            show_window=False)
        if i == 0 and print_options.show_commentaries and (
                commentaries := entity.commentaries):
            self.print_commentaries(commentaries)

    def print_story(self, entities, repo, print_options):
        table = Table(box=self.box, title="STORIES", expand=True)
        for column in ("id", "name", "description", "project", "tasks"):
            table.add_column(column, style="bold")
        for i, entity in enumerate(entities):
            tasks = []
            for story_task in entity.story_tasks:
                task = story_task.tasks
                tasks.append(task)
            try:
                project_obj = services.lookup_project_name(
                    entity.project, repo)
                project = project_obj.name
            except:
                project = None
            table.add_row(f"S{entity.id}", str(entity.name),
                          entity.description, project, str(len(tasks)))
        if table.row_count:
            self.console.print(table)
        if print_options.show_tasks and tasks:
            self.print_task(entities=tasks,
                            repo=repo,
                            print_options=print_options,
                            show_window=False)
        if i == 0 and print_options.show_commentaries and (
                commentaries := entity.commentaries):
            self.print_commentaries(commentaries)

    def print_sprint(self, entities, repo, print_options, kwargs=None):
        table = Table(box=rich.box.SQUARE_DOUBLE_HEAD)
        for column in ("id", "start_date", "end_date", "goal", "status",
                       "open tasks", "tasks", "velocity", "collaborators",
                       "time_spent"):
            table.add_column(column)
        for i, entity in enumerate(entities):
            story_points = []
            tasks = []
            collaborators = []
            collaborators_dict = defaultdict(int)
            for sprint_task in entity.sprint_tasks:
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
            time_spent_sum = sum([
                entry.time_spent_minutes for task in tasks
                for entry in task.time_spent
            ])

            time_spent = self._format_time_spent(time_spent_sum)
            table.add_row(str(entity.id), str(entity.start_date),
                          str(entity.end_date), entity.goal,
                          entity.status.name, str(len(open_tasks)),
                          str(len(tasks)), str(round(sum(story_points),
                                                     2)), collaborators_string,
                          str(time_spent))
        if table.row_count:
            self.console.print(table)

        if print_options.show_tasks:
            task_print_options = deepcopy(print_options)
            task_print_options.show_commentaries = False
            self.print_task(entities=tasks,
                            repo=repo,
                            print_options=task_print_options,
                            story_points=story_points,
                            kwargs=kwargs,
                            show_window=False)
        if i == 0 and print_options.show_commentaries and (
                commentaries := entities[0].commentaries):
            self.print_commentaries(commentaries)
        time_entries = views.time_spent(repo.session, entity.start_date,
                                        entity.end_date)
        dates = [entry.get("date") for entry in time_entries]
        times = [entry.get("time_spent_hours") for entry in time_entries]
        plt.date_form('Y-m-d')
        plt.plot_size(100, 15)
        plt.title("Time tracker")
        plt.bar(dates, times)
        plt.show()

    def print_project(self, entities, print_options, kwargs=None):
        table = Table(box=rich.box.SQUARE_DOUBLE_HEAD, expand=True)
        non_active_projects = Table(box=rich.box.SQUARE_DOUBLE_HEAD)
        for column in ("id", "name", "description", "status", "open_tasks",
                       "overdue", "stale", "backlog", "todo", "in_progress",
                       "review", "done", "median_task_age"):
            table.add_column(column)
        for column in ("id", "name", "description", "status", "open_tasks"):
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
                    if (event_history :=
                            task.history) and task.status.name in (
                                "TODO", "IN_PROGRESS", "REVIEW"):
                        for event in event_history:
                            if max([
                                    event.date for event in event_history
                            ]) < (datetime.today() - timedelta(days=5)):
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
                table.add_row(f"{entity_id}", entity.name, entity.description,
                              entity.status.name, str(open_tasks),
                              str(len(overdue_tasks)), str(len(stale_tasks)),
                              str(backlog), str(todo), str(in_progress),
                              str(review), str(done), str(median_task_age))
            else:
                non_active_projects.add_row(str(entity.id), entity.name,
                                            entity.description,
                                            entity.status.name,
                                            str(open_tasks))

        if table.row_count:
            self.console.print(table)
        if non_active_projects.row_count:
            self.console.print("[green]Inactive projects[/green]")
            self.console.print(non_active_projects)
        non_task_view_options = deepcopy(print_options)
        non_task_view_options.show_tasks = False
        if print_options.show_epics and (epics := entity.epics):
            self.console.print("")
            self.print_epic(epics, self.repo, non_task_view_options)
        if print_options.show_stories and (stories := entity.stories):
            self.console.print("")
            self.print_story(stories, self.repo, non_task_view_options)
        if print_options.show_tasks and (tasks := entity.tasks):
            task_print_options = deepcopy(print_options)
            task_print_options.show_commentaries = False
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

    def print_task(self,
                   entities,
                   repo,
                   print_options,
                   custom_sort=None,
                   show_window=True,
                   story_points=None,
                   kwargs=None):
        table = Table(box=self.box, title="TASKS")
        if story_points:
            default_columns = ("id", "name", "description", "story points",
                               "status", "priority", "project", "due_date",
                               "tags", "collaborators", "time_spent")
        else:
            default_columns = ("id", "name", "description", "status",
                               "priority", "project", "due_date", "tags",
                               "collaborators", "time_spent")
        #TODO: Add printing for only a single task
        # if (entities[0].status.name == "DONE"):
        #     console.print(f"[green]task is completed on [/green]")
        # else:
        #     active_in_days = datetime.now() - entities[0].creation_date
        #     console.print(f"[blue]task is active {active_in_days.days} days[/blue]")
        entities = list(entities)
        if kwargs:
            entities = self._get_filtered_entities(entities, kwargs)
        if not story_points:
            if custom_sort:
                entities.sort(key=lambda c: getattr(c, custom_sort),
                              reverse=False)
            else:
                entities.sort(key=lambda c: (c.status.value, c.priority.value),
                              reverse=True)
        table, completed_tasks, completed_story_points = self._print_task(
            table=table,
            entities=entities,
            default_columns=default_columns,
            repo=repo,
            story_points=story_points,
            show_window=show_window)
        if table.row_count:
            self.console.print(table)
        if print_options.show_completed and completed_tasks:
            table = Table(box=self.box)
            table, *rest = self._print_task(
                table=table,
                entities=completed_tasks,
                default_columns=default_columns,
                repo=repo,
                story_points=completed_story_points,
                show_window=show_window,
                all_tasks=False)
            if table.row_count:
                self.console.print(f"[green]****COMPLETED TASKS*****[/green]")
                self.console.print(table)

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
                    attributes.append((name, project.name))
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

    def _calculate_time_spent(self, entity) -> str:
        time_spent_sum = sum(
            [entry.time_spent_minutes for entry in entity.time_spent])
        return self._format_time_spent(time_spent_sum)

    def _format_time_spent(self, time_spent: int) -> str:
        time_spent_hours = time_spent // 60
        time_spent_minutes = time_spent % 60
        if time_spent_hours and time_spent_minutes:
            time_spent = f"{time_spent_hours}H:{time_spent_minutes}M"
        elif time_spent_hours:
            time_spent = f"{time_spent_hours}H"
        elif time_spent_minutes:
            time_spent = f"{time_spent_minutes}M"
        else:
            time_spent = ""
        return time_spent

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
                    show_window=True):
        if all_tasks:
            completed_tasks = []
        else:
            completed_tasks = None
            completed_story_points = None
        if story_points:
            completed_story_points = []
            entities = [(entity, story_point) for entity, story_point in
                        sorted(zip(entities, story_points),
                               key=lambda x: x[0].status.value,
                               reverse=True)]
        else:
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
                tag_texts = sorted([tag.base_tag.text for tag in list(tags)])
                tag_string = ",".join(tag_texts)
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
            try:
                project_obj = services.lookup_project_name(
                    entity.project, repo)
                project = project_obj.name
            except:
                project = None
            priority = entity.priority.name if hasattr(entity.priority,
                                                       "name") else "UNKNOWN"
            time_spent = self._calculate_time_spent(entity)
            if entity.status.name in ("DELETED", "DONE") and all_tasks:
                completed_tasks.append(entity)
                if story_points:
                    completed_story_points.append(story_point)
                continue
            entity_name = f"{entity.name}" if not comments else f"{entity.name} [blue][{len(comments)}][/blue]"
            if not all_tasks:
                entity_id = str(entity.id)
            elif entity.due_date and entity.due_date <= date.today():
                entity_id = f"[red]{entity.id}[/red]"
            elif (event_history := entity.history) and entity.status.name in (
                    "TODO", "IN_PROGRESS", "REVIEW"):
                if max([event.date for event in event_history
                        ]) < (datetime.today() - timedelta(days=5)):
                    entity_id = f"[yellow]{entity.id}[/yellow]"
                else:
                    entity_id = str(entity.id)
            else:
                entity_id = str(entity.id)
            if story_points:
                table.add_row(entity_id, entity_name, entity.description,
                              str(story_point), entity.status.name, priority,
                              project, str(entity.due_date), tag_string,
                              collaborator_string, str(time_spent))
            else:
                table.add_row(entity_id, entity_name, entity.description,
                              entity.status.name, priority, project,
                              str(entity.due_date), tag_string,
                              collaborator_string, str(time_spent))
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
