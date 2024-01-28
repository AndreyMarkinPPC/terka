from __future__ import annotations

import abc
from collections.abc import MutableSequence
from datetime import datetime, timedelta

from terka.domain.entities.entity import Entity
from terka.domain.entities.event_history import TaskEvent
from . import orm


class AbsRepository(abc.ABC):

    def __init__(self):
        pass

    def add(self, entity: Entity) -> None:
        self._add(entity)

    def get(self, entity: Entity, entity_name: str) -> Entity:
        return self._get(entity, entity_name)

    def get_by_id(self, entity: Entity, entity_id: int) -> Entity:
        return self._get_by_entity_id(entity, entity_id)

    def get_by_conditions(self, entity: Entity,
                          conditions: dict) -> list[Entity]:
        return self._get_by_conditions(entity, conditions)

    @abc.abstractmethod
    def _add(self, entity: Entity) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def _get(self, entity: Entity, entity_name: str) -> Entity:
        ...

    @abc.abstractmethod
    def _get_by_entity_id(self, entity_type: str,
                           entity_id: int) -> Entity:
        ...

    @abc.abstractmethod
    def _get_by_conditions(self, entity: Entity,
                           conditions: dict) -> list[Entity]:
        ...


class SqlAlchemyRepository(AbsRepository):

    def __init__(self, session):
        super().__init__()
        self.session = session

    def delete(self, entity: Entity, entity_id: str):
        return self.session.query(entity).filter_by(id=entity_id).delete()

    def update(self, entity: Entity, entity_id: str,
               update_dict: dict[str, str]):
        return self.session.query(entity).filter_by(
            id=entity_id).update(update_dict)

    def list(self,
             entity: Entity,
             filter_dict: dict[str, str] = {}):
        query_object = self.session.query(entity)
        overdue_check = False
        stale_check = False
        if "overdue" in filter_dict:
            overdue_check = True
            del filter_dict["overdue"]
        if "stale" in filter_dict:
            stale_check = True
            stale_lookback = int(filter_dict["stale"])
            del filter_dict["stale"]
        if filter_dict and isinstance(filter_dict, dict):
            query_dict = {}
            or_values = {}
            for k, v in filter_dict.items():
                if isinstance(v, str):
                    if len((multiple_values := v.split(","))) == 1:
                        query_dict[k] = str(v)
                    else:
                        or_values[k] = [str(v) for v in multiple_values]
                elif isinstance(v, int):
                    query_dict[k] = str(v)
                elif isinstance(v, datetime):
                    query_dict[k] = v
                else:
                    if len(v) > 1:
                        or_values[k] = [str(v) for v in v]
                    else:
                        query_dict[k] = str(v[0])
            if or_values:
                for key, values in or_values.items():
                    if values[0].startswith("NOT"):
                        values = [
                            value.replace("NOT:", "") for value in values
                        ]
                        query_object = query_object.filter(
                            ~getattr(entity, key).in_(values))
                    else:
                        query_object = query_object.filter(
                            getattr(entity, key).in_(values))
            if query_dict:
                for key, value in query_dict.items():
                    if isinstance(value, str) and value.startswith("NOT"):
                        query_object = query_object.filter(
                            getattr(entity, key) != value.replace("NOT:", ""))
                    if isinstance(value, datetime):
                        query_object = query_object.filter(
                            getattr(entity, key) <= value)
                    else:
                        query_object = query_object.filter(
                            getattr(entity, key) == value)

            if stale_check:
                days_ago = datetime.now().date() - timedelta(
                    days=stale_lookback)
                query_object = query_object.filter(
                    getattr(entity, "status").in_([
                        "TODO", "IN_PROGRESS", "REVIEW"
                    ])).join(TaskEvent, (entity.id == TaskEvent.task)).filter(
                        TaskEvent.date <= days_ago, TaskEvent.type == "STATUS")
                return query_object.all()
            if overdue_check:
                query_object = query_object.filter(
                    getattr(entity, "due_date") < datetime.now().date())
                return query_object.all()
        elif isinstance(filter_dict, str):
            if overdue_check:
                query_object = query_object.filter(
                    getattr(entity, "due_date") < datetime.now().date())
            if filter_dict.startswith("NOT:"):
                return query_object.filter(
                    getattr(entity, "name") != filter_dict.replace(
                        "NOT:", "")).all()
            else:
                return query_object.filter_by(name=filter_dict).first()
        if overdue_check:
            query_object = query_object.filter(
                getattr(entity, "due_date") < datetime.now().date())
        if stale_check:
            days_ago = datetime.now().date() - timedelta(days=stale_lookback)
            query_object = query_object.filter(
                getattr(entity,
                        "status").in_(["TODO", "IN_PROGRESS", "REVIEW"])).join(
                            Event, (entity.id == Event.entity_id)).filter(
                                Event.date <= days_ago, Event.type == "status")
        return query_object.all()

    def _add(self, entity):
        self.session.add(entity)

    def _get(self, entity, entity_name):
        return self.session.query(entity).filter_by(
            name=entity_name).one_or_none()

    def _get_by_entity_id(self, entity, entity_id):
        return self.session.query(entity).filter_by(
            id=entity_id).one_or_none()

    def _get_by_conditions(self, entity, conditions):
        query = self.session.query(entity)
        for condition_name, condition_value in conditions.items():
            if isinstance(condition_value, MutableSequence):
                query = query.filter(
                    getattr(entity, condition_name).in_(condition_value))
            else:
                query = query.filter(
                    getattr(entity, condition_name) == condition_value)
        return query.all()
