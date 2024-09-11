import os
import sys
import telebot
import logging
from dotenv import load_dotenv
from model.db import Base
from model import Match
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
def handle_all_messages(message):
    global player_stats
    msj = message.text
    if ' v ' in msj:
        home, away = msj.split(' v ')
        home = home.strip()
        away = away.strip()
        bot.reply_to(message, f'{home} v {away}.')
    else:
        bot.reply_to(message, msj)


def main():
    global DB_FILE
    engine = create_engine(f'sqlite:///{DB_FILE}')
    Base.metadata.create_all(engine)
    Session = scoped_session(sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False
    ))
    matches = Match.get_all(Session)
    print(f'Extrayendo {len(matches)} partidos.')
    for match in matches:
        match


def start_bot():
    global bot
    logging.info('Ultron BOT')
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
