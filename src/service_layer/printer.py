from typing import Any, Dict, List, Tuple

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

    def print_new_object(self, obj, project):
        console = Console()
        table = Table(box=self.box)
        attributes = self._get_attributes(obj)
        for column, _ in attributes:
            table.add_column(column)
        table.add_row(*list(zip(*attributes))[1])
        console.print(table)


    def print_history(self, entities):
        console = Console()
        table = Table(box=self.box)
        print("History:")
        for column in ("date", "type", "old_value", "new_value"):
            table.add_column(column)
        for event in entities:
            table.add_row(event.date.strftime("%Y-%m-%d %H:%M"), event.type,
                          event.old_value, event.new_value)
        console.print(table)


    def print_commentaries(self, entities):
        console = Console()
        table = Table(box=self.box)
        print("Comments:")
        for column in ("date", "text"):
            table.add_column(column)
        for event in entities:
            table.add_row(event.date.strftime("%Y-%m-%d %H:%M"), event.text)
        console.print(table)



    def print_entities(self, entities, type, repo, custom_sort):
        if type == "projects":
            entities.sort(key=self._sort_open_tasks, reverse=True)
            self.print_project(entities)
        elif type == "tasks":
            if custom_sort:
                entities.sort(key=lambda c: getattr(c, custom_sort), reverse=False)
            else:
                entities.sort(key=lambda c:
                              (c.status.value, c.priority.value
                               if hasattr(c.priority, "value") else 0),
                              reverse=True)
            self.print_task(entities=entities, repo=repo, custom_sort=custom_sort)
        else:
            self.print_default_entity(self, entities)


    def print_default_entity(self, entities):
        console = Console()
        table = Table(box=self.box)
        for column in ("id", "date", "text"):
            table.add_column(column)
        for entity in entities:
            table.add_row(f"[red]{entity.id}[/red]",
                          entity.date.strftime("%Y-%m-%d %H:%M"), entity.text)
        console.print(table)


    def print_project(self, entities,
                      zero_tasks: bool = False,
                      zero_tasks_only: bool = False):
        console = Console()
        table = Table(box=rich.box.SQUARE_DOUBLE_HEAD)
        for column in ("id", "name", "description", "open_tasks", "overdue",
                       "backlog", "todo", "in_progress", "review", "done",
                       "median_task_age"):
            table.add_column(column)
        for entity in entities:
            if entity.status.name == "DELETED":
                continue
            open_tasks = self._sort_open_tasks(entity)
            if open_tasks > 0:
                overdue_tasks = [
                    task for task in entity.tasks
                    if task.due_date and task.due_date <= datetime.now().date()
                    and task.status.name not in ("DELETED", "DONE")
                ]
                median_task_age = round(
                    median([(datetime.now() - task.creation_date).days
                            for task in entity.tasks
                            if task.status.name not in ("DELETED", "DONE")]))
                backlog = self._count_task_status(entity.tasks, "BACKLOG")
                todo = self._count_task_status(entity.tasks, "TODO")
                in_progress = self._count_task_status(entity.tasks, "IN_PROGRESS")
                review = self._count_task_status(entity.tasks, "REVIEW")
                done = self._count_task_status(entity.tasks, "DONE")

                if zero_tasks or len(overdue_tasks) > 0:
                    entity_id = f"[red]{entity.id}[/red]"
                else:
                    entity_id = f"[green]{entity.id}[/green]"
                table.add_row(f"{entity_id}", entity.name, entity.description,
                              str(open_tasks),
                              str(len(overdue_tasks)), str(backlog), str(todo),
                              str(in_progress), str(review), str(done),
                              str(median_task_age))
                # if zero_tasks_only and open_tasks == 0:
                #     table.add_row(f"[red]{entity.id}[/red]", entity.name,
                #                   entity.description, str(tasks))
        console.print(table)

    def print_task(self, entities,
                   repo,
                   show_completed=False,
                   custom_sort=None,
                   history=None,
                   comments=None):
        console = Console()
        table = Table(box=self.box)
        #TODO: Add printing for only a single task
        # if (entities[0].status.name == "DONE"):
        #     console.print(f"[green]task is completed on [/green]")
        # else:
        #     active_in_days = datetime.now() - entities[0].creation_date
        #     console.print(f"[blue]task is active {active_in_days.days} days[/blue]")
        for column in ("id", "name", "description", "status", "priority",
                       "project", "due_date"):
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
            try:
                project_obj = services.lookup_project_name(entity.project, repo)
                project = project_obj.name
            except:
                project = None
            priority = entity.priority.name if hasattr(entity.priority,
                                                       "name") else "UNKNOWN"
            if entity.status.name in ("DELETED", "DONE"):
                completed_tasks.append(entity)
                continue
            printable_entities += 1
            if entity.due_date and entity.due_date <= date.today():
                table.add_row(f"[red]{entity.id}[/red]", entity.name,
                              entity.description, entity.status.name, priority,
                              project, str(entity.due_date))
            else:
                table.add_row(str(entity.id), entity.name, entity.description,
                              entity.status.name, priority, project,
                              str(entity.due_date))
        if show_completed:
            console.print(f"[green]****OPEN TASKS*****[/green]")
        if printable_entities:
            if printable_entities == 1:
                app = TerkaTask(entity=entity,
                                project=project,
                                history=history,
                                commentaries=comments)
                app.run()
            console.print(table)
        if show_completed:
            if show_completed:
                console.print(f"[green]****COMPLETED TASKS*****[/green]")
            table = Table(box=self.box)
            for column in ("id", "name", "description", "status", "priority",
                           "project", "due_date"):
                table.add_column(column)
            for entity in completed_tasks:
                table.add_row(str(entity.id), entity.name, entity.description,
                              entity.status.name, priority, project,
                              str(entity.due_date))
            console.print(table)
        if len(entities) == 1 and printable_entities == 0:
            table = Table(box=self.box)
            for column in ("id", "name", "description", "status", "priority",
                           "project", "due_date"):
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
                              str(entity.due_date))
            console.print(table)

    def _get_attributes(self, obj) -> List[Tuple[str, str]]:
        import inspect
        attributes = []
        for name, value in inspect.getmembers(obj):
            if not name.startswith("_") and not inspect.ismethod(value):
                if hasattr(value, "name"):
                    attributes.append((name, value.name))
                elif isinstance(value, datetime):
                    attributes.append((name, value.strftime("%Y-%m-%d %H:%M")))
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
