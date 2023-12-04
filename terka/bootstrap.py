import inspect

from terka.adapters import orm, publisher
from terka.service_layer import handlers, messagebus, unit_of_work


def bootstrap(
    uow: unit_of_work.AbstractUnitOfWork,
    start_orm: bool = True,
    publish_service: publisher.BasePublisher = publisher.LogPublisher(),
    config: dict | None = None
) -> messagebus.MessageBus:

    if start_orm:
        orm.start_mappers(engine=uow.engine)

    return messagebus.MessageBus(uow=uow,
                                 publisher=publish_service,
                                 event_handlers=handlers.EVENT_HANDLERS,
                                 command_handlers=handlers.COMMAND_HANDLERS,
                                 config=config)
