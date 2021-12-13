import json

from outmessages.OutMessage import OutMessage


class GeneratePermanentUrl(OutMessage):
    KEY_FILE = "file"
    KEY_PARAM1 = "param1"

    file = None
    param1 = None

    def __init__(self):
        self.method = "generatePermanentUrl"

    def to_json_obj(self):
        _, dictionary = super(GeneratePermanentUrl, self).to_json_obj()

        if self.file is not None:
            dictionary[self.KEY_FILE] = self.file
        if self.param1 is not None:
            dictionary[self.KEY_PARAM1] = self.param1

        return json.dumps(dictionary), dictionary
    