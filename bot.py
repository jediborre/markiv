import os
import re
import sys
import json
import telebot
import logging
# from model.db import Base
# from model import Match
from catalogos import paises
from dotenv import load_dotenv
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, scoped_session
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
matches = {}
pais_matches = {}

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


@bot.message_handler(func=lambda message: True)
def handle_(message):
    global player_stats
    pattern = r"^#\d{1,}$"
    msj = message.text
    if msj:
        msj_l = msj.lower()
        if msj_l == 'paises':
            str_msj = []
            pais_cuenta = []
            for pais in pais_matches:
                pais_cuenta.append([pais, len(pais_matches[pais])])
            pais_cuenta_sorted = sorted(
                pais_cuenta,
                key=lambda x: x[1],
                reverse=True
            )
            for pais, n in pais_cuenta_sorted:
                str_msj.append(f'{pais} [{n}]')
            bot.reply_to(message, '\n'.join(str_msj))
        elif msj_l in paises:
            pais = msj_l
            if pais in pais_matches:
                str_msj = []
                matches = pais_matches[pais]
                for match in matches:
                    str_msj.append(f'#{match["id"]} {match["time"]} {match["liga"]} {match["home"]} - {match["away"]}') # noqa
                bot.reply_to(message, '\n'.join(str_msj))
            else:
                bot.reply_to(message, f'No hay partidos en {pais}')
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
    args = sys.argv[1:]
    if len(args) > 0:
        db_file = args[0]
        match_file = os.path.join(result_path, f'{db_file}.json')
        pais_match_file = os.path.join(result_path, f'{db_file}_pais.json')
        if os.path.exists(match_file) and os.path.exists(pais_match_file):
            execute = True
            try:
                pais_matches = json.load(open(pais_match_file))
            except Exception as e:
                execute = False
                print(e)
                print(match_file)
            try:
                pais_matches = json.load(open(pais_match_file))
                start_bot()
            except Exception as e:
                execute = False
                print(e)
                print(pais_match_file)
            if execute:
                start_bot()
        else:
            print('Archivo de base no existe, lo escribiste bien?')
    else:
        print('Falta expecificar nombre de archivo sqlite')
