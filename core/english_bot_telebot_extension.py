import random
from typing import Mapping

from helpers.loggers import get_logger
from core.english_bot_user import EnglishBotUser
from helpers.translations import get_translations
from core._base_telebot_extension import BaseTelebotExtension

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = get_logger(__file__)


class EnglishBotTelebotExtension(BaseTelebotExtension):
    MIN_WORDS_PER_USER = 4
    MAX_WORDS_PER_USER = 100

    def __init__(self, token: str):
        super(EnglishBotTelebotExtension, self).__init__(token)
        self.word_sender = None

    def show_menu(self, chat_id):
        logger.debug(f"showing menu for '{chat_id}'")

        menu_buttons = {
            '1': 'הוסף מילה חדשה',
            '2': 'הפעל/עצור שליחה אוטומטית',
            '3': 'רשימת מילים ואפשרות מחיקה',
            '4': 'שנה זמן המתנה בין מילים',
            '5': 'הצג רשימת מילים לשינון',
            '6': 'עזרה'
        }

        reply_markup = InlineKeyboardMarkup()
        options = [InlineKeyboardButton(button_text, callback_data=f'menu:{button_id}') for button_id, button_text in
                   menu_buttons.items()]

        for option in options:
            reply_markup.row(option)

        self.send_message(chat_id, "תפריט", reply_markup=reply_markup)

    def show_wordlist(self, chat_id, word_range: list):
        logger.debug(f"showing wordlist for '{chat_id}'")
        user = EnglishBotUser.get_user_by_chat_id(chat_id)
        en_words = user.get_user_sorted_words()[word_range[0]:word_range[1]]

        cross_icon = u"\u274c"

        words_buttons = [InlineKeyboardButton(en_word, callback_data=f'word:{en_word}') for en_word in en_words]
        cross_icon_buttons = [InlineKeyboardButton(cross_icon, callback_data=f'delete_word:{en_word}|{word_range}')
                              for en_word in en_words]

        reply_markup = InlineKeyboardMarkup()

        for button_index in range(len(words_buttons)):
            reply_markup.row(words_buttons[button_index], cross_icon_buttons[button_index])

        reply_markup.row(InlineKeyboardButton("חזרה לתפריט הקודם", callback_data=f'exit-to-word-range'))

        self.send_message(chat_id, "רשימת המילים:", reply_markup=reply_markup)

    def show_existing_words_to_practice(self, chat_id):
        table = "```\n"

        for en_word, details in sorted(EnglishBotUser.get_user_by_chat_id(chat_id).user_translations.items()):
            table += f"{en_word}" + " - " + f"{'/'.join(details['he_words'])}\n"
        table += "```\n"

        reply_markup = InlineKeyboardMarkup()
        reply_markup.row(InlineKeyboardButton("חזרה לתפריט הראשי", callback_data=f'exit-to-main-menu'))

        self.send_message(chat_id, table, reply_markup=reply_markup, parse_mode='MarkdownV2')

    def show_existing_words_with_their_priorities(self, chat_id):
        table = "```\n"

        for en_word, details in sorted(EnglishBotUser.get_user_by_chat_id(chat_id).user_translations.items()):
            table += f"{en_word}" + " - " + f"{details['usages']}\n"
        table += "```\n"

        reply_markup = InlineKeyboardMarkup()
        reply_markup.row(InlineKeyboardButton("חזרה לתפריט הראשי", callback_data=f'exit-to-main-menu'))

        self.send_message(chat_id, table, reply_markup=reply_markup, parse_mode='MarkdownV2')

    def show_word_ranges(self, chat_id):
        user = EnglishBotUser.get_user_by_chat_id(chat_id)

        en_words = user.get_user_sorted_words()

        # calculate words ranges to split the buttons
        divide_by = 20
        ranges = [[start, start + divide_by] for start in range(0, len(en_words), divide_by)]
        ranges[-1][1] -= (divide_by - len(en_words) % divide_by)

        ranges_buttons = [InlineKeyboardButton(f" {en_words[words_range[0]][:1]}-{en_words[words_range[1] - 1][:1]} רשימת מילים ",
                                               callback_data=f'range_words:{words_range}') for words_range in ranges]
        reply_markup = InlineKeyboardMarkup()
        for button_index in range(len(ranges_buttons)):
            reply_markup.row(ranges_buttons[button_index])

        reply_markup.row(InlineKeyboardButton("חזרה לתפריט הראשי", callback_data=f'exit-to-main-menu'))

        logger.debug(f"showing words ranges for '{chat_id}'")
        self.send_message(chat_id, "בחר באחת הרשימות:", reply_markup=reply_markup)

    @staticmethod
    def assertions_before_addition_a_new_word(new_word: str, user: EnglishBotUser):
        result_message = None
        if new_word in user.user_translations.keys():
            result_message = f'המילה {new_word} כבר קיימת במערכת.'

        try:
            assert new_word
            assert new_word.replace(' ', '').isalpha()
            assert len(new_word) < 46
        except AssertionError:
            result_message = 'המילה צריכה להכיל רק אותיות ולהיות לא יותר מ45 תווים'

        return result_message

    def add_new_word_to_db(self, message):
        chat_id = message.chat.id
        user = EnglishBotUser.get_user_by_chat_id(chat_id)
        user.messages.append(message.message_id)

        new_word = message.text.lower()

        logger.debug(f"The provided word - '{new_word}'. Will check the input string...")

        assertion_result = self.assertions_before_addition_a_new_word(new_word, user)

        if assertion_result:
            self.clean_chat(chat_id)
            self.send_message(chat_id, assertion_result)
            self.resume_user_word_sender(chat_id)
            return

        extracted_translations = get_translations(new_word)
        logger.debug(f"Got these translations - '{extracted_translations}' for the word '{new_word}'")

        translations = [{'en_word': new_word, 'he_word': translation,
                         'chat_id': chat_id} for translation in extracted_translations]
        if not translations:
            self.send_message(chat_id, 'המערכת לא הצליחה למצוא תרגום למילה המבוקשת')
            return

        insertion_status = user.update_translations(translations)

        self.clean_chat(chat_id)

        if insertion_status:
            he_words = ", ".join([item['he_word'] for item in translations])
            self.send_message(chat_id, f'המילה {new_word} נוספה בהצלחה. תרגום המילה: {he_words}')
        else:
            self.send_message(chat_id, 'המערכת לא הצליחה להוסיף את המילה המבוקשת, שאל את המפתחים')

        self.resume_user_word_sender(chat_id)

    def change_waiting_time(self, message):
        chat_id = message.chat.id
        user = EnglishBotUser.get_user_by_chat_id(chat_id)
        user.messages.append(message.message_id)

        new_time = message.text
        logger.debug(f"Changing time to '{new_time}'. | chat_id - '{chat_id}'")

        try:
            assert new_time, "The object is empty"
            assert new_time.isnumeric(), "The object is not numeric"

            new_time = int(new_time)
            assert new_time <= 24 * 60, "The number is more than 24 hours"

            self.clean_chat(chat_id)
            update_status = user.update_delay_time(new_time)
            if update_status:
                self.send_message(chat_id, f'זמן ההמתנה שונה ל-{new_time} דקות')
            else:
                self.send_message(chat_id, 'המערכת לא הצליחה לשנות את זמן ההמתנה')
        except AssertionError as e:
            logger.error(
                f"There was an assertion error. Error - '{e}'. | method - 'change_waiting_time' | message.text - '{new_time}'")
        finally:
            self.resume_user_word_sender(chat_id)

    def send_new_word(self, chat_id):
        user = EnglishBotUser.get_user_by_chat_id(chat_id)

        en_words, priorities = user.get_sorted_words_and_their_priority()

        chosen_en_word = random.choices(en_words, weights=priorities, k=1)[0]
        en_words.remove(chosen_en_word)

        chosen_he_word = random.choice(user.user_translations[chosen_en_word]['he_words'])

        additional_random_en_words = []
        while len(additional_random_en_words) < 3:
            current_random_choice = random.choice(en_words)
            if current_random_choice not in additional_random_en_words:
                additional_random_en_words.append(current_random_choice)

        random_he_words = []
        while additional_random_en_words:
            current_en_word = additional_random_en_words.pop()
            current_random_he_word = random.choice(user.user_translations[current_en_word]['he_words'])
            random_he_words.append(current_random_he_word)

        random_he_words.append(chosen_he_word)

        random.shuffle(random_he_words)

        reply_markup = InlineKeyboardMarkup()
        options = [InlineKeyboardButton(button_he_word,
                                        callback_data=f'c:{chosen_he_word}|{button_he_word}') for
                   button_he_word in random_he_words]

        for option in options:
            reply_markup.row(option)

        self.clean_chat(chat_id)

        self.send_message(chat_id, f'בחר את התרגום של {chosen_en_word}', reply_markup=reply_markup)
        logger.debug(f"sent word '{chosen_en_word}' to chat id - '{chat_id}'")

        # increase usage of the chosen word
        user.increase_word_usages(chosen_en_word)

        self.pause_user_word_sender(chat_id)

    def delete_word(self, chat_id, en_word):
        user = EnglishBotUser.get_user_by_chat_id(chat_id)

        delete_status = user.delete_word(en_word)

        self.clean_chat(chat_id)
        if delete_status:
            self.send_message(chat_id, f"המילה {en_word} נמחקה בהצלחה")
            if user.word_sender_active and user.num_of_words < 4:
                self.send_message(chat_id,
                                  f'שליחת המילים האוטומטית הופסקה, מספר המילים לא מספיקה ({user.num_of_words})')
        else:
            self.send_message(chat_id, "המערכת נתקלה בתקלה, המילה המבוקשת לא נמחקה.")

    def infinity_polling(self, **kwargs):
        active_users: "Mapping[int, EnglishBotUser]" = EnglishBotUser.active_users

        logger.debug("Activating users...")
        for chat_id, active_user in active_users.items():
            if active_user.word_sender_active:
                active_user.activate_word_sender()

        super().infinity_polling(timeout=10, long_polling_timeout=5, **kwargs)

    @staticmethod
    def pause_user_word_sender(chat_id):
        active_users: "Mapping[int, EnglishBotUser]" = EnglishBotUser.active_users

        active_users[chat_id].pause_sender()

    @staticmethod
    def resume_user_word_sender(chat_id):
        active_users: "Mapping[int, EnglishBotUser]" = EnglishBotUser.active_users

        active_users[chat_id].resume_sender()

    def close(self):
        # TODO: check regarding the stop forcing

        for chat_id, active_user in EnglishBotUser.active_users.items():
            active_user.close()
            self.clean_chat(chat_id)
