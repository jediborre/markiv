import re
import sys
import os
import logging
import pygsheets
from web import Web
from utils import path
from datetime import datetime
from utils import get_percent
from utils import save_matches
from utils import prepare_paths
from parse import get_team_matches
from parse import get_all_matches
from cron_flashscore import cron_matches
from filtros import get_ligas_google_sheet

sys.stdout.reconfigure(encoding='utf-8')

# https://app.dataimpulse.com/plans/create-new
# https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json

# chrome --remote-debugging-port=9222 --user-data-dir="C:\Log"
# .venv/Scripts/Activate.ps1
# clear;python .\scrape_flashcore.py --over

opened_web = False
path_result, path_cron, path_csv, path_json, path_html = prepare_paths('scrape_past_flashcore.log') # noqa


def parse_spanish_date(str_date):
    month_translation = {
        'ene': 'Jan', 'feb': 'Feb', 'mar': 'Mar', 'abr': 'Apr', 'may': 'May',
        'jun': 'Jun', 'jul': 'Jul', 'ago': 'Aug', 'sep': 'Sep', 'oct': 'Oct',
        'nov': 'Nov', 'dic': 'Dec'
    }

    parts = str_date.split()
    if len(parts) != 3:
        raise ValueError("Invalid date format. Expected format: 'mmm dd yyyy'")

    spanish_month, day, year = parts
    if spanish_month.lower() not in month_translation:
        raise ValueError(f"Unknown month: {spanish_month}")

    english_month = month_translation[spanish_month.lower()]
    english_date = f"{english_month} {day} {year}"

    return datetime.strptime(english_date, '%b %d %Y')


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


def get_past_links():
    print('get_past Matches wayBackMachine', '')
    path_script = os.path.dirname(os.path.realpath(__file__))
    service_file = path(path_script, 'feroslebosgc.json')
    gc = pygsheets.authorize(service_file=service_file)

    spreadsheet = gc.open('Mark 4')
    wks = spreadsheet.worksheet_by_title('LinksBack')
    rows = wks.get_all_values(returnas='matrix')

    result = []
    for n, row in enumerate(rows):
        if n > 0:
            fecha, link, hecho = row
            result.append([
                n + 1,
                parse_spanish_date(fecha),
                link,
                hecho
            ])

    return result


def main():
    global web, path_html

    links_fechas = get_past_links()
    if len(links_fechas) == 0:
        logging.info('No hay links')
        return

    ligas = get_ligas_google_sheet()
    web = Web(multiples=True)
    for n, [n_, dt, link, hecho] in enumerate(links_fechas):
        if hecho == 'si':
            continue

        str_fecha = dt.strftime('%Y%m%d')
        str_fecha_human = dt.strftime('%d %b %Y')

        print(f'{n_} - {str_fecha} - {link}')
        path_page_matches = path(path_html, f'{str_fecha}_matches.html')
        matches = get_all_matches(
            path_html,
            path_page_matches,
            link,
            web,
            ligas,
            True
        )
        for m, (pais, liga, hora, home, away, link) in enumerate(matches):
            print(f'{m} {str_fecha_human} {hora} | {pais} - {liga} | {home} - {away} - {link}') # noqa

        if len(matches) == 0:
            logging.info(f'No hay partidos {str_fecha_human}')
            continue

        break
    web.close()


        # process_matches(matches, date, web, True)
    # url = url_matches_tomorrow

    # path_page_matches = path(path_html, f'{fecha}_matches.html') # noqa

    # web = Web(multiples=True)
    # matches = get_all_matches(path_html, path_page_matches, url, web, True) # noqa
    # if len(matches) == 0:
    #     logging.info(f'No hay partidos {fecha}')
    #     return

    # process_matches(matches, date, web, overwrite)


if __name__ == "__main__":
    main()
