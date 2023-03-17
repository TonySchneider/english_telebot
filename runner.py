import os
import sys
import time

from helpers.loggers import get_logger
from helpers.multiple_languages import load_dictionary

from wrappers.db_wrapper import DBWrapper

from core.english_bot_user import EnglishBotUser
from core.english_bot_telebot_extension import EnglishBotTelebotExtension

logger = get_logger(__file__)

try:
    TOKEN = os.environ["BOT_TOKEN"]
    MYSQL_HOST = os.environ["MYSQL_HOST"]
    MYSQL_USER = os.environ["MYSQL_USER"]
    MYSQL_PASS = os.environ["MYSQL_PASS"]
except KeyError:
    logger.error("Please set the environment variables: MYSQL_USER, MYSQL_PASS, BOT_TOKEN")
    sys.exit(1)

db_connector = DBWrapper(host=MYSQL_HOST, mysql_user=MYSQL_USER, mysql_pass=MYSQL_PASS, database='english_bot')
bot = EnglishBotTelebotExtension(TOKEN)
dictionary = load_dictionary(lang="he")


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id
    current_user: "EnglishBotUser" = EnglishBotUser.get_user_by_chat_id(chat_id)

    data = call.data
    if data.startswith("menu:"):
        button_id = data.replace('menu:', '')
        if not current_user.is_locked():
            if button_id == '1':
                if current_user.num_of_words >= bot.MAX_WORDS_PER_USER:
                    bot.clean_chat(chat_id)
                    bot.send_message(chat_id, 'הגעת לכמות מילים המקסימלית שניתן להוסיף (100 מילים).')
                else:
                    bot.pause_user_word_sender(chat_id)
                    bot.clean_chat(chat_id)

                    callback_msg = bot.send_message(chat_id, 'שלח את המילה החדשה')
                    bot.register_next_step_handler(callback_msg, bot.add_new_word_to_db)
            elif button_id == '2':
                current_sender_status = current_user.word_sender_active
                if not current_sender_status:
                    if current_user.num_of_words >= bot.MIN_WORDS_PER_USER:
                        current_user.activate_word_sender()
                        bot.send_message(chat_id, 'שליחת המילים האוטומטית הופעלה')
                    else:
                        bot.send_message(chat_id, 'לא נוספו 4 מילים')
                elif current_sender_status:
                    current_user.deactivate_word_sender()
                    bot.send_message(chat_id, 'שליחת המילים האוטומטית הופסקה')
            elif button_id == '3':
                bot.pause_user_word_sender(chat_id)
                bot.clean_chat(chat_id)

                bot.show_word_ranges(chat_id)
            elif button_id == '4':
                bot.pause_user_word_sender(chat_id)

                callback_msg = bot.send_message(chat_id, 'שלח מספר דקות לשינוי זמן ההמתנה')
                bot.register_next_step_handler(callback_msg, bot.change_waiting_time)
            elif button_id == '5':
                bot.pause_user_word_sender(chat_id)
                bot.clean_chat(chat_id)

                bot.show_existing_words_to_practice(chat_id)
            elif button_id == '6':
                bot.send_message(chat_id, 'מה אתה צריך????!!')
        else:
            logger(f"The user trying to press on button {button_id} but the chat is locked")

    elif data.startswith("c:"):
        logger.debug(f"comparison words for '{chat_id}'")

        button_callback = data.replace('c:', '')
        he_word, chosen_he_word = button_callback.split('|')

        bot.clean_chat(chat_id)
        prefix = f' המילה הבאה תישלח בעוד {current_user.delay_time} דקות.'

        if he_word == chosen_he_word:
            bot.send_message(chat_id, f'נכון, כל הכבוד.' + prefix)
            time.sleep(1)
        else:
            bot.send_message(chat_id, f'טעות, התרגום הנכון זה - "{he_word}."' + prefix)
            time.sleep(1)

        bot.resume_user_word_sender(chat_id)

    elif data.startswith("range_words:"):
        button_callback = data.replace('range_words:', '')

        bot.clean_chat(chat_id)
        bot.show_wordlist(chat_id, eval(button_callback))

    elif data.startswith("delete_word:"):
        button_callback = data.replace('delete_word:', '')
        chosen_word, last_menu_range = button_callback.split('|')
        bot.delete_word(chat_id, chosen_word)

        bot.show_wordlist(chat_id, eval(last_menu_range))

    elif data.startswith("exit-to-main-menu"):
        bot.clean_chat(chat_id)

        bot.show_menu(chat_id)
        bot.resume_user_word_sender(chat_id)

    elif data.startswith("exit-to-word-range"):
        bot.clean_chat(chat_id)

        bot.show_word_ranges(chat_id)


