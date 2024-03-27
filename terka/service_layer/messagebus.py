from __future__ import annotations

import logging
from typing import Type

from terka import exceptions
from terka.adapters import publisher
from terka.domain import commands
from terka.domain import events
from terka.presentations.console import printer
from terka.service_layer import handlers
from terka.service_layer import unit_of_work

Message = commands.Command | events.Event


class MessageBus:

    def __init__(self,
                 uow: unit_of_work.AbstractUnitOfWork,
                 event_handlers: Type[handlers.Handler],
                 command_handlers: Type[handlers.Handler],
                 config: dict | None = None,
                 publisher: publisher.BasePublisher | None = None,
                 ) -> None:
        self.uow = uow
        self.publisher = publisher
        self.event_handlers = event_handlers
        self.command_handlers = command_handlers
        self.config = config
        self.return_value = None
        self.printer = printer.Printer(uow)

    def handle(self, message: Message, context: dict = {}):
        self.queue = [message]
        while self.queue:
            message = self.queue.pop(0)
            if isinstance(message, events.Event):
                self.handle_event(message, context)
            elif isinstance(message, commands.Command):
                self.handle_command(message, context)

        if self.return_value:
            return self.return_value

    def handle_command(self, command: commands.Command,
                       context: dict) -> None:
        handler = self.command_handlers[type(command)]
        try:
            if result := handler(command, self, context):
                self.return_value = result
            self.queue.extend(self.uow.collect_new_events())
        except exceptions.TaskAddedToEntity:
            logging.warning('Task already added to compound entity')

    def handle_event(self, event: events.Event, context: dict) -> None:
        for handler in self.event_handlers[type(event)]:
            if result := handler(event, self, context):
                self.return_value = result
            self.queue.extend(self.uow.collect_new_events())
