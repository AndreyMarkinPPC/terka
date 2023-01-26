from typing import Dict, Optional

import abc
from datetime import datetime, timedelta
from . import orm
from src.domain.element import Element
from src.domain.task import Task
from src.domain.project import Project
from src.domain.user import User
from src.domain.event_history import Event
from sqlalchemy import and_, or_, not_


class AbsRepository(abc.ABC):

    def __init__(self):
        pass

    def add(self, element: Element) -> None:
        self._add(element)

    def get(self, element: Element, element_name: str) -> Element:
        element = self._get(element, element_name)
        return element

    def get_by_id(self, element: Element, element_id: int) -> Element:
        element = self._get_by_element_id(element, element_id)
        return element

    @abc.abstractmethod
    def _add(self, element: Element) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def _get(self, element: Element, element_name: str) -> Element:
        raise NotImplementedError @ abc.abstractmethod

    def _get_by_element_id(self, element_type: str,
                           element_id: int) -> Element:
        raise NotImplementedError


class SqlAlchemyRepository(AbsRepository):

    def __init__(self, session):
        super().__init__()
        self.session = session

    def delete(self, element: Element, element_id: str):
        return self.session.query(element).filter_by(id=element_id).delete()

    def update(self, element: Element, element_id: str,
               update_dict: Dict[str, str]):
        return self.session.query(element).filter_by(
            id=element_id).update(update_dict)

    def list(self, element: Element, filter_dict: Optional[Dict[str, str]]):
        query_object = self.session.query(element)
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
                            ~getattr(element, key).in_(values))
                    else:
                        query_object = query_object.filter(
                            getattr(element, key).in_(values))
            if query_dict:
                for key, value in query_dict.items():
                    if isinstance(value, str) and value.startswith("NOT"):
                        query_object = query_object.filter(
                            getattr(element, key) != value.replace("NOT:", ""))
                    if isinstance(value, datetime):
                        query_object = query_object.filter(
                            getattr(element, key) <= value)
                    else:
                        query_object = query_object.filter(
                            getattr(element, key) == value)

            if stale_check:
                days_ago = datetime.now().date() - timedelta(days=stale_lookback)
                query_object = query_object.filter(
                    getattr(element,
                            "status").in_(["TODO", "IN_PROGRESS", "REVIEW"])).join(
                                Event, (element.id == Event.element_id)).filter(
                                    Event.date <= days_ago, Event.type == "status")
                return query_object.all()
            if overdue_check:
                query_object = query_object.filter(
                    getattr(element, "due_date") < datetime.now().date())
                return query_object.all()
        elif isinstance(filter_dict, str):
            if overdue_check:
                query_object = query_object.filter(
                    getattr(element, "due_date") < datetime.now().date())
            if filter_dict.startswith("NOT:"):
                return query_object.filter(
                    getattr(element, "name") != filter_dict.replace(
                        "NOT:", "")).all()
            else:
                return query_object.filter_by(name=filter_dict).first()
        if overdue_check:
            query_object = query_object.filter(
                getattr(element, "due_date") < datetime.now().date())
        if stale_check:
            days_ago = datetime.now().date() - timedelta(days=stale_lookback)
            query_object = query_object.filter(
                getattr(element,
                        "status").in_(["TODO", "IN_PROGRESS", "REVIEW"])).join(
                            Event, (element.id == Event.element_id)).filter(
                                Event.date <= days_ago, Event.type == "status")
        return query_object.all()

    def _add(self, element):
        self.session.add(element)

    def _get(self, element, element_name):
        return self.session.query(element).filter_by(name=element_name).first()

    def _get_by_element_id(self, element, element_id):
        return (self.session.query(element).filter(id=element_id).first())
