from helpers.loggers import get_logger

logger = get_logger(__file__)


class BaseBotUser:
    active_users = {}

    @staticmethod
    def get_user_by_chat_id(chat_id: int):
        return BaseBotUser.active_users.get(chat_id)

    def __init__(self, chat_id: int, db_connector, global_bot):
        self.chat_id = chat_id
        self.messages = []
        self.global_bot = global_bot
        self.db_connector = db_connector
        self.chat_paused = False

        BaseBotUser.active_users[chat_id] = self

    def is_locked(self):
        return self.chat_paused

    def pause_chat(self):
        logger.debug(f"Pausing chat (chat_id={self.chat_id})")
        self.chat_paused = True

    def resume_sender(self):
        logger.debug(f"Resuming chat (chat_id={self.chat_id})")
        self.chat_paused = False

    def close(self):
        logger.debug(f"Closing chat (chat_id={self.chat_id})")
        pass
