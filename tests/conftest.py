import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, clear_mappers

from terka.adapters.orm import metadata, start_mappers
from terka.adapters import repository
from terka.domain import events
from terka.service_layer import unit_of_work

@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    return engine

@pytest.fixture
def session(in_memory_db):
    start_mappers()
    yield sessionmaker(bind=in_memory_db)()
    clear_mappers()


class FakeRepository(repository.AbsRepository):

    def __init__(self):
        super().__init__()
        self.session = list()

    def _add(self, element):
        self.session.append(element)

    def _get(self, task_id):
        return next(e for e in self.session if e.id == task_id)

    def _get_by_condition(self, entity_name, condition_value):
        try:
            return next(e for e in self.session
                        if getattr(e, entity_name) == condition_value)
        except StopIteration:
            return None

    def _list(self):
        return list(self.session)

    def _update(self, task_id, update_dict):
        element = self._get(task_id)
        element_dict = element.__dict__
        element_dict.update(update_dict)
        element.__init__(**element_dict)

    def _delete(self, task_id):
        element = self._get(task_id)
        self.session.remove(element)


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    tasks: FakeRepository = FakeRepository()
    published_events: list[events.Event] = []

    def __init__(self, url) -> None:
        ...

    def _commit(self):
        self.committed = True

    def _flush(self):
        self.flushed = True

    def rollback(self):
        ...

@pytest.fixture
def uow(): 
    return unit_of_work.SqlAlchemyUnitOfWork("sqlite:///:memory:")
