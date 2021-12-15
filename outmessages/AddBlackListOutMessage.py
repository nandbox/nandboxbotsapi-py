import json

from outmessages.OutMessage import OutMessage


class AddBlackListOutMessage(OutMessage):
    __KEY_USERS = "users"

    users = []

    def __init__(self):
        self.method = "addBlacklist"

    def to_json_obj(self):
        _, dictionary = super(AddBlackListOutMessage, self).to_json_obj()

        if self.users is not None:
            dictionary[self.__KEY_USERS] = self.users

        return json.dumps(dictionary), dictionary
