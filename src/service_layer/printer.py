from typing import Any, Dict, List, Tuple

from collections import defaultdict
from datetime import datetime, date, timedelta
import rich
from rich.console import Console
from rich.table import Table
from statistics import mean, median

from src.service_layer import services
from src.service_layer.ui import TerkaTask


class Printer:

    def __init__(self, box=rich.box.SIMPLE) -> None:
        self.box = box
        self.console = Console()

    def print_new_object(self, obj, project):
        table = Table(box=self.box)
        attributes = self._get_attributes(obj)
        for column, value in attributes:
            if value:
                table.add_column(column)
        table.add_row(*list(zip(*attributes))[1])
        self.console.print(table)

    def print_history(self, entities):
        table = Table(box=self.box)
        print("History:")
        for column in ("date", "type", "old_value", "new_value"):
            table.add_column(column)
        for event in entities:
            table.add_row(event.date.strftime("%Y-%m-%d %H:%M"),
                          event.type.name, event.old_value, event.new_value)
        self.console.print(table)

    def print_commentaries(self, entities):
        table = Table(box=self.box)
        print("Comments:")
        for column in ("date", "text"):
            table.add_column(column)
        entities.sort(key=lambda c: c.date, reverse=False)
        for event in entities:
            table.add_row(event.date.strftime("%Y-%m-%d %H:%M"), event.text)
        self.console.print(table)

    def print_entities(self,
                       entities,
                       type,
                       repo,
                       custom_sort,
                       show_completed=False):
        if type == "projects":
            entities.sort(key=self._sort_open_tasks, reverse=True)
            self.print_project(entities)
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
                            show_completed=show_completed,
                            custom_sort=custom_sort)
        elif type == "tags":
            self.print_tag(entities=entities)
        elif type == "users":
            self.print_user(entities=entities)
        elif type == "sprints":
            self.print_sprint(entities=entities, repo=repo)
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
        self.console.print(table)

    def print_default_entity(self, entities):
        table = Table(box=self.box)
        for column in ("id", "date", "text"):
            table.add_column(column)
        for entity in entities:
            table.add_row(f"[red]{entity.id}[/red]",
                          entity.date.strftime("%Y-%m-%d %H:%M"), entity.text)
        self.console.print(table)

    def print_sprint(self, entities, repo, show_tasks=True):
        table = Table(box=rich.box.SQUARE_DOUBLE_HEAD)
        for column in ("id", "start_date", "end_date", "goal", "status",
                       "open tasks", "tasks", "velocity", "collaborators"):
            table.add_column(column)
        for entity in entities:
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
                collaborators.append(f"{user} ({story_point})")

            collaborators = ", ".join(collaborators)
            open_tasks = [
                task for task in tasks
                if task.status.name not in ("DONE", "DELETED")
            ]
            table.add_row(str(entity.id), str(entity.start_date),
                          str(entity.end_date), entity.goal,
                          entity.status.name, str(len(open_tasks)),
                          str(len(tasks)), str(sum(story_points)),
                          collaborators)
        self.console.print(table)
        if show_tasks:
            self.print_sprint_task(entities=tasks,
                                   repo=repo,
                                   show_completed=True,
                                   story_points=story_points)

    def print_project(self,
                      entities,
                      zero_tasks: bool = False,
                      zero_tasks_only: bool = False):
        table = Table(box=rich.box.SQUARE_DOUBLE_HEAD)
        non_active_projects = Table(box=rich.box.SQUARE_DOUBLE_HEAD)
        for column in ("id", "name", "description", "status", "open_tasks",
                       "overdue", "backlog", "todo", "in_progress", "review",
                       "done", "median_task_age"):
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

                if zero_tasks or len(overdue_tasks) > 0:
                    entity_id = f"[red]{entity.id}[/red]"
                else:
                    entity_id = f"[green]{entity.id}[/green]"
                table.add_row(f"{entity_id}", entity.name, entity.description,
                              entity.status.name, str(open_tasks),
                              str(len(overdue_tasks)), str(backlog), str(todo),
                              str(in_progress), str(review), str(done),
                              str(median_task_age))
                # if zero_tasks_only and open_tasks == 0:
                #     table.add_row(f"[red]{entity.id}[/red]", entity.name,
                #                   entity.description, str(tasks))
            else:
                non_active_projects.add_row(str(entity.id), entity.name,
                                            entity.description,
                                            entity.status.name,
                                            str(open_tasks))

        self.console.print(table)
        if non_active_projects.row_count:
            self.console.print("[green]Inactive projects[/green]")
            self.console.print(non_active_projects)

    def print_sprint_task(self,
                          entities,
                          repo,
                          show_completed=False,
                          history=None,
                          comments=None,
                          story_points=None):
        table = Table(box=self.box)
        default_columns = ("id", "name", "description", "story points",
                           "status", "priority", "project", "due_date", "tags",
                           "collaborators")
        for column in default_columns:
            table.add_column(column)
        entities = list(entities)
        completed_tasks = []
        completed_tasks_story_points = []
        printable_entities = 0
        for entity, story_point in sorted(zip(entities, story_points),
                                          key=lambda x: x[0].status.value,
                                          reverse=True):
            if tags := entity.tags:
                tag_texts = sorted([tag.base_tag.text for tag in list(tags)])
                tag_string = ",".join(tag_texts)
            else:
                tag_string = ""
            if collaborators := entity.collaborators:
                collaborators_texts = sorted([
                    collaborator.users.name
                    for collaborator in list(collaborators)
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
            if entity.status.name in ("DELETED", "DONE"):
                completed_tasks.append(entity)
                completed_tasks_story_points.append(story_point)
                continue
            printable_entities += 1
            entity_name = f"{entity.name}"
            if entity.due_date and entity.due_date <= date.today():
                table.add_row(f"[red]{entity.id}[/red]", entity_name,
                              entity.description, str(story_point),
                              entity.status.name, priority, project,
                              str(entity.due_date), tag_string,
                              collaborator_string)
            else:
                table.add_row(str(entity.id), entity_name, entity.description,
                              str(story_point), entity.status.name, priority,
                              project, str(entity.due_date), tag_string,
                              collaborator_string)
        if show_completed and completed_tasks:
            self.console.print(f"[green]****OPEN TASKS*****[/green]")
        if printable_entities:
            if printable_entities == 1:
                app = TerkaTask(entity=entity,
                                project=project,
                                history=history,
                                commentaries=comments)
                app.run()
            self.console.print(table)
        if show_completed and completed_tasks:
            self.console.print(f"[green]****COMPLETED TASKS*****[/green]")
            table = Table(box=self.box)
            for column in default_columns:
                table.add_column(column)
            for entity, story_point in zip(completed_tasks,
                                           completed_tasks_story_points):
                try:
                    project_obj = services.lookup_project_name(
                        entity.project, repo)
                    project = project_obj.name
                except:
                    project = None
                priority = entity.priority.name if hasattr(
                    entity.priority, "name") else "UNKNOWN"
                if tags := entity.tags:
                    tag_texts = sorted(
                        [tag.base_tag.text for tag in list(tags)])
                    tag_string = ",".join(tag_texts)
                else:
                    tag_string = ""
                if collaborators := entity.collaborators:
                    collaborators_texts = sorted([
                        collaborator.users.name
                        for collaborator in list(collaborators)
                    ])
                    collaborator_string = ",".join(collaborators_texts)
                else:
                    collaborator_string = ""
                table.add_row(str(entity.id), entity.name, entity.description,
                              str(story_point), entity.status.name, priority,
                              project, str(entity.due_date), tag_string,
                              collaborator_string)
            self.console.print(table)
        if len(entities) == 1 and printable_entities == 0:
            table = Table(box=self.box)
            for column in default_columns:
                table.add_column(column)
            for entity in entities:
                app = TerkaTask(entity=entity,
                                project=project,
                                is_completed=True,
                                history=history,
                                commentaries=comments)
                app.run()
                table.add_row(str(entity.id), entity.name, entity.description,
                              entity.status.name, priority, project,
                              str(entity.due_date), tag_string,
                              collaborator_string)
            self.console.print(table)

    def print_task(self,
                   entities,
                   repo,
                   show_completed=False,
                   custom_sort=None,
                   history=None,
                   comments=None):
        table = Table(box=self.box)
        default_columns = ("id", "name", "description", "status", "priority",
                           "project", "due_date", "tags", "collaborators")
        #TODO: Add printing for only a single task
        # if (entities[0].status.name == "DONE"):
        #     console.print(f"[green]task is completed on [/green]")
        # else:
        #     active_in_days = datetime.now() - entities[0].creation_date
        #     console.print(f"[blue]task is active {active_in_days.days} days[/blue]")
        for column in default_columns:
            table.add_column(column)
        entities = list(entities)
        completed_tasks = []
        if custom_sort:
            entities.sort(key=lambda c: getattr(c, custom_sort), reverse=False)
        else:
            entities.sort(key=lambda c: (c.status.value, c.priority.value),
                          reverse=True)
        printable_entities = 0
        for entity in entities:
            if tags := entity.tags:
                tag_texts = sorted([tag.base_tag.text for tag in list(tags)])
                tag_string = ",".join(tag_texts)
            else:
                tag_string = ""
            if collaborators := entity.collaborators:
                collaborators_texts = sorted([
                    collaborator.users.name
                    for collaborator in list(collaborators)
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
            if entity.status.name in ("DELETED", "DONE"):
                completed_tasks.append(entity)
                continue
            printable_entities += 1
            entity_name = f"{entity.name}"
            if entity.due_date and entity.due_date <= date.today():
                table.add_row(f"[red]{entity.id}[/red]", entity_name,
                              entity.description, entity.status.name, priority,
                              project, str(entity.due_date), tag_string,
                              collaborator_string)
            else:
                table.add_row(str(entity.id), entity_name, entity.description,
                              entity.status.name, priority, project,
                              str(entity.due_date), tag_string,
                              collaborator_string)
        if show_completed and completed_tasks:
            self.console.print(f"[green]****OPEN TASKS*****[/green]")
        if printable_entities:
            if printable_entities == 1:
                app = TerkaTask(entity=entity,
                                project=project,
                                history=history,
                                commentaries=comments)
                app.run()
            self.console.print(table)
        if show_completed and completed_tasks:
            self.console.print(f"[green]****COMPLETED TASKS*****[/green]")
            table = Table(box=self.box)
            for column in default_columns:
                table.add_column(column)
            for entity in completed_tasks:
                table.add_row(str(entity.id), entity.name, entity.description,
                              entity.status.name, priority, project,
                              str(entity.due_date), tag_string,
                              collaborator_string)
            self.console.print(table)
        if len(entities) == 1 and printable_entities == 0:
            table = Table(box=self.box)
            for column in default_columns:
                table.add_column(column)
            for entity in entities:
                app = TerkaTask(entity=entity,
                                project=project,
                                is_completed=True,
                                history=history,
                                commentaries=comments)
                app.run()
                table.add_row(str(entity.id), entity.name, entity.description,
                              entity.status.name, priority, project,
                              str(entity.due_date), tag_string,
                              collaborator_string)
            self.console.print(table)

    def _get_attributes(self, obj) -> List[Tuple[str, str]]:
        import inspect
        attributes = []
        for name, value in inspect.getmembers(obj):
            if not name.startswith("_") and not inspect.ismethod(value):
                if not value:
                    continue
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
