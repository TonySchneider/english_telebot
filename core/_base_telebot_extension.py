
from typing import Union, Optional, List

from telebot import TeleBot, types
from telebot.async_telebot import REPLY_MARKUP_TYPES

from helpers.loggers import get_logger
from core.english_bot_user import EnglishBotUser

logger = get_logger(__file__)


class BaseTelebotExtension(TeleBot):

    def __init__(self, token: str):
        super().__init__(token)
        self.token = token

    def send_message(
            self, chat_id: Union[int, str], text: str,
            parse_mode: Optional[str] = None,
            entities: Optional[List[types.MessageEntity]] = None,
            disable_web_page_preview: Optional[bool] = None,
            disable_notification: Optional[bool] = None,
            protect_content: Optional[bool] = None,
            reply_to_message_id: Optional[int] = None,
            allow_sending_without_reply: Optional[bool] = None,
            reply_markup: Optional[REPLY_MARKUP_TYPES] = None,
            timeout: Optional[int] = None) -> types.Message:
        logger.debug(f"Sending message to '{chat_id}'. (text- '{text}')")

        msg_obj = super().send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)

        logger.debug(f"Storing message that was sent. id - {msg_obj.message_id}")

        user = EnglishBotUser.get_user_by_chat_id(chat_id)
        user.messages.append(msg_obj.message_id)

        return msg_obj

    def clean_chat(self, chat_id):
        logger.debug(f"Cleaning chat {chat_id}")
        user = EnglishBotUser.get_user_by_chat_id(chat_id)

        try:
            while user.messages:
                msg_id = user.messages.pop(0)

                try:
                    logger.debug(f"Deleting message id - '{msg_id}'")
                    self.delete_message(chat_id=chat_id, message_id=msg_id)
                except Exception as e:
                    logger.warning(f"Didn't manage to delete message {msg_id} id. Error (debug level):")
                    logger.debug(e.__str__())

        except AssertionError as e:
            logger.warning(f"Second Cleaning | assertion error - {e.__str__()}")
