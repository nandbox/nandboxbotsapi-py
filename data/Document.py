import json


class Document:
    KEY_ID = "id"
    KEY_NAME = "name"
    KEY_SIZE = "size"

    id = None
    name = None
    size = None

    def __init__(self, dictionary):
        self.id = str(dictionary[self.KEY_ID]) if self.KEY_ID in dictionary.keys() else None
        self.name = str(dictionary[self.KEY_NAME]) if self.KEY_NAME in dictionary.keys() else None
        self.size = int(dictionary[self.KEY_SIZE]) if self.KEY_SIZE in dictionary.keys() else None

    def to_json_obj(self):

        dictionary = {}

        if self.id is not None:
            dictionary[self.KEY_ID] = self.id
        if self.name is not None:
            dictionary[self.KEY_NAME] = self.name
        if self.size is not None:
            dictionary[self.KEY_SIZE] = self.size

        return json.dumps(dictionary), dictionary
