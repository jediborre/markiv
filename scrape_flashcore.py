import os
import sys
import pprint # noqa
import telebot
import logging
import argparse
from web import Web
from utils import path
from utils import send_text
from utils import prepare_paths
from parse import get_all_matches
from parse import process_matches
from cron_flashscore import cron_matches
from filtros import get_ligas_google_sheet
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

# https://app.dataimpulse.com/plans/create-new
# https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json

# chrome --remote-debugging-port=9222 --user-data-dir="C:\Log"
# .venv/Scripts/Activate.ps1
# clear;python .\scrape_flashcore.py --over

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID').split(',')

opened_web = False
parser = argparse.ArgumentParser(description="Solicita partidos de hoy o mañana de flashscore") # noqa
parser.add_argument('--today', action='store_true', help="Partidos Hoy")
parser.add_argument('--tomorrow', action='store_true', help="Partidos Mañana")
parser.add_argument('--over', action='store_true', help="Sobreescribir")
args = parser.parse_args()

url_matches_today = 'https://m.flashscore.com.mx/'
url_matches_tomorrow = 'https://m.flashscore.com.mx/?d=1'
path_result, path_cron, path_csv, path_json, path_html = prepare_paths('scrape_flashcore.log') # noqa


def main(hoy=False, overwrite=False):
    global web, path_html
    global path_json, path_html, path_result
    global url_matches_today, url_matches_tomorrow

    today = datetime.today()
    if hoy:
        date = today
        url = url_matches_today
    else:
        tomorrow = (today + timedelta(days=1))
        date = tomorrow
        url = url_matches_tomorrow

    fecha = date.strftime('%Y%m%d')
    fecha_hum = date.strftime('%d %m %Y')
    path_page_matches = path(path_html, f'{fecha}_matches.html') # noqa

    web = Web(multiples=True)
    ligas = get_ligas_google_sheet()
    matches = get_all_matches(
        path_html,
        path_page_matches,
        url,
        web,
        ligas,
        True
    )
    if len(matches) == 0:
        logging.info(f'No hay partidos {fecha}')
        return

    [path_matches, n_matches] = process_matches(
        matches,
        date,
        web,
        path_json,
        path_html,
        path_result,
        overwrite
    )
    if web is not None:
        web.close()
        web.quit()

    cron_matches(path_matches)

    msj = f'Partidos {fecha_hum}\n{n_matches}-{len(matches)}'
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
    for chat_id in TELEGRAM_CHAT_ID:
        send_text(
            bot,
            chat_id,
            msj
        )


if __name__ == "__main__":
    overwrite = args.over
    if args.tomorrow:
        main(False, overwrite)
    else:
        main(True, overwrite)
