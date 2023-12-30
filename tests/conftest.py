import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, clear_mappers

from terka import bootstrap
from terka.adapters.orm import metadata, start_mappers
from terka.adapters import publisher, repository
from terka.domain import events
from terka.service_layer import unit_of_work


class FakePublisher(publisher.BasePublisher):

    def __init__(self):
        self.events = []  # type: Dict[str, List[str]]

    def publish(self, topic, event):
        self.events.append(event)


@pytest.fixture(scope="session")
def fake_publisher():
    return FakePublisher()


@pytest.fixture(scope="session")
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    return engine


@pytest.fixture(scope="session")
def session(in_memory_db):
    start_mappers()
    yield sessionmaker(bind=in_memory_db)()
    clear_mappers()


@pytest.fixture(scope="session")
def uow():
    return unit_of_work.SqlAlchemyUnitOfWork("sqlite:///:memory:")


@pytest.fixture(scope="session")
def bus(fake_publisher, uow):
    return bootstrap.bootstrap(start_orm=True,
                               uow=uow,
                               publish_service=fake_publisher,
                               config={
                                   "user": "test_user",
                                   "workspace": "default"
                               })
