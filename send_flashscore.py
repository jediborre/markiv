import os
import logging # noqa
import argparse
import pprint # noqa
import pygsheets
from sheet_utils import get_last_row
from utils import path
from utils import get_json
from dotenv import load_dotenv
from utils import prepare_paths

load_dotenv()

path_result, path_cron, path_csv, path_json, path_html = prepare_paths('envio_flashcore.log') # noqa

parser = argparse.ArgumentParser(description="Envia Partidos Telegram, Sheets")
parser.add_argument('file', type=str, help='Archivo de Partidos Flashscore')

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID').split(',')


def write_sheet_row(wks, row, match):
    #                                                                         Home                Away                VS           Ganador      Ambos Marcan   HandiCap 0/0.5  HandiCap -1  HandiCap -2   Momios FT     Linea de Gol   Roja		Total               Dif Anotaran		Momio GP	Local				Visitante				Goles Esp	Prob %	% L	% V	% A	X2	Asiatico
    # Fecha	Hora	Local	Visitante	AP	RESULTADO	Pais	Liga	1	2	3	4	5	1	2	3	4	5	1	2	3	4	5 Local	Visit	Si	No	         HM	  AM	     HM	  AM	  HM	AM    -3.5	-4.5  1 	2	3	4  L	V	Final    Mensajes  # noqa
    reg = [
        match['id'],
    ]
    wks.update_row(row, reg)


def process_match(wks, match: dict):
    id = match['id']
    pais = match['pais']
    hora = match['hora']
    liga = match['liga']
    home = match['home']
    away = match['away']
    link = match['url']
    logging.info(f'#{id} {hora}|{pais} {liga}| {home} - {away}|{link}')
    row = get_last_row(wks)
    write_sheet_row(wks, row, match)


def send_matches(path_matches: str):
    logging.info(f'MarkIV Envio {path_matches}') # noqa
    try:
        matches = get_json(path_matches)

        gc = pygsheets.authorize(service_file='feroslebosgc.json')
        spreadsheet = gc.open('Mark 4')
        wks = spreadsheet.worksheet_by_title('Bot')

        for match in matches:
            process_match(wks, match)
    except KeyboardInterrupt:
        print('\nFin...')


if __name__ == '__main__':
    args = parser.parse_args()
    filename = args.file
    path_file = path(path_result, filename.split('.')[0][:8], filename)

    if not os.path.exists(path_file):
        logging.info(f'Archivo {path_file} no existe')
        exit(1)

    send_matches(path_file)
