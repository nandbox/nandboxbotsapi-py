import datetime
import json
import time
from threading import Thread, Lock
from nandboxbots.util.Logger import Logger
import websocket

from nandboxbots.data.Chat import Chat
from nandboxbots.data.User import User
from nandboxbots.inmessages.BlackList import BlackList
from nandboxbots.inmessages.ChatAdministrators import ChatAdministrators
from nandboxbots.inmessages.ChatMember import ChatMember
from nandboxbots.inmessages.ChatMenuCallback import ChatMenuCallback
from nandboxbots.inmessages.IncomingMessage import IncomingMessage
from nandboxbots.inmessages.InlineMessageCallback import InlineMessageCallback
from nandboxbots.inmessages.InlineSearch import InlineSearch
from nandboxbots.inmessages.MessageAck import MessageAck
from nandboxbots.inmessages.WhiteList import WhiteList
from nandboxbots.inmessages.PermanentUrl import PermanentUrl
from nandboxbots import nandbox
from nandboxbots.outmessages.AddBlackListOutMessage import AddBlackListOutMessage
from nandboxbots.outmessages.AddBlacklistPatternsOutMessage import AddBlacklistPatternsOutMessage
from nandboxbots.outmessages.AddWhiteListOutMessage import AddWhiteListOutMessage
from nandboxbots.outmessages.AddWhitelistPatternsOutMessage import AddWhitelistPatternsOutMessage
from nandboxbots.outmessages.AudioOutMessage import AudioOutMessage
from nandboxbots.outmessages.BanChatMemberOutMessage import BanChatMemberOutMessage
from nandboxbots.outmessages.ContactOutMessage import ContactOutMessage
from nandboxbots.outmessages.DeleteBlackListOutMessage import DeleteBlackListOutMessage
from nandboxbots.outmessages.DeleteBlackListPatternsOutMessage import DeleteBlackListPatternsOutMessage
from nandboxbots.outmessages.DeleteWhiteListOutMessage import DeleteWhiteListOutMessage
from nandboxbots.outmessages.DeleteWhiteListPatternsOutMessage import DeleteWhiteListPatternsOutMessage
from nandboxbots.outmessages.DocumentOutMessage import DocumentOutMessage
from nandboxbots.outmessages.GeneratePermanentUrl import GeneratePermanentUrl
from nandboxbots.outmessages.GetBlackListOutMessage import GetBlackListOutMessage
from nandboxbots.outmessages.GetChatAdministratorsOutMessage import GetChatAdministratorsOutMessage
from nandboxbots.outmessages.GetChatMemberOutMessage import GetChatMemberOutMessage
from nandboxbots.outmessages.GetChatOutMessage import GetChatOutMessage
from nandboxbots.outmessages.GetMyProfiles import GetMyProfiles
from nandboxbots.outmessages.GetUserOutMessage import GetUserOutMessage
from nandboxbots.outmessages.GetWhiteListOutMessage import GetWhiteListOutMessage
from nandboxbots.outmessages.LocationOutMessage import LocationOutMessage
from nandboxbots.outmessages.PhotoOutMessage import PhotoOutMessage
from nandboxbots.outmessages.RecallOutMessage import RecallOutMessage
from nandboxbots.outmessages.RemoveChatMemberOutMessage import RemoveChatMemberOutMessage
from nandboxbots.outmessages.SetChatOutMessage import SetChatOutMessage
from nandboxbots.outmessages.SetMyProfileOutMessage import SetMyProfileOutMessage
from nandboxbots.outmessages.TextOutMessage import TextOutMessage
from nandboxbots.outmessages.UnbanChatMember import UnbanChatMember
from nandboxbots.outmessages.UpdateOutMessage import UpdateOutMessage
from nandboxbots.outmessages.VideoOutMessage import VideoOutMessage
from nandboxbots.outmessages.VoiceOutMessage import VoiceOutMessage
from nandboxbots.util import Utils

CGREEN = '\033[92m'
CRED = '\033[91m'
CEND = '\033[0m'


