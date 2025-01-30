import os
import sys
import logging
import argparse
from web import Web
from utils import get_json
from bs4 import BeautifulSoup
from utils import path, pathexist
from utils import prepare_paths_ok

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
    logging.info(f'MarkIV {filename}\n')
    web = Web()
    matches = get_json(path_file)
    try:
        for m in matches:
            link = m["url"].replace('h2h/overall', 'resumen-del-partido')
            liga = m["liga"]
            home = m["home"]
            away = m["away"]
            hora = m["hora"]
            pais = m["pais"]
            print(pais, liga, hora, home, away, link)
            web.open(link)
            web.wait(1)
            soup = BeautifulSoup(web.source(), 'html.parser')

            finalizado = False
            try:
                resultado = soup.find('div', class_='duelParticipant__score').text.strip() # noqa
                if 'Finalizado' in resultado:
                    finalizado = True
                    home_ft, away_ft = resultado.replace('Finalizado', '').strip().split('-') # noqa
                    print(f"Resultado: {home_ft} - {away_ft}")
            except AttributeError:
                print("No se pudo encontrar el resultado. Revisa la estructura del HTML.") # noqa

            if finalizado:
                try:
                    goles = []
                    eventos_home = soup.find_all('div', class_='smv__participantRow smv__homeParticipant') # noqa
                    if len(eventos_home) > 0:
                        for evento in eventos_home:
                            minuto = evento.find('div', class_='smv__timeBox').text.strip().replace("'", '') # noqa
                            goles.append([minuto, 'Home'])

                    eventos_away = soup.find_all('div', class_='smv__participantRow smv__awayParticipant') # noqa
                    if len(eventos_away) > 0:
                        for evento in eventos_away:
                            minuto = evento.find('div', class_='smv__timeBox').text.strip().replace("'", '') # noqa
                            goles.append([minuto, 'Away'])

                    goles_ordenados = sorted(goles, key=lambda x: x[0])

                    for min, equipo in goles_ordenados:
                        print(f'{min} - {equipo}')
                except AttributeError:
                    print("No se pudieron encontrar los goles. Revisa la estructura del HTML.") # noqa

            # input('Enter para continuar...')
    except KeyboardInterrupt:
        print('\nFin...')
    # web.close()


if __name__ == '__main__':
    args = parser.parse_args()
    filename = args.file
    path_file = path(path_result, filename.split('.')[0][:8], filename)

    if pathexist(path_file):
        resultados(path_file, filename)
