from villas.controller.components.manager import Manager
from villas.controller.component import Component


class GenericManager(Manager):

    create_schema = {
        '$schema': 'http://json-schema.org/draft-04/schema#',
        'properties': {
        }
    }

    def create(self, message):
        component = Component.from_dict(message.payload.get('parameters'))

        try:
            self.add_component(component)
        except KeyError:
            self.logger.error('A component with the UUID %s already exists',
                              component.uuid)

    def delete(self, message):
        parameters = message.payload.get('parameters')
        uuid = parameters.get('uuid')

        try:
            comp = self.components[uuid]

            self.remove_component(comp)

        except KeyError:
            self.logger.error('There is not component with UUID: %s', uuid)