class NandboxClient:
    BOT_ID = None
    nandboxClient = None
    webSocketClient = None

    closingCounter = 0
    timeOutCounter = 0
    connRefusedCounter = 0

    _uri = None
    KEY_METHOD = "method"
    KEY_ERROR = "error"

    config = None
    lock = Lock()
    log = Logger().xlog

    def __init__(self, config):
        self.config = config
        self._uri = self.config["URI"]

    @staticmethod
    def init(config):
        NandboxClient.lock.acquire()

        if NandboxClient.nandboxClient is not None:
            return

        NandboxClient.nandboxClient = NandboxClient(config)

        NandboxClient.lock.release()

    @staticmethod
    def get(config):
        if NandboxClient.nandboxClient is None:
            NandboxClient.init(config)

        return NandboxClient.nandboxClient

    def connect(self, token, callback):
        internalWebSocket = self.InternalWebSocket(token=token, callback=callback)
        # websocket.enableTrace(True)
        NandboxClient.webSocketClient = websocket.WebSocketApp(self._uri, on_error=internalWebSocket.on_error,
                                                               on_close=internalWebSocket.on_close,
                                                               on_message=internalWebSocket.on_message,
                                                               on_open=internalWebSocket.on_open)
        NandboxClient.webSocketClient.run_forever()

    def get_uri(self):
        return self._uri

    def set_uri(self, uri):
        self._uri = uri

    class InternalWebSocket:
        NO_OF_RETRIES_IF_CONN_TO_SERVER_REFUSED = 20
        NO_OF_RETRIES_IF_CONN_TIMEDOUT = 10
        NO_OF_RETRIES_IF_CONN_CLOSED = 20
        KEY_USER = "user"
        KEY_CHAT = "chat"
        KEY_NAME = "name"
        KEY_ID = "ID"

        callback = None
        session = None
        token = None
        api = None

        authenticated = False
        echo = False
        lastMessage = 0

        class PingThread(Thread):
            interrupted = False

            def run(self):
                while True:
                    try:
                        obj = {
                            NandboxClient.KEY_METHOD: "PING"
                        }

                        NandboxClient.InternalWebSocket.send(json.dumps(obj))
                    except():
                        NandboxClient.log.error("Exception when sending ping")

                    if self.interrupted:
                        return

                    try:
                        time.sleep(
                            3)  # this blocks the thread not the process: https://stackoverflow.com/questions/92928/time-sleep-sleeps-thread-or-process
                    except():
                        self.interrupted = True
                        return

        pingThread = None

        def __init__(self, token, callback):
            self.token = token
            self.callback = callback

        def on_close(self, close_status_code, close_msg):
            NandboxClient.log.info("INTERNAL: ONCLOSE")
            NandboxClient.log.info(f"StatusCode = {str(close_status_code)}")
            NandboxClient.log.info(f"Reason : {str(close_msg)}")

            now = datetime.datetime.now()
            dt_string = now.strftime("%Y/%m/%d %H:%M:%S")
            NandboxClient.log.info(f"Date = {dt_string}")

            NandboxClient.InternalWebSocket.authenticated = False

            if NandboxClient.InternalWebSocket.pingThread is not None:
                NandboxClient.InternalWebSocket.PingThread.interrupted = True

            NandboxClient.InternalWebSocket.pingThread = None

            NandboxClient.InternalWebSocket.callback.onClose()

            if (
                    close_status_code == 1000 or close_status_code == 1006 or close_status_code == 1001 or close_status_code == close_status_code == 1005) and NandboxClient.closingCounter < NandboxClient.InternalWebSocket.NO_OF_RETRIES_IF_CONN_CLOSED:
                try:
                    NandboxClient.log.info("Please wait 10 seconds for Reconnecting ")
                    time.sleep(10)
                    NandboxClient.closingCounter = NandboxClient.closingCounter + 1
                    NandboxClient.log.info(f"Connection Closing counter is  : {str(NandboxClient.closingCounter)}")
                except Exception as e:
                    NandboxClient.log.error(e)
                    NandboxClient.InternalWebSocket.PingThread.interrupted = True

                self.__stop_websocket_client()

                try:
                    self.__reconnect_websocket_client()

                except Exception as e:
                    NandboxClient.log.error(e)
                    NandboxClient.InternalWebSocket.PingThread.interrupted = True

        def __stop_websocket_client(self):
            NandboxClient.log.info("Stopping Websocket client")

            try:
                if NandboxClient.webSocketClient is not None:
                    NandboxClient.webSocketClient.close()
                    NandboxClient.webSocketClient = None
                    NandboxClient.log.info("Websocket client stopped Successfully")
            except Exception as e:
                NandboxClient.log.error("Exception while stopping websocket client")
                NandboxClient.log.error(e)

        def __reconnect_websocket_client(self):
            NandboxClient.log.info("Creating new web socket client")

            # TODO: Should I instantiate the websocket client here?

            NandboxClient.log.info("web socket client started")
            NandboxClient.log.info("Getting nandbox client instance")

            n_client = NandboxClient.get(NandboxClient.config)

            NandboxClient.log.info("Calling nandbox client connect")
            n_client.connect(NandboxClient.InternalWebSocket.token, NandboxClient.InternalWebSocket.callback)

        @staticmethod
        def send(string):
            # print(
            #     f'{CGREEN} {Utils.format_date(datetime.datetime.now())} >>>>>>>>> Sent JSON : {string} {CEND}')
            NandboxClient.webSocketClient.send(data=string)

        def on_open(self, ws):

            NandboxClient.log.info("INTERNAL: ONCONNECT")

            auth_object = {
                "method": "TOKEN_AUTH",
                "token": self.token,
                "rem": True
            }

            class nandboxAPI(nandbox.Nandbox.Api):
                def send(self, message):
                    now = datetime.datetime.now()
                    dt_string = now.strftime("%Y/%m/%d %H:%M:%S")

                    NandboxClient.log.info(f"{dt_string} >>>>>> Sending Message : {message}")
                    NandboxClient.InternalWebSocket.send(string=message)  # TODO convert to string?

                @staticmethod
                def prepare_out_message(message, chat_id, reference, reply_to_message_id, to_user_id,
                                        web_page_preview, disable_notification, caption, chat_settings, tab):
                    message.chat_id = chat_id
                    message.reference = reference

                    if to_user_id is not None:
                        message.to_user_id = to_user_id
                    if reply_to_message_id is not None:
                        message.reply_to_message_id = reply_to_message_id
                    if web_page_preview is not None:
                        message.web_page_preview = web_page_preview
                    if disable_notification is not None:
                        message.disable_notification = disable_notification
                    if caption is not None:
                        message.caption = caption
                    if chat_settings is not None:
                        message.chat_settings = chat_settings
                    if tab is not None:
                        message.tab = tab

                    return message

                def send_text(self, chat_id, text, reference, reply_to_message_id=None, to_user_id=None,
                              web_page_preview=None, disable_notification=None, chat_settings=None, bg_color=None,
                              tab=None):

                    if (chat_id is not None and
                            text is not None and
                            reference is None and
                            reply_to_message_id is None and
                            to_user_id is None and
                            web_page_preview is None and
                            disable_notification is None and
                            chat_settings is None and
                            bg_color is None and
                            tab is None):
                        reference = Utils.get_unique_id()

                        self.send_text(chat_id=chat_id, text=text, reference=reference)
                    else:
                        message = TextOutMessage()

                        message = nandboxAPI.prepare_out_message(message=message,
                                                                 chat_id=chat_id,
                                                                 reference=reference,
                                                                 reply_to_message_id=reply_to_message_id,
                                                                 to_user_id=to_user_id,
                                                                 web_page_preview=web_page_preview,
                                                                 disable_notification=disable_notification,
                                                                 caption=None,
                                                                 chat_settings=chat_settings,
                                                                 tab=tab)

                        message.method = "sendMessage"
                        message.text = text
                        message.bg_color = bg_color

                        obj, _ = message.to_json_obj()
                        self.send(obj)

                def send_text_with_background(self, chat_id, text, bg_color):
                    reference = Utils.get_unique_id()
                    self.send_text(chat_id=chat_id, text=text, reference=reference, bg_color=bg_color)

                def send_photo(self, chat_id, photo_file_id, reference, reply_to_message_id=None, to_user_id=None,
                               web_page_preview=None, disable_notification=None, caption=None, chat_settings=None,
                               tab=None):
                    if (chat_id is not None and
                            photo_file_id is not None and
                            caption is not None and
                            reference is None and
                            reply_to_message_id is None and
                            to_user_id is None and
                            web_page_preview is None and
                            disable_notification is None and
                            chat_settings is None and
                            tab is None):

                        reference = Utils.get_unique_id()

                        self.send_photo(chat_id=chat_id, photo_file_id=photo_file_id, reference=reference,
                                        caption=caption)
                    else:
                        message = PhotoOutMessage()
                        message = nandboxAPI.prepare_out_message(message=message,
                                                                 chat_id=chat_id,
                                                                 reference=reference,
                                                                 reply_to_message_id=reply_to_message_id,
                                                                 to_user_id=to_user_id,
                                                                 web_page_preview=web_page_preview,
                                                                 disable_notification=disable_notification,
                                                                 caption=caption,
                                                                 chat_settings=chat_settings,
                                                                 tab=tab)
                        message.method = "sendPhoto"
                        message.photo = photo_file_id

                        obj, _ = message.to_json_obj()
                        self.send(obj)

                def send_contact(self, chat_id, phone_number, name, reference, reply_to_message_id=None,
                                 to_user_id=None, web_page_preview=None, disable_notification=None, chat_settings=None,
                                 tab=None):
                    if (chat_id is not None and
                            phone_number is not None and
                            name is not None and
                            reference is None and
                            reply_to_message_id is None and
                            to_user_id is None and
                            web_page_preview is None and
                            disable_notification is None and
                            chat_settings is None and
                            tab is None):
                        reference = Utils.get_unique_id()

                        self.send_contact(chat_id=chat_id, phone_number=phone_number, name=name, reference=reference)
                    else:
                        contactOutMessage = ContactOutMessage()
                        contactOutMessage = nandboxAPI.prepare_out_message(message=contactOutMessage,
                                                                           chat_id=chat_id,
                                                                           reference=reference,
                                                                           reply_to_message_id=reply_to_message_id,
                                                                           to_user_id=to_user_id,
                                                                           web_page_preview=web_page_preview,
                                                                           disable_notification=disable_notification,
                                                                           chat_settings=chat_settings,
                                                                           tab=tab,
                                                                           caption=None)
                        contactOutMessage.method = "sendContact"
                        contactOutMessage.phone_number = phone_number
                        contactOutMessage.name = name

                        obj, _ = contactOutMessage.to_json_obj()
                        self.send(obj)

                def send_video(self, chat_id, video_file_id, reference, reply_to_message_id=None, to_user_id=None,
                               web_page_preview=None, disable_notification=None, caption=None, chat_settings=None,
                               tab=None):
                    if (chat_id is not None and
                            video_file_id is not None and
                            caption is not None and
                            reference is None and
                            reply_to_message_id is None and
                            to_user_id is None and
                            web_page_preview is None and
                            disable_notification is None and
                            chat_settings is None and
                            tab is None):

                        reference = Utils.get_unique_id()

                        self.send_video(chat_id=chat_id, video_file_id=video_file_id, reference=reference,
                                        caption=caption)

                    else:
                        message = VideoOutMessage()

                        message = self.prepare_out_message(message=message,
                                                           chat_id=chat_id,
                                                           reference=reference,
                                                           reply_to_message_id=reply_to_message_id,
                                                           to_user_id=to_user_id,
                                                           web_page_preview=web_page_preview,
                                                           disable_notification=disable_notification,
                                                           caption=caption,
                                                           chat_settings=chat_settings,
                                                           tab=tab)
                        message.method = "sendVideo"
                        message.video = video_file_id

                        obj, _ = message.to_json_obj()
                        self.send(obj)

                def send_audio(self, chat_id, audio_file_id, reference, reply_to_message_id=None, to_user_id=None,
                               web_page_preview=None, disable_notification=None, caption=None, performer=None,
                               title=None, chat_settings=None, tab=None):
                    if (chat_id is not None and
                            audio_file_id is not None and
                            caption is not None and
                            reference is None and
                            reply_to_message_id is None and
                            to_user_id is None and
                            web_page_preview is None and
                            disable_notification is None and
                            performer is None and
                            title is None and
                            chat_settings is None and
                            tab is None):

                        reference = Utils.get_unique_id()

                        self.send_audio(chat_id=chat_id, audio_file_id=audio_file_id, reference=reference,
                                        caption=caption)

                    else:
                        message = AudioOutMessage()

                        message = nandboxAPI.prepare_out_message(message=message,
                                                                 chat_id=chat_id,
                                                                 reference=reference,
                                                                 reply_to_message_id=reply_to_message_id,
                                                                 to_user_id=to_user_id,
                                                                 web_page_preview=web_page_preview,
                                                                 disable_notification=disable_notification,
                                                                 caption=caption,
                                                                 chat_settings=chat_settings,
                                                                 tab=tab)

                        message.method = "sendAudio"
                        message.performer = performer
                        message.title = title
                        message.audio = audio_file_id

                        obj, _ = message.to_json_obj()
                        self.send(obj)

                def send_voice(self, chat_id, voice_file_id, reference, reply_to_message_id=None, to_user_id=None,
                               web_page_preview=None, disable_notification=None, caption=None, size=None,
                               chat_settings=None, tab=None):
                    if (chat_id is not None and
                            voice_file_id is not None and
                            caption is not None and
                            reference is None and
                            reply_to_message_id is None and
                            to_user_id is None and
                            web_page_preview is None and
                            disable_notification is None and
                            size is None and
                            chat_settings is None and
                            tab is None):

                        reference = Utils.get_unique_id()

                        self.send_voice(chat_id=chat_id, voice_file_id=voice_file_id, reference=reference,
                                        caption=caption)

                    else:
                        message = VoiceOutMessage()

                        message = nandboxAPI.prepare_out_message(message=message,
                                                                 chat_id=chat_id,
                                                                 reference=reference,
                                                                 reply_to_message_id=reply_to_message_id,
                                                                 to_user_id=to_user_id,
                                                                 web_page_preview=web_page_preview,
                                                                 disable_notification=disable_notification,
                                                                 caption=caption,
                                                                 chat_settings=chat_settings,
                                                                 tab=tab)

                        message.method = "sendVoice"
                        message.size = size
                        message.voice = voice_file_id

                        obj, _ = message.to_json_obj()
                        self.send(obj)

                def send_document(self, chat_id, document_file_id, reference, reply_to_message_id=None, to_user_id=None,
                                  web_page_preview=None, disable_notification=None, caption=None, name=None, size=None,
                                  chat_settings=None, tab=None):
                    if (chat_id is not None and
                            document_file_id is not None and
                            caption is not None and
                            reference is None and
                            reply_to_message_id is None and
                            to_user_id is None and
                            web_page_preview is None and
                            disable_notification is None and
                            name is None and
                            size is None and
                            chat_settings is None and
                            tab is None):

                        reference = Utils.get_unique_id()

                        self.send_document(chat_id=chat_id, document_file_id=document_file_id, reference=reference,
                                           caption=caption)

                    else:
                        message = DocumentOutMessage()

                        message = nandboxAPI.prepare_out_message(message=message,
                                                                 chat_id=chat_id,
                                                                 reference=reference,
                                                                 reply_to_message_id=reply_to_message_id,
                                                                 to_user_id=to_user_id,
                                                                 web_page_preview=web_page_preview,
                                                                 disable_notification=disable_notification,
                                                                 caption=caption,
                                                                 chat_settings=chat_settings,
                                                                 tab=tab)

                        message.method = "sendDocument"
                        message.document = document_file_id
                        message.name = name
                        message.size = size

                        obj, _ = message.to_json_obj()
                        self.send(obj)

                def send_location(self, chat_id, latitude, longitude, reference, reply_to_message_id=None,
                                  to_user_id=None, web_page_preview=None, disable_notification=None, name=None,
                                  details=None, chat_settings=None, tab=None):
                    if (chat_id is not None and
                            latitude is not None and
                            longitude is not None and
                            reference is None and
                            reply_to_message_id is None and
                            to_user_id is None and
                            web_page_preview is None and
                            disable_notification is None and
                            name is None and
                            details is None and
                            chat_settings is None and
                            tab is None):

                        reference = Utils.get_unique_id()

                        self.send_location(chat_id=chat_id, latitude=latitude, longitude=longitude, reference=reference)

                    else:
                        message = LocationOutMessage()

                        message = nandboxAPI.prepare_out_message(message=message,
                                                                 chat_id=chat_id,
                                                                 reference=reference,
                                                                 reply_to_message_id=reply_to_message_id,
                                                                 to_user_id=to_user_id,
                                                                 web_page_preview=web_page_preview,
                                                                 disable_notification=disable_notification,
                                                                 chat_settings=chat_settings,
                                                                 tab=tab,
                                                                 caption=None)

                        message.method = "sendLocation"
                        message.name = name
                        message.details = details

                        obj, _ = message.to_json_obj()
                        self.send(obj)

                def send_gif(self, chat_id, gif_file_id, reference, reply_to_message_id=None, to_user_id=None,
                             web_page_preview=None, disable_notification=None, caption=None, chat_settings=None,
                             tab=None):
                    if (chat_id is not None and
                            gif_file_id is not None and
                            caption is not None and
                            reference is None and
                            reply_to_message_id is None and
                            to_user_id is None and
                            web_page_preview is None and
                            disable_notification is None and
                            chat_settings is None and
                            tab is None):

                        reference = Utils.get_unique_id()

                        self.send_photo(chat_id=chat_id, photo_file_id=gif_file_id, reference=reference,
                                        caption=caption)

                    else:
                        message = PhotoOutMessage()

                        message = nandboxAPI.prepare_out_message(message=message,
                                                                 chat_id=chat_id,
                                                                 reference=reference,
                                                                 reply_to_message_id=reply_to_message_id,
                                                                 to_user_id=to_user_id,
                                                                 web_page_preview=web_page_preview,
                                                                 disable_notification=disable_notification,
                                                                 caption=caption,
                                                                 chat_settings=chat_settings,
                                                                 tab=tab)

                        message.method = "sendPhoto"
                        message.photo = gif_file_id

                        obj, _ = message.to_json_obj()
                        self.send(obj)

                def send_gif_video(self, chat_id, gif_file_id, reference, reply_to_message_id=None, to_user_id=None,
                                   web_page_preview=None, disable_notification=None, caption=None, chat_settings=None,
                                   tab=None):
                    if (chat_id is not None and
                            gif_file_id is not None and
                            caption is not None and
                            reference is None and
                            reply_to_message_id is None and
                            to_user_id is None and
                            web_page_preview is None and
                            disable_notification is None and
                            chat_settings is None and
                            tab is None):

                        reference = Utils.get_unique_id()

                        self.send_video(chat_id=chat_id, video_file_id=gif_file_id, reference=reference,
                                        caption=caption)
                    else:
                        message = VideoOutMessage()

                        message = nandboxAPI.prepare_out_message(message=message,
                                                                 chat_id=chat_id,
                                                                 reference=reference,
                                                                 reply_to_message_id=reply_to_message_id,
                                                                 to_user_id=to_user_id,
                                                                 web_page_preview=web_page_preview,
                                                                 disable_notification=disable_notification,
                                                                 caption=caption,
                                                                 chat_settings=chat_settings,
                                                                 tab=tab)
                        message.method = "sendVideo"
                        message.video = gif_file_id

                        obj, _ = message.to_json_obj()
                        self.send(obj)

                def update_message(self, message_id, text=None, caption=None, to_user_id=None, chat_id=None, tab=None):
                    updateMessage = UpdateOutMessage()

                    updateMessage.message_id = message_id
                    updateMessage.text = text
                    updateMessage.caption = caption
                    updateMessage.to_user_id = to_user_id
                    updateMessage.chat_id = chat_id
                    updateMessage.tab = tab

                    obj, _ = updateMessage.to_json_obj()
                    self.send(obj)

                def update_text_msg(self, message_id, text, to_user_id, tab):
                    self.update_message(message_id=message_id, text=text, to_user_id=to_user_id, tab=tab)

                def update_media_caption(self, message_id, caption, to_user_id, tab):
                    self.update_message(message_id=message_id, caption=caption, to_user_id=to_user_id, tab=tab)

                def update_chat_msg(self, message_id, text, chat_id, tab):
                    self.update_message(message_id=message_id, text=text, chat_id=chat_id, tab=tab)

                def update_chat_media_caption(self, message_id, caption, chat_id, tab):
                    self.update_message(message_id=message_id, caption=caption, chat_id=chat_id, tab=tab)

                def get_chat_member(self, chat_id, user_id):
                    getChatMemberOutMessage = GetChatMemberOutMessage()

                    getChatMemberOutMessage.chat_id = chat_id
                    getChatMemberOutMessage.user_id = user_id

                    obj, _ = getChatMemberOutMessage.to_json_obj()
                    self.send(obj)

                def get_user(self, user_id):
                    getUserOutMessage = GetUserOutMessage()

                    getUserOutMessage.user_id = user_id

                    obj, _ = getUserOutMessage.to_json_obj()
                    self.send(obj)

                def get_chat(self, chat_id):
                    chatOutMessage = GetChatOutMessage()

                    chatOutMessage.chat_id = chat_id

                    obj, _ = chatOutMessage.to_json_obj()
                    self.send(obj)

                def get_chat_administrators(self, chat_id):
                    getChatAdministratorsOutMessage = GetChatAdministratorsOutMessage()

                    getChatAdministratorsOutMessage.chat_id = chat_id

                    obj, _ = getChatAdministratorsOutMessage.to_json_obj()
                    self.send(obj)

                def ban_chat_member(self, chat_id, user_id):
                    banChatMemberOutMessage = BanChatMemberOutMessage()

                    banChatMemberOutMessage.chat_id = chat_id
                    banChatMemberOutMessage.user_id = user_id

                    obj, _ = banChatMemberOutMessage.to_json_obj()
                    self.send(obj)

                def add_black_list(self, chat_id, users):
                    addBlackListOutMessage = AddBlackListOutMessage()

                    addBlackListOutMessage.chat_id = chat_id
                    addBlackListOutMessage.users = users

                    obj, _ = addBlackListOutMessage.to_json_obj()
                    self.send(obj)

                def add_white_list(self, chat_id, white_list_users):
                    addWhitelistOutMessage = AddWhiteListOutMessage()

                    addWhitelistOutMessage.chat_id = chat_id
                    addWhitelistOutMessage.white_list_users = white_list_users

                    obj, _ = addWhitelistOutMessage.to_json_obj()
                    self.send(obj)

                def delete_black_list(self, chat_id, users):
                    deleteBlackListOutMessage = DeleteBlackListOutMessage()

                    deleteBlackListOutMessage.chat_id = chat_id
                    deleteBlackListOutMessage.users = users

                    obj, _ = deleteBlackListOutMessage.to_json_obj()
                    self.send(obj)

                def delete_white_list(self, chat_id, users):
                    deleteWhiteListOutMessage = DeleteWhiteListOutMessage()

                    deleteWhiteListOutMessage.chat_id = chat_id
                    deleteWhiteListOutMessage.users = users

                    obj, _ = deleteWhiteListOutMessage.to_json_obj()
                    self.send(obj)

                def delete_black_list_patterns(self, chat_id, pattern):
                    deleteBlackListPatterns = DeleteBlackListPatternsOutMessage()

                    deleteBlackListPatterns.chat_id = chat_id
                    deleteBlackListPatterns.pattern = pattern

                    obj, _ = deleteBlackListPatterns.to_json_obj()
                    self.send(obj)

                def delete_white_list_patterns(self, chat_id, pattern):
                    deleteWhiteListPatterns = DeleteWhiteListPatternsOutMessage()

                    deleteWhiteListPatterns.chat_id = chat_id
                    deleteWhiteListPatterns.pattern = pattern

                    obj, _ = deleteWhiteListPatterns.to_json_obj()
                    self.send(obj)

                def add_black_list_patterns(self, chat_id, data):
                    addBlacklistPatternsOutMessage = AddBlacklistPatternsOutMessage()

                    addBlacklistPatternsOutMessage.chat_id = chat_id
                    addBlacklistPatternsOutMessage.data = data

                    obj, _ = addBlacklistPatternsOutMessage.to_json_obj()
                    self.send(obj)

                def add_white_list_patterns(self, chat_id, data):
                    addWhitelistPatternsOutMessage = AddWhitelistPatternsOutMessage()

                    addWhitelistPatternsOutMessage.chat_id = chat_id
                    addWhitelistPatternsOutMessage.data = data

                    obj, _ = addWhitelistPatternsOutMessage.to_json_obj()
                    self.send(obj)

                def unban_chat_member(self, chat_id, user_id):
                    unbanChatMember = UnbanChatMember()

                    unbanChatMember.chat_id = chat_id
                    unbanChatMember.user_id = user_id

                    obj, _ = unbanChatMember.to_json_obj()
                    self.send(obj)

                def remove_chat_member(self, chat_id, user_id):
                    removeChatMemberOutMessage = RemoveChatMemberOutMessage()

                    removeChatMemberOutMessage.chat_id = chat_id
                    removeChatMemberOutMessage.user_id = user_id

                    obj, _ = removeChatMemberOutMessage.to_json_obj()
                    self.send(obj)

                def recall_message(self, chat_id, message_id, to_user_id, reference):
                    recallOutMessage = RecallOutMessage()

                    recallOutMessage.chat_id = chat_id
                    recallOutMessage.message_id = message_id
                    recallOutMessage.to_user_id = to_user_id

                    obj, _ = recallOutMessage.to_json_obj()
                    self.send(obj)

                def set_my_profile(self, user):
                    setMyProfileOutMessage = SetMyProfileOutMessage()

                    setMyProfileOutMessage.user = user

                    obj, _ = setMyProfileOutMessage.to_json_obj()
                    self.send(obj)

                def set_chat(self, chat):
                    setChatOutMessage = SetChatOutMessage()

                    setChatOutMessage.chat = chat

                    obj, _ = setChatOutMessage.to_json_obj()
                    self.send(obj)

                def get_my_profiles(self):
                    getMyProfiles = GetMyProfiles()

                    obj, _ = getMyProfiles.to_json_obj()
                    self.send(obj)

                def generate_permanent_url(self, file, param1):
                    generatePermanentUrl = GeneratePermanentUrl()

                    generatePermanentUrl.file = file
                    generatePermanentUrl.param1 = param1

                    obj, _ = generatePermanentUrl.to_json_obj()
                    self.send(obj)

                def get_black_list(self, chat_id):
                    getBlackListOutMessage = GetBlackListOutMessage()

                    getBlackListOutMessage.chat_id = chat_id

                    obj, _ = getBlackListOutMessage.to_json_obj()
                    self.send(obj)

                def get_white_list(self, chat_id):
                    getWhiteListOutMessage = GetWhiteListOutMessage()

                    getWhiteListOutMessage.chat_id = chat_id

                    obj, _ = getWhiteListOutMessage.to_json_obj()
                    self.send(obj)

            NandboxClient.InternalWebSocket.api = nandboxAPI()

            NandboxClient.InternalWebSocket.send(json.dumps(auth_object))

        def on_message(self, ws, message):
            NandboxClient.log.info("INTERNAL: ONMESSAGE")

            dictionary = json.loads(message)

            NandboxClient.log.info(f"{Utils.format_date(datetime.datetime.now())} >>>>>>>>> Update Obj : {message}")
            # print(
            #     f'{CRED} {Utils.format_date(datetime.datetime.now())} <<<<<<<<< Update Obj : {message} {CEND}')

            method = str(dictionary[NandboxClient.KEY_METHOD])

            if method is not None:
                NandboxClient.log.info(f"method: {method}")
                if method == "TOKEN_AUTH_OK":
                    print("Authenticated!")
                    NandboxClient.log.info("Authenticated!")
                    NandboxClient.BOT_ID = str(dictionary[NandboxClient.InternalWebSocket.KEY_ID])
                    print(f"====> Your Bot Id is : {NandboxClient.BOT_ID}")
                    print(f"====> Your Bot Name is : {str(dictionary[NandboxClient.InternalWebSocket.KEY_NAME])}")
                    NandboxClient.log.info(f"====> Your Bot Id is : {NandboxClient.BOT_ID}")
                    NandboxClient.log.info(
                        f"====> Your Bot Name is : {str(dictionary[NandboxClient.InternalWebSocket.KEY_NAME])}")

                    if NandboxClient.InternalWebSocket.pingThread is not None:
                        try:
                            NandboxClient.InternalWebSocket.pingThread.interrupted = True
                        except Exception as e:
                            NandboxClient.log.error(e)

                    ping_thread = NandboxClient.InternalWebSocket.PingThread()
                    ping_thread.name = "PingThread"
                    ping_thread.start()
                    self.callback.on_connect(self.api)
                    return
                elif method == "message":
                    incoming_message = IncomingMessage(dictionary)
                    self.callback.on_receive(incoming_message)
                    return
                elif method == "scheduledMessage":
                    incoming_schedule_message = IncomingMessage(dictionary)
                    self.callback.on_schedule_message(incoming_schedule_message)
                    return
                elif method == "chatMenuCallback":
                    chat_menu_callback = ChatMenuCallback(dictionary)
                    self.callback.on_chat_menu_callback(chat_menu_callback)
                    return
                elif method == "inlineMessageCallback":
                    inline_message_callback = InlineMessageCallback(dictionary)
                    self.callback.on_inline_message_callback(inline_message_callback)
                    return
                elif method == "inlineSearch":
                    inline_search = InlineSearch(dictionary)
                    self.callback.on_inline_search(inline_search)
                    return
                elif method == "messageAck":
                    msg_ack = MessageAck(dictionary)
                    self.callback.on_message_ack_callback(msg_ack)
                    return
                elif method == "userJoinedBot":
                    user = User(dictionary[NandboxClient.InternalWebSocket.KEY_USER])
                    self.callback.on_user_joined_bot(user)
                    return
                elif method == "chatMember":
                    chat_member = ChatMember(dictionary)
                    self.callback.on_chat_member(chat_member)
                    return
                elif method == "myProfile":
                    user = User(dictionary[NandboxClient.InternalWebSocket.KEY_USER])
                    self.callback.on_my_profile(user)
                    return
                elif method == "userDetails":
                    user = User(dictionary[NandboxClient.InternalWebSocket.KEY_USER])
                    self.callback.on_user_details(user)
                    return
                elif method == "chatDetails":
                    chat = Chat(dictionary[NandboxClient.InternalWebSocket.KEY_CHAT])
                    self.callback.on_chat_details(chat)
                    return
                elif method == "chatAdministrators":
                    chat_administrators = ChatAdministrators(dictionary)
                    self.callback.on_chat_administrators(chat_administrators)
                    return
                elif method == "userStartedBot":
                    user = User(dictionary[NandboxClient.InternalWebSocket.KEY_USER])
                    self.callback.user_started_bot(user)
                    return
                elif method == "userStoppedBot":
                    user = User(dictionary[NandboxClient.InternalWebSocket.KEY_USER])
                    self.callback.user_stopped_bot(user)
                    return
                elif method == "userLeftBot":
                    user = User(dictionary[NandboxClient.InternalWebSocket.KEY_USER])
                    self.callback.user_left_bot(user)
                    return
                elif method == "blacklist":
                    blacklist = BlackList(dictionary)
                    self.callback.on_black_list(blacklist)
                    return
                elif method == "whitelist":
                    whitelist = WhiteList(dictionary)
                    self.callback.on_white_list(whitelist)
                    return
                elif method == "permanentUrl":
                    permanent_url = PermanentUrl(dictionary)
                    self.callback.permanent_url(permanent_url)
                    return
                else:
                    self.callback.on_receive_obj(dictionary)
                    return
            else:
                error = str(dictionary[NandboxClient.KEY_ERROR])
                NandboxClient.log.error(f"Error : {error}")

        def on_error(self, ws, error):
            NandboxClient.log.error("INTERNAL: ONERROR")
            # print("INTERNAL: ONERROR")
            NandboxClient.log.error(f"Error due to : {error} On : {Utils.format_date(datetime.datetime.now())}")
            # print(f"Error due to : {str(error)} On : {Utils.format_date(datetime.datetime.now())}")
