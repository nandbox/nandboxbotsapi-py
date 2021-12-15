import json

from data.Chat import Chat
from data.User import User


class InlineSearch:
    KEY_INLINE_SEARCH = "inlineSearch"
    KEY_DATE = "date"
    KEY_METHOD = "method"
    KEY_CHAT = "chat"
    KEY_FROM = "from"
    KEY_SEARCH_ID = "search_id"
    KEY_OFFSET = "offset"
    KEY_KEYWORDS = "keywords"

    date = None
    method = None
    chat = None
    from_ = None
    search_id = None
    offset = None
    keywords = None

    def __init__(self, dictionary):

        inline_search_dict = dictionary[self.KEY_INLINE_SEARCH] if self.KEY_INLINE_SEARCH in dictionary.keys() else {}

        from_user = User(inline_search_dict.get(self.KEY_FROM, {}))

        self.chat = Chat(inline_search_dict.get(self.KEY_CHAT, None))
        self.method = str(inline_search_dict[self.KEY_METHOD]) if self.KEY_METHOD in inline_search_dict.keys() else None
        self.from_ = from_user
        self.date = int(inline_search_dict[self.KEY_DATE]) if self.KEY_DATE in inline_search_dict.keys() else None
        self.search_id = int(inline_search_dict[self.KEY_SEARCH_ID]) if self.KEY_SEARCH_ID in inline_search_dict.keys() else None
        self.offset = str(inline_search_dict[self.KEY_OFFSET]) if self.KEY_OFFSET in inline_search_dict.keys() else None
        self.keywords = str(inline_search_dict[self.KEY_KEYWORDS]) if self.KEY_KEYWORDS in inline_search_dict.keys() else None

    def to_json_obj(self):

        dictionary = {}

        if self.date is not None:
            dictionary[self.KEY_DATE] = self.date
        if self.from_ is not None:
            _, from_user_dict = self.from_.to_json_obj()
            dictionary[self.KEY_FROM] = from_user_dict
        if self.chat is not None:
            _, chat_dict = self.chat.to_json_obj()
            dictionary[self.KEY_CHAT] = chat_dict
        if self.method is not None:
            dictionary[self.KEY_METHOD] = self.method
        if self.search_id is not None:
            dictionary[self.KEY_SEARCH_ID] = self.search_id
        if self.offset is not None:
            dictionary[self.KEY_OFFSET] = self.offset
        if self.keywords is not None:
            dictionary[self.KEY_KEYWORDS] = self.keywords

        return json.dumps(dictionary), dictionary
