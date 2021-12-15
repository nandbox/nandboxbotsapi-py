import json

from outmessages.OutMessage import OutMessage


class GetBlackListOutMessage(OutMessage):
    __KEY_PAGE_SIZE = "page_size"

    page_size = None

    def __init__(self):
        self.method = "getBlacklist"

    def to_json_obj(self):
        _, dictionary = super(GetBlackListOutMessage, self).to_json_obj()

        if self.page_size is not None:
            dictionary[self.__KEY_PAGE_SIZE] = self.page_size

        return json.dumps(dictionary), dictionary
