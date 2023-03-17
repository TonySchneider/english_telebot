import os
import sys

from helpers.loggers import get_logger
from helpers.multiple_languages import load_dictionary

from core.english_bot_user import EnglishBotUser
from core.english_bot_telebot_extension import EnglishBotTelebotExtension

from wrappers.db_wrapper import DBWrapper

logger = get_logger(__file__)

try:
    TOKEN = os.environ["BOT_TOKEN"]
    MYSQL_HOST = os.environ["MYSQL_HOST"]
    MYSQL_USER = os.environ["MYSQL_USER"]
    MYSQL_PASS = os.environ["MYSQL_PASS"]
except KeyError:
    logger.error("Please set the environment variables: MYSQL_USER, MYSQL_PASS, BOT_TOKEN")
    sys.exit(1)

bot = EnglishBotTelebotExtension(TOKEN)
db_connector = DBWrapper(host=MYSQL_HOST, mysql_user=MYSQL_USER, mysql_pass=MYSQL_PASS, database='english_bot')

dictionary = load_dictionary(lang="he")


if __name__ == '__main__':
    try:
        logger.info('Starting bot... Press CTRL+C to quit.')

        EnglishBotUser.load_users_and_global_instances(bot, db_connector)

        bot.init_handlers()
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
