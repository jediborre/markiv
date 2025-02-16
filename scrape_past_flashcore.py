import sys
import os
import logging
import pygsheets
from web import Web
from utils import path
from datetime import datetime
from utils import prepare_paths
from parse import get_all_matches
from parse import process_matches
from filtros import get_ligas_google_sheet

sys.stdout.reconfigure(encoding='utf-8')

# https://app.dataimpulse.com/plans/create-new
# https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json

# chrome --remote-debugging-port=9222 --user-data-dir="C:\Log"
# .venv/Scripts/Activate.ps1
# clear;python .\scrape_flashcore.py --over

opened_web = False
path_result, path_cron, path_csv, path_json, path_html = prepare_paths('scrape_past_flashcore.log') # noqa


def get_past_links():
    # print('get_past Matches wayBackMachine', '')
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


def main():
    global web, path_html
    global path_json, path_html, path_result

    links_fechas = get_past_links()
    if len(links_fechas) == 0:
        logging.info('No hay links')
        return

    ligas = get_ligas_google_sheet()
    web = Web(multiples=True)
    for n, dt, link, hecho in links_fechas:
        if hecho == 'si':
            continue

        str_fecha = dt.strftime('%Y%m%d')
        str_fecha_human = dt.strftime('%d %b %Y')

        print(f'{n} - {str_fecha} - {link}')
        path_page_matches = path(path_html, f'{n}_{str_fecha}_matches.html')
        matches = get_all_matches(
            path_html,
            path_page_matches,
            link,
            web,
            ligas
        )
        process_matches(
            matches,
            dt,
            web,
            path_json,
            path_html,
            path_result,
            True
        )

        if len(matches) == 0:
            logging.info(f'No hay partidos {str_fecha_human}')
            continue

        break
    web.close()


if __name__ == "__main__":
    main()
