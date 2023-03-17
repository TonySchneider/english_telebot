import time

from helpers.loggers import get_logger
from core.word_sender import WordSender

logger = get_logger(__file__)


class EnglishBotUser:
    active_users = {}

    @staticmethod
    def get_user_by_chat_id(chat_id: int):
        return EnglishBotUser.active_users.get(chat_id)

    def __init__(self, chat_id: int, db_connector, global_bot, word_sender_active: bool = False, delay_time: int = 20,
                 user_translations: list = None):
        self.chat_id = chat_id
        self.word_sender = None
        self.messages = []
        self.word_sender_active = word_sender_active
        self.global_bot = global_bot
        self.delay_time = delay_time
        self.user_translations = self.convert_db_translation_into_a_dict(user_translations) if user_translations else {}
        self.db_connector = db_connector
        self.word_sender_paused = False

        EnglishBotUser.active_users[chat_id] = self

    @property
    def num_of_words(self):
        return len(self.user_translations.keys())

    @staticmethod
    def convert_db_translation_into_a_dict(translations: list) -> dict:
        trans_as_a_dict = {}
        for translation in translations:
            if translation['en_word'] in trans_as_a_dict.keys():
                trans_as_a_dict[translation['en_word']]['he_words'].append(translation['he_word'])
            else:
                trans_as_a_dict[translation['en_word']] = {
                    'he_words': [translation['he_word']],
                    'usages': 0
                }
        return trans_as_a_dict

    def increase_word_usages(self, en_word: str):
        self.user_translations[en_word]['usages'] += 1
        logger.debug(f"Increased the number of usages of the word - '{en_word}'."
                     f" The current value is {self.user_translations[en_word]['usages']}.")

    def get_sorted_words_and_their_priority(self) -> tuple:
        sorted_words = []
        priorities = []
        for word, details in sorted(self.user_translations.items()):
            sorted_words.append(word)
            priorities.append(details['usages'])

        priorities = [1.0 / (priority + 1) for priority in priorities]
        return sorted_words, priorities

    def get_user_sorted_words(self):
        return sorted(self.user_translations.keys())

    def new_words_worker(self):
        got_exception = 0

        while True:
            if self.word_sender.is_stopped:
                logger.debug(f"The word sender of chat id '{self.chat_id}' was stopped")
                break

            try:
                self.global_bot.send_new_word(self.chat_id)
            # TODO: change this exception to something better
            except Exception as e:
                logger.debug(f"Got exception - {e}")
                if got_exception >= 3:
                    raise Exception(e)

                got_exception += 1
                continue

            got_exception = 0
            while self.word_sender_paused:
                if self.word_sender.is_stopped:
                    break
                time.sleep(1)

            logger.debug(f"WordSender | Sleeping {self.delay_time} minutes")
            time.sleep(self.delay_time * 60)

    def is_locked(self):
        return self.word_sender_paused

    def activate_word_sender(self):
        logger.debug(f"Activating word sender (chat_id={self.chat_id})")

        self.word_sender = WordSender(chat_id=self.chat_id,
                                      delay_time=self.delay_time,
                                      target=self.new_words_worker)
        self.word_sender.start()

        # TODO: change the following to celery task
        if not self.word_sender_active:
            self.db_connector.update_field(table_name='users', field='auto_send_active', condition_field='chat_id',
                                           condition_value=self.chat_id, value=True)
            self.word_sender_active = True

    def pause_sender(self):
        logger.debug(f"Pausing word sender (chat_id={self.chat_id})")
        self.word_sender_paused = True

    def resume_sender(self):
        logger.debug(f"Resuming word sender (chat_id={self.chat_id})")
        self.word_sender_paused = False

    def deactivate_word_sender(self):
        logger.debug(f"Deactivating word sender (chat_id={self.chat_id})")

        # change the status in DB
        self.db_connector.update_field(table_name='users', field='auto_send_active', condition_field='chat_id',
                                       condition_value=self.chat_id, value=False)

        # change in the object (mem)
        self.word_sender_active = False

        # stop the thread
        if self.word_sender:
            self.word_sender.stop()
            self.word_sender = None

    def delete_word(self, en_word: str) -> bool:
        logger.debug(f"Deleting word ({en_word})")

        delete_status = self.db_connector.delete_by_field(table_name='translations', field_condition='en_word',
                                                          value_condition=en_word, second_field_condition='chat_id',
                                                          second_value_condition=self.chat_id)

        if delete_status:
            self.user_translations.pop(en_word)

        return delete_status

    def update_delay_time(self, new_time: int) -> bool:
        update_status = self.db_connector.update_field(table_name='users', condition_field='chat_id',
                                                       condition_value=self.chat_id, field='delay_time',
                                                       value=new_time)

        if update_status:
            self.delay_time = new_time

        return update_status

    def update_translations(self, translations) -> bool:
        translations_insertion_status = self.db_connector.insert_multiple_rows(table_name='translations',
                                                                               keys_values=translations)

        usages_insertion_status = self.db_connector.insert_row(table_name='usages',
                                                               keys_values={'en_word': translations[0]['en_word']})

        if translations_insertion_status and usages_insertion_status:
            self.user_translations.update(self.convert_db_translation_into_a_dict(translations))

        return translations_insertion_status and usages_insertion_status

    def close(self):
        if self.word_sender:
            self.word_sender.stop()

        # logger.debug(f"Updating usages table for user - '{self.chat_id}'...")
        # self.db_connector.update_multiple_rows(table_name='usages',
        #                                        keys_values={en_word: details['usages']
        #                                                     for en_word, details in self.user_translations.items()})
