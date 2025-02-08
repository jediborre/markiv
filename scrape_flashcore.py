import re
import sys
import pprint # noqa
import logging
import argparse
from web import Web
from utils import path
from utils import get_percent
from utils import save_matches
from utils import prepare_paths
from parse import get_all_matches
from parse import get_team_matches
from cron_flashscore import cron_matches
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

# https://app.dataimpulse.com/plans/create-new
# https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json

# chrome --remote-debugging-port=9222 --user-data-dir="C:\Log"
# .venv/Scripts/Activate.ps1
# clear;python .\scrape_flashcore.py --over


opened_web = False
parser = argparse.ArgumentParser(description="Solicita partidos de hoy o mañana de flashscore") # noqa
parser.add_argument('--today', action='store_true', help="Partidos Hoy")
parser.add_argument('--tomorrow', action='store_true', help="Partidos Mañana")
parser.add_argument('--over', action='store_true', help="Sobreescribir")
args = parser.parse_args()

url_matches_today = 'https://m.flashscore.com.mx/'
url_matches_tomorrow = 'https://m.flashscore.com.mx/?d=1'
path_result, path_cron, path_csv, path_json, path_html = prepare_paths('scrape_flashcore.log') # noqa


def process_matches(matches_, date, web, overwrite=False):
    global path_csv, path_json, path_html, path_result

    ok = 0
    matches, matches_pais = {}, {}
    fecha = date.strftime('%Y-%m-%d')
    filename_fecha = date.strftime('%Y%m%d')
    path_matches = path(path_result, f'{filename_fecha}.json')
    path_matches_pais = path(path_result, f'{filename_fecha}_pais.json') # noqa

    TS = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f'{TS} - Procesando {len(matches_)} partidos {fecha}\n\n')
    for m, match in enumerate(matches_):
        [
            pais,
            liga,
            hora,
            home,
            away,
            link,
        ] = match

        filename_hora = re.sub(r":", "", hora)
        filename_match = f'{m}_{filename_fecha}{filename_hora}'
        path_match = path(path_json, f'{filename_match}.json')

        total_matches = len(matches_)
        percent = get_percent(m + 1, total_matches)
        str_percent = f'{m + 1}-{total_matches} → {percent}'
        TS = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logging.info(f'{TS}|{str_percent}|{ok}| {hora} {liga} : {home} - {away}') # noqa

        team_matches = get_team_matches(
            path_html,
            filename_match,
            link,
            home,
            away,
            liga,
            web,
            overwrite
        )

        n_vs = team_matches['vs_nmatches']
        n_h = team_matches['home_nmatches']
        n_a = team_matches['away_nmatches']

        if team_matches['OK']:
            ok += 1
            reg = {
                'id': str(m),
                'hora': hora,
                'fecha': fecha,
                'pais': pais,
                'liga': liga,
                'home': home,
                'away': away,
                'url': link,
                '1x2': None,
                'goles': None,
                'ambos': None,
                'handicap': None,
                'home_matches': team_matches['home_matches'],
                'away_matches': team_matches['away_matches'],
                'vs_matches': team_matches['vs_matches'],
                'filename_fecha': filename_fecha,
                'filename_match': filename_match
            }
            if pais not in matches_pais:
                matches_pais[pais] = []

            matches[reg['id']] = reg
            matches_pais[pais].append(reg)

            save_matches(path_match, reg, overwrite)
            save_matches(path_matches, matches, True)
            save_matches(path_matches_pais, matches_pais, True)

            logging.info('| OK\n')
        else:
            logging.info(f'| NO H:{n_h}, A→{n_a}, VS→{n_vs}\n')

    logging.info(f'\n\nPARTIDOS {len(matches)} {fecha}')
    if len(matches) > 0:
        save_matches(path_matches, matches, True)
        cron_matches(path_matches)

    if len(matches_pais) > 0:
        save_matches(path_matches_pais, matches_pais, True)


def main(hoy=False, overwrite=False):
    global web, path_html
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
    path_page_matches = path(path_html, f'{fecha}_matches.html') # noqa

    web = Web(multiples=True)
    matches = get_all_matches(path_html, path_page_matches, url, web, True) # noqa
    if len(matches) == 0:
        logging.info(f'No hay partidos {fecha}')
        return

    process_matches(matches, date, web, overwrite)
    web.close()


if __name__ == "__main__":
    overwrite = args.over
    if args.tomorrow:
        main(False, overwrite)
    else:
        main(True, overwrite)
