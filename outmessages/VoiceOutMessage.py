import json

from outmessages.OutMessage import OutMessage


class VoiceOutMessage(OutMessage):
    KEY_VOICE = "voice"
    KEY_SIZE = "size"

    voice = None
    size = None

    def __init__(self):
        self.method = "sendVoice"

    def to_json_obj(self):
        _, dictionary = super(VoiceOutMessage, self).to_json_obj()

        if self.voice is not None:
            dictionary[self.KEY_VOICE] = self.voice
        if self.size is not None:
            dictionary[self.KEY_SIZE] = self.size

        return json.dumps(dictionary), dictionary
