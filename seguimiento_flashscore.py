import re
import os
import sys
import logging
import argparse
from web import Web
from utils import get_json
from bs4 import BeautifulSoup
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


def get_current_scores(web: Web):
    web.open(url_matches_today)
    web.wait_ID('main', 5)
    html = web.source()
    matches = {}
    filter_ligas = [
        'amistoso',
        'amistosos',
        'cup',
        'copa',
        'femenino',
        'femenina',
        'mundial',
        'playoffs',
        'internacional',
        'women',
    ]
    domain = 'https://www.flashscore.com.mx'
    soup = BeautifulSoup(html, 'html.parser')
    ligas = soup.find_all('h4')
    for liga in ligas:
        tmp_liga = ''.join([str(content) for content in liga.contents if not content.name]) # noqa
        pais, nombre_liga = tmp_liga.split(': ')
        nombre_liga = re.sub(r'\s+$', '', nombre_liga)
        partido_actual = liga.find_next_sibling()

        if any([x in nombre_liga.lower() for x in filter_ligas]):
            continue

        while partido_actual and partido_actual.name != 'h4':
            if partido_actual.name == 'span':
                hora = partido_actual.get_text(strip=True)
                aplazado = 'Aplazado' in hora
                hora = hora[:5]
                equipos = partido_actual.find_next_sibling(string=True).strip() # noqa
                try:
                    home, away = equipos.split(' - ')
                    score = partido_actual.find_next_sibling('a').get_text(strip=True) # noqa
                    link = partido_actual.find_next_sibling('a')['href']
                    link = f'{domain}{link}#/h2h/overall'
                    if not aplazado:
                        if nombre_liga not in matches:
                            matches[nombre_liga] = []
                        matches[nombre_liga].append({
                            'hora': hora,
                            'home': home,
                            'away': away,
                            'score': score,
                            'url': link,
                        })
                except ValueError:
                    pass
            partido_actual = partido_actual.find_next_sibling()
    return matches


def seguimiento(path_file: str, filename: str):
    logging.info(f'MarkIV {filename} {path_file}')
    web = Web()
    matches = get_json(path_file)
    _matches = get_current_scores(web)
    try:
        for m in matches:
            # link = m["url"]
            liga = m["liga"]
            home = m["home"]
            away = m["away"]
            hora = m["hora"]
            pais = m["pais"]
            if liga in _matches:
                # [{'hora': '17:00', 'home': 'Juárez', 'away': 'Cruz Azul', 'score': '1:0', 'url': 'https://www.flashscore.com.mx/partido/OWSpVMH6/#/h2h/overall'}, {'hora': '19:00', 'home': 'Toluca', 'away': 'Monterrey', 'score': '1:1', 'url': 'https://www.flashscore.com.mx/partido/M7WTY4Is/#/h2h/overall'}, {'hora': "80'", 'home': 'Atlas', 'away': 'León', 'score': '1:0', 'url': 'https://www.flashscore.com.mx/partido/UXZyXrmf/#/h2h/overall'}] # noqa
                record = next((match for match in _matches[liga] if match['home'] == home and match['away'] == away), None) # noqa
                if record:
                    home_score, away_score = record['score'].split(':') if record else (None, None) # noqa
                    record['hora'] == 'Aplazado'
                    minuto = record['hora'] if ':' not in record['hora'] else None # noqa
                    if minuto:
                        print(pais, hora, home, home_score, away, away_score, minuto) # noqa
                    else:
                        print(pais, home, home_score, away, away_score, 'FT')
                else:
                    print(pais, home, away, 'No encontrado')
            else:
                print(pais, hora, home, away, 'No encontrado')

    except KeyboardInterrupt:
        print('\nFin...')
    input('Presione una tecla para continuar')
    # web.close()


if __name__ == '__main__':
    args = parser.parse_args()
    filename = args.file
    path_file = path(path_result, filename.split('.')[0][:8], filename)

    if pathexist(path_file):
        seguimiento(path_file, filename)
