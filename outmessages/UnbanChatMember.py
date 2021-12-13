import json

from outmessages.OutMessage import OutMessage


class UnbanChatMember(OutMessage):
    KEY_USER_ID = "user_id"

    user_id = None

    def __init__(self):
        self.method = "unbanChatMember"

    def to_json_obj(self):
        _, dictionary = super(UnbanChatMember, self).to_json_obj()

        if self.chat_id is not None:
            dictionary[self.KEY_CHAT_ID] = self.chat_id
        if self.user_id is not None:
            dictionary[self.KEY_USER_ID] = self.user_id

        return json.dumps(dictionary), dictionary
