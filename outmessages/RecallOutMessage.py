import json

from outmessages.OutMessage import OutMessage


class RecallOutMessage(OutMessage):
    KEY_MESSAGE_ID = "message_id"
    KEY_FROM_USER_ID = "from_user_id"

    message_id = None
    from_user_id = None

    def __init__(self):
        self.method = "recallMessage"

    def to_json_obj(self):
        _, dictionary = super(RecallOutMessage, self).to_json_obj()

        if self.message_id is not None:
            dictionary[self.KEY_MESSAGE_ID] = self.message_id
        if self.from_user_id is not None:
            dictionary[self.KEY_FROM_USER_ID] = self.from_user_id

        return json.dumps(dictionary), dictionary
