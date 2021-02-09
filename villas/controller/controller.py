import logging
import kombu.mixins

LOGGER = logging.getLogger(__name__)


class ControllerMixin(kombu.mixins.ConsumerMixin):

    def __init__(self, connection, components):
        self.components = {c.uuid: c for c in components if c.enabled}
        self.connection = connection

        for uuid, comp in self.components.items():
            LOGGER.info('Adding %s', comp)
            comp.set_mixin(self)
            comp.on_ready()

        self.active_components = self.components.copy()

    def get_consumers(self, Consumer, channel):
        return map(lambda comp: comp.get_consumer(channel),
                   self.active_components.values())

    def on_iteration(self):
        added = self.components.keys() - self.active_components.keys()
        removed = self.active_components.keys() - self.components.keys()
        if added or removed:
            LOGGER.info('Components changed. Restarting mixin')

            # We need to re-enter the contextmanager of the mixin
            # in order to consume messages for the new components
            self.should_stop = True

            for uuid in added:
                comp = self.components[uuid]

                LOGGER.info('Adding %s', comp)
                comp.set_mixin(self)

            for uuid in removed:
                comp = self.active_components[uuid]

                LOGGER.info('Removing %s', comp)

            self.active_components = self.components.copy()

    def run(self):
        while True:
            self.should_stop = False

            LOGGER.info('Startig mixing for %d components',
                        len(self.active_components))

            super().run()

    def shutdown(self):
        LOGGER.info('Shutdown controller')
        for u, c in self.components.items():
            c.on_shutdown()

        self.connection.drain_events(timeout=3)
