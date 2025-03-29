import os
import telebot
import logging
import argparse
import traceback
from utils import path
from utils import gsheet
from telebot import types
from utils import send_text
from utils import busca_id_bot
from dotenv import load_dotenv
from utils import get_json_list
from utils import prepare_paths
from send_flashscore import get_match_ok

load_dotenv()

path_result, path_cron, path_csv, path_json, path_html = prepare_paths('envio_telegram.log') # noqa

parser = argparse.ArgumentParser(description="Envia Partidos Telegram, Sheets")
parser.add_argument('file', type=str, help='Archivo de Partidos Flashscore')
parser.add_argument('--cron', action='store_true', help="Programar")

cron = True
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID').split(',')


def process_match(bot_regs, bot, match):
    link = match['url']
    id = match['id']
    row = busca_id_bot(bot_regs, id)
    if row:
        bot_reg = bot_regs[row - 1]
        if not bot_reg:
            return
        home = bot_reg[3]
        away = bot_reg[4]
        # resultado = bot_reg[5]
        apuesta = bot_reg[6]
        apostar = 'OK' in apuesta
        if apostar:
            msj = get_match_ok(match, apuesta, '')
            logging.info(f'{msj}')
            # logging.info(f'{id} -> {msj}')
            markup = types.InlineKeyboardMarkup()
            if link:
                link_boton = types.InlineKeyboardButton('Apostar', url=link) # noqa
                markup.add(link_boton)
            for chat_id in TELEGRAM_CHAT_ID:
                send_text(
                    bot,
                    chat_id,
                    msj,
                    markup
                )
        else:
            logging.info(f'{id} -> {home} - {away}, No apostar')
    else:
        logging.info(f'{id} No encontrado')
        return


def send_matches(path_matches: str):
    try:
        matches = get_json_list(path_matches)

        wks = gsheet('Bot')
        bot_regs = wks.get_all_values(returnas='matrix')
        bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

        for match in matches:
            process_match(bot_regs, bot, match)

    except Exception as e:
        logging.error(f'Error: {e}')
        traceback.print_exc()
    except KeyboardInterrupt:
        print('\nFin...')


if __name__ == '__main__':
    args = parser.parse_args()
    filename = args.file
    date = filename.split('.')[0][:8]
    path_file = path(path_result, date, 'ok', filename)

    file = r"C:\Users\Robot\Documents\markiv\result\20250325\ok\202503251245.json" # noqa

    if not os.path.exists(path_file):
        logging.info(f'Archivo {path_file} no existe')
        exit(1)

    send_matches(path_file)
