from typing import Any, Callable, Dict, Type


from terka.domain import _commands, events
from terka.service_layer import unit_of_work, handlers


Message = _commands.Command | events.Event

class MessageBus:
    def __init__(
        self,
        uow: unit_of_work.AbstractUnitOfWork,
        publisher,
        event_handlers: Type[handlers.Handler],
        command_handlers: Type[handlers.Handler] 
    ) -> None:
        self.handler = handlers.Handler(uow, publisher)
        self.event_handlers = event_handlers
        self.command_handlers = command_handlers
        self.return_value = None

    def handle(self, message: Message):
        self.queue = [message]
        while self.queue:
            message = self.queue.pop(0)
            if isinstance(message, events.Event):
                self.handle_event(message)
            elif isinstance(message, _commands.Command):
                self.handle_command(message)

        if self.return_value:
            return self.return_value

    def handle_command(self, command: _commands.Command) -> None:
        handler = self.command_handlers[type(command)]
        result = handler(command, self.handler)
        self.return_value = result
        self.queue.extend(self.handler.uow.collect_new_events())

    def handle_event(self, event: events.Event) -> None:
        for handler in self.event_handlers[type(event)]:
            handler(event, self.handler)
            self.queue.extend(self.handler.uow.collect_new_events())

