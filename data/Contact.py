import json


class Contact:
    KEY_NAME = "name"
    KEY_PHONE_NUMBER = "phone_number"

    name = None
    phone_number = None

    def __init__(self, dictionary):
        self.name = str(dictionary[self.KEY_NAME])
        self.phone_number = str(dictionary[self.KEY_PHONE_NUMBER])

    def to_json_obj(self):

        dictionary = {}

        if self.name is not None:
            dictionary[self.KEY_NAME] = self.name
        if self.phone_number is not None:
            dictionary[self.KEY_PHONE_NUMBER] = self.phone_number

        return json.dumps(dictionary), dictionary
