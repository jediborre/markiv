import re
import os
import pprint # noqa
import logging
import datetime
import argparse
from utils import prepare
# from parse import get_momios
from utils import save_matches
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


def process_matches(matches_, date, web, opened_web, overwrite=False):
    global path_result, path_csv, path_json, path_html

    n = 1
    matches, matches_pais = {}, {}
    fecha = date.strftime('%Y-%m-%d')
    fecha_filename = date.strftime('%Y%m%d')

    print(web, opened_web)

    for pais, liga, hora, home, away, link, link_momios_1x2, link_momios_goles, link_momios_ambos, link_momios_handicap in matches_: # noqa
        hora_filename = re.sub(r":", "", hora)
        filename_match = f'{n}_{fecha_filename}{hora_filename}'
        team_matches = get_team_matches(
            path_html,
            filename_match,
            link,
            home,
            away,
            liga,
            web,
            opened_web,
            overwrite
        )
        if team_matches['OK']:
            reg = {
                'id': str(n),
                'time': hora,
                'fecha': fecha,
                'pais': pais,
                'liga': liga,
                'home': home,
                'away': away,
                'url': link,
                '1x2': None,
                'goles': None,
                'ambos': None,
                'link_1x2': link_momios_1x2,
                'link_goles': link_momios_goles,
                'link_ambos': link_momios_ambos,
                'link_handicap': link_momios_handicap,
                'home_matches': team_matches['home_matches'],
                'away_matches': team_matches['away_matches'],
                'face_matches': team_matches['face_matches']
            }
            if pais not in matches_pais:
                matches_pais[pais] = []

            matches[reg['id']] = reg
            matches_pais[pais].append(reg)

            logging.info(f'OK {filename_match} {liga} | {home} - {away}')
            match_json = os.path.join(path_json, f'{filename_match}.json')
            save_matches(match_json, reg, overwrite)

            input('')
            print('Continuar')
        else:
            logging.info(f'DESCARTADO {liga} | {home}:{team_matches["home_nmatches"]} - {away}:{team_matches["away_nmatches"]} VS:{team_matches["face_nmatches"]}') # noqa
        n += 1

    logging.info(f'PARTIDOS {len(matches)} {fecha}')
    filename_matches = os.path.join(path_result, f'{fecha_filename}.json')
    filename_matches_pais = os.path.join(path_result, f'{fecha_filename}_pais.json') # noqa

    if len(matches) > 0:
        save_matches(filename_matches, matches, overwrite)

    if len(matches_pais) > 0:
        save_matches(filename_matches_pais, matches_pais, overwrite)


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
    filename_matches = os.path.join(path_html, f'{fecha_filename}_matches.html') # noqa

    matches, web, opened_web = get_all_matches(path_html, filename_matches, url, web, opened_web, overwrite) # noqa
    if len(matches) == 0:
        return

    process_matches(matches, date, web, opened_web, overwrite)


if __name__ == "__main__":
    overwrite = args.over
    if args.tomorrow:
        main(False, overwrite)
    else:
        main(True, overwrite)

# momios = get_momios(
#     match_filename,
#     link_momios_1x2,
#     link_momios_goles,
#     link_momios_ambos,
#     link_momios_handicap,
#     web,
#     opened_web,
#     overwrite
# )
# if momios['OK']:
#     pass
# else:
#     logging.info(f'DESCARTADO MOMIOS {liga} | {home}:{matches["home_nmatches"]} - {away}:{matches["away_nmatches"]} VS:{matches["face_nmatches"]}') # noqa
#     pprint.pprint(momios)