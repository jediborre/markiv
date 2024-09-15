import os
import re
import sys
import telebot
import logging
from model.db import Base
from model import Match
from catalogos import paises
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from requests.exceptions import ConnectionError, ReadTimeout

load_dotenv()

DB_FILE = os.getenv('DB_FILE')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID').split(',')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
filename = 'partidos_totalcorner'
script_path = os.path.dirname(os.path.abspath(__file__))
result_path = os.path.join(script_path, 'result')
if not os.path.exists(result_path):
    os.makedirs(result_path)
os.chdir(result_path)

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


@bot.message_handler(func=lambda message: True)
def handle_(message):
    global player_stats
    pattern = r"^#\d{1,}$"
    msj = message.text
    if msj:
        if msj.lower() in paises:
            bot.reply_to(message, msj)
        else:
            if re.fullmatch(pattern, msj):
                bot.reply_to(message, f'id {msj}')
            else:
                bot.reply_to(message, f'Pais no reconocido "{msj}"')
    else:
        bot.reply_to(message, 'Instruccion vacia')


def start_bot():
    global bot
    logging.info('Mark IV BOT')
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=10)
    except (ConnectionError, ReadTimeout):
        sys.stdout.flush()
        os.execv(sys.argv[0], sys.argv)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Fin...")
        bot.stop_polling()
    else:
        bot.infinity_polling(timeout=20, long_polling_timeout=10)
    finally:
        try:
            bot.stop_polling()
        except Exception:
            pass


if __name__ == "__main__":
    start_bot()
