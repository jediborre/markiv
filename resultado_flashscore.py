import os
import sys
import logging
import argparse
from web import Web
from utils import gsheet
from utils import busca_id_bot
from utils import get_json_list
from parse import get_marcador_ft
from parse import status_partido
from utils import path, pathexist
from parse import remueve_anuncios
from utils import prepare_paths_ok
from parse import click_OK_cookies_btn

# https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json

url_matches_today = 'https://m.flashscore.com.mx/'

sys.stdout.reconfigure(encoding='utf-8')

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID').split(',')

path_result, path_ok = prepare_paths_ok()

parser = argparse.ArgumentParser(description="Solicita partidos de hoy o mañana de flashscore") # noqa
parser.add_argument('file', type=str, help='Archivo de Partidos Flashscore')
args = parser.parse_args()


def resultados(path_file: str, filename: str):
    logging.info(f'Friday {filename}\n')
    web = Web(multiples=True)
    matches = get_json_list(path_file)
    try:
        wks = gsheet('Bot')
        bot_regs = wks.get_all_values(returnas='matrix')
        for n, m in enumerate(matches):
            id = m["id"]
            link = m["url"].replace('h2h/overall', 'resumen-del-partido')
            liga = m["liga"]
            home = m["home"]
            away = m["away"]
            hora = m["hora"]
            pais = m["pais"]
            row = busca_id_bot(bot_regs, id)
            print(link)
            web.open(link)
            web.wait(1)

            if n == 0:
                click_OK_cookies_btn(web)

            remueve_anuncios(web)

            status = status_partido(web)
            finalizado = False
            if status == 'finalizado':
                finalizado = True
                print(pais, liga, hora, home, away, row, 'Finalizado') # noqa
            elif status == 'aplazado':
                print(pais, liga, hora, home, away, row, 'Aplazado', '-', '-') # noqa
                wks.update_value(f'AK{row}', '-')
                wks.update_value(f'AL{row}', '-')
                wks.update_value(f'AM{row}', '-')
                wks.update_value(f'AN{row}', '-')
                wks.update_value(f'AQ{row}', '-')
            else:
                print(pais, liga, hora, home, away, row, 'En Juego', '-', '-') # noqa
            if finalizado:
                marcador = get_marcador_ft(web, True)
                total_goles = marcador['ft']
                sheet = marcador['sheet']
                gol1, gol2, gol3, gol4, rojahome, rojas_away = sheet
                wks.update_value(f'AK{row}', gol1)
                wks.update_value(f'AL{row}', gol2)
                wks.update_value(f'AM{row}', gol3)
                wks.update_value(f'AN{row}', gol4)
                wks.update_value(f'AO{row}', rojahome)
                wks.update_value(f'AP{row}', rojas_away)
                wks.update_value(f'AQ{row}', total_goles)
    except KeyboardInterrupt:
        print('\nFin...')
    web.close()


if __name__ == '__main__':
    args = parser.parse_args()
    filename = args.file
    filename_date = filename[:8]
    path_file = path(path_result, filename_date, 'ok', filename)

    if not pathexist(path_file):
        logging.error(f'No se encontró el archivo {path_file}')
        sys.exit(1)

    resultados(path_file, filename)
