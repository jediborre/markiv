import os
import sys
import logging
import argparse
from web import Web
from utils import path, pathexist
from utils import prepare_paths_ok

url_matches_today = 'https://m.flashscore.com.mx/'

sys.stdout.reconfigure(encoding='utf-8')

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID').split(',')

path_result, path_ok = prepare_paths_ok()

parser = argparse.ArgumentParser(description="Solicita partidos de hoy o mañana de flashscore") # noqa
parser.add_argument('file', type=str, help='Archivo de Partidos Flashscore')
args = parser.parse_args()

if __name__ == '__main__':
    args = parser.parse_args()
    filename = args.file
    path_file = path(path_result, filename.split('.')[0][:8], filename)

    if not pathexist(path_file):
        seguimiento = 1
