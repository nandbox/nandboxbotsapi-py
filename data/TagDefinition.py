import json


class TagDefinition:
    KEY_NAME = "name"
    KEY_DESCRIPTION = "description"
    KEY_ID = "id"
    KEY_ISPRIVATE = "isPrivate"

    name = None
    description = None
    id = None
    is_private = None

    def __init__(self, dictionary):

        self.id = str(dictionary[self.KEY_ID]) if self.KEY_ID in dictionary.keys() else None
        self.name = str(dictionary[self.KEY_NAME]) if self.KEY_NAME in dictionary.keys() else None
        self.description = str(dictionary[self.KEY_DESCRIPTION]) if self.KEY_DESCRIPTION in dictionary.keys() else None
        self.is_private = str(dictionary[self.KEY_ISPRIVATE]) if self.KEY_ISPRIVATE in dictionary.keys() else None

    def to_json_obj(self):

        dictionary = {}

        if self.id is not None:
            dictionary[self.KEY_ID] = self.id
        if self.name is not None:
            dictionary[self.KEY_NAME] = self.name
        if self.description is not None:
            dictionary[self.KEY_DESCRIPTION] = self.description
        if self.is_private is not None:
            dictionary[self.KEY_ISPRIVATE] = self.is_private

        return json.dumps(dictionary), dictionary
