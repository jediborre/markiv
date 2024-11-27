import re
import os
import pprint # noqa
import logging
import datetime
import argparse
from utils import prepare
from utils import save_matches
from parse import get_momios
from parse import get_all_matches
from parse import get_team_matches


# https://app.dataimpulse.com/plans/create-new
# https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json
# 131.0.6778.85
# .venv/Scripts/Activate.ps1
# chrome --remote-debugging-port=9222 --user-data-dir="C:\Log"
# python db/flashcore.py

web = None
opened_web = False
path_result, path_csv, path_json, path_html = prepare()
parser = argparse.ArgumentParser(description="Solicita partidos de hoy o mañana de flashscore") # noqa
parser.add_argument('--today', action='store_true', help="Partidos Hoy")
parser.add_argument('--tomorrow', action='store_true', help="Partidos Mañana")
parser.add_argument('--over', action='store_true', help="Sobreescribir")
args = parser.parse_args()
matches_today_url = 'https://m.flashscore.com.mx/'
matches_tomorrow_url = 'https://m.flashscore.com.mx/?d=1'


def process_matches(matches, date, overwrite=False):
    global path_result, path_csv, path_json, path_html

    n = 1
    result, result_pais = {}, {}
    fecha = date.strftime('%Y-%m-%d')
    fecha_filename = date.strftime('%Y%m%d')

    for pais, liga, hora, home, away, link, link_momios_1x2, link_momios_goles, link_momios_ambos in matches: # noqa
        hora_filename = re.sub(r":", "", hora)
        match_filename = f'{n}_{fecha_filename}{hora_filename}'
        matches = get_team_matches(
            match_filename,
            link,
            home,
            away,
            liga,
            web,
            opened_web,
            overwrite
        )
        if matches['OK']:
            momios = get_momios(
                match_filename,
                link_momios_1x2,
                link_momios_goles,
                link_momios_ambos,
                web,
                opened_web,
                overwrite
            )
            if momios['OK']:
                reg = {
                    'id': str(n),
                    'time': hora,
                    'fecha': fecha,
                    'pais': pais,
                    'liga': liga,
                    'home': home,
                    'away': away,
                    'url': link,
                    'promedio_gol': '',
                    '1x2': momios['odds_1x2'],
                    'goles': momios['odds_goles'],
                    'ambos': momios['odds_ambos'],
                    'link_1x2': link_momios_1x2,
                    'link_goles': link_momios_goles,
                    'link_ambos': link_momios_ambos,
                    'home_matches': matches['home_matches'],
                    'away_matches': matches['away_matches'],
                    'face_matches': matches['face_matches']
                }
                if pais not in result_pais:
                    result_pais[pais] = []

                result[reg['id']] = reg
                result_pais[pais].append(reg)

                logging.info(f'OK {match_filename} {liga} | {home} - {away}')
                match_json = os.path.join(path_json, f'{match_filename}.json')
                save_matches(match_json, reg, overwrite)

                input('')
                print('Continuar')
            else:
                logging.info(f'DESCARTADO MOMIOS {liga} | {home}:{matches["home_nmatches"]} - {away}:{matches["away_nmatches"]} VS:{matches["face_nmatches"]}') # noqa
                pprint.pprint(momios)
        else:
            logging.info(f'DESCARTADO {liga} | {home}:{matches["home_nmatches"]} - {away}:{matches["away_nmatches"]} VS:{matches["face_nmatches"]}') # noqa
        n += 1

    logging.info(f'PARTIDOS {len(matches)} {fecha}')
    matches_result = os.path.join(path_result, f'{fecha_filename}.json')
    matches_pais_result = os.path.join(path_result, f'{fecha_filename}_pais.json') # noqa

    if len(result) > 0:
        save_matches(matches_result, result, overwrite)

    if len(result_pais) > 0:
        save_matches(matches_pais_result, result_pais, overwrite)


def main(hoy=False, overwrite=False):
    global path_html
    global web, opened_web
    global matches_today_url, matches_tomorrow_url

    today = datetime.datetime.today()
    if hoy:
        date = today
        url = matches_today_url
    else:
        tomorrow = (today + datetime.timedelta(days=1))
        date = tomorrow
        url = matches_tomorrow_url

    fecha_filename = date.strftime('%Y%m%d')
    matches_filename = os.path.join(path_html, f'{fecha_filename}_matches.html') # noqa

    matches = get_all_matches(path_html, matches_filename, url, web, opened_web, overwrite) # noqa
    if len(matches) == 0:
        return

    process_matches(matches, date, overwrite)


if __name__ == "__main__":
    overwrite = args.over
    if args.tomorrow:
        main(False, overwrite)
    else:
        main(True, overwrite)