@bot.message_handler(commands=['start'])
def start_the_bot(message):
    chat_id = message.chat.id
    current_user: "EnglishBotUser" = EnglishBotUser.get_user_by_chat_id(chat_id)

    if current_user:
        current_user.messages.append(message.message_id)
        bot.show_menu(chat_id)
    else:
        EnglishBotUser(chat_id=chat_id,
                       db_connector=db_connector,
                       global_bot=bot)
        db_connector.insert_row(table_name='users', keys_values={'chat_id': chat_id})

        bot.show_menu(chat_id)
        bot.send_message(chat_id, 'אנא הוסף לפחות 4 מילים על מנת שהמערכת תוכל להתחיל לשלוח מילים בצורה אוטומטית')


@bot.message_handler(func=lambda message: message.text in ['שלח-עדיפויות', '/priorities'])
def new_word_command(message):
    chat_id = message.chat.id
    current_user: "EnglishBotUser" = EnglishBotUser.get_user_by_chat_id(chat_id)

    if current_user:
        current_user.messages.append(message.message_id)

    if not current_user.is_locked():
        bot.clean_chat(chat_id)
        bot.show_existing_words_with_their_priorities(chat_id)


@bot.message_handler(func=lambda message: message.text in ['שלח-מילה', '/send'])
def new_word_command(message):
    chat_id = message.chat.id
    current_user: "EnglishBotUser" = EnglishBotUser.get_user_by_chat_id(chat_id)

    if current_user:
        current_user.messages.append(message.message_id)

    if not current_user.is_locked():
        bot.send_new_word(message.chat.id)


@bot.message_handler(func=lambda message: message.text in ['תפריט', '/menu'])
def new_word_command(message):
    chat_id = message.chat.id
    current_user: "EnglishBotUser" = EnglishBotUser.get_user_by_chat_id(chat_id)

    if current_user:
        current_user.messages.append(message.message_id)

    if not current_user.is_locked():
        bot.clean_chat(chat_id)
        bot.show_menu(chat_id)


@bot.message_handler(func=lambda message: message.text)
def catch_every_user_message(message):
    logger.debug(f"catching user message ({message.text})")
    chat_id = message.chat.id
    current_user: "EnglishBotUser" = EnglishBotUser.get_user_by_chat_id(chat_id)

    if current_user:
        current_user.messages.append(message.message_id)


if __name__ == '__main__':
    try:
        logger.info('Starting bot... Press CTRL+C to quit.')

        logger.debug(f"Initializing users")
        fetched_users = db_connector.get_all_values_by_field(table_name='users_extended')
        for user in fetched_users:
            user_translations = db_connector.get_all_values_by_field(table_name='translations',
                                                                     condition_field='chat_id',
                                                                     condition_value=user['chat_id'])

            EnglishBotUser(chat_id=user['chat_id'],
                           word_sender_active=eval(user['auto_send_active']),
                           delay_time=user['delay_time'],
                           user_translations=user_translations,
                           db_connector=db_connector,
                           global_bot=bot)

        bot.infinity_polling()
    except KeyboardInterrupt:
        print('Quitting... (CTRL+C pressed)\n Exits...')
    except Exception as e:  # Catch-all for unexpected exceptions, with stack trace
        print(f"Unhandled exception occurred!\n Error: '{e}'\nAborting...")
    finally:
        print('Existing...')

        bot.close()
        db_connector.close_connection()
        sys.exit(0)
