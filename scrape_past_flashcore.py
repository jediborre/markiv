import os
import sys
import logging
import pygsheets
from web import Web
from utils import path
from datetime import datetime
from utils import save_matches
from utils import prepare_paths
from parse import get_all_matches
from parse import process_full_matches
from filtros import get_ligas_google_sheet

sys.stdout.reconfigure(encoding='utf-8')

# https://app.dataimpulse.com/plans/create-new
# https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json

# chrome --remote-debugging-port=9222 --user-data-dir="C:\Log"
# .venv/Scripts/Activate.ps1
# clear;python .\scrape_flashcore.py --over

opened_web = False
path_result, path_cron, path_csv, path_json, path_html = prepare_paths('scrape_past_flashcore.log') # noqa


def get_sheet_robot():
    path_script = os.path.dirname(os.path.realpath(__file__))
    service_file = path(path_script, 'feroslebosgc.json')
    gc = pygsheets.authorize(service_file=service_file)

    spreadsheet = gc.open('Mark 4')
    wks = spreadsheet.worksheet_by_title('Bot2')
    return wks


def get_sheet_wayback():
    path_script = os.path.dirname(os.path.realpath(__file__))
    service_file = path(path_script, 'feroslebosgc.json')
    gc = pygsheets.authorize(service_file=service_file)

    spreadsheet = gc.open('Mark 4')
    return spreadsheet.worksheet_by_title('LinksBack')


def get_past_links(wks=None):
    if wks is None:
        return []
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


def main(links=None):
    global web
    global path_json, path_html, path_result

    if not links:
        wks_wayback = get_sheet_wayback()
        links_fechas = get_past_links(wks_wayback)
    else:
        links_fechas = links

    if len(links_fechas) == 0:
        logging.info('No hay links')
        return

    web = Web(multiples=True)
    ligas = get_ligas_google_sheet()

    for n, dt, link, hecho in links_fechas:
        if hecho == 'si':
            continue

        str_fecha = dt.strftime('%Y%m%d')
        print(f'{n} - {str_fecha} - {link}')
        str_fecha_human = dt.strftime('%d %b %Y')
        path_page_matches = path(path_html, f'{n}_{str_fecha}_matches.html')

        matches = get_all_matches(
            path_html,
            path_page_matches,
            link,
            web,
            ligas
        )

        if len(matches) == 0:
            logging.info(f'No hay partidos {str_fecha_human}')
            continue

        filename_fecha = dt.strftime('%Y%m%d')
        path_result_date = path(path_result, filename_fecha)
        if not os.path.exists(path_result_date):
            os.makedirs(path_result_date)
        path_file = path(path_result_date, f'{filename_fecha}_ok.json')

        matches = process_full_matches(matches, dt, web, path_html)
        save_matches(path_file, matches, True)

        if not links:
            wks_wayback.update_value(f'C{n}', 'si')

    web.close()


if __name__ == "__main__":
    main([[
        '1',
        parse_spanish_date('may 11 2025'),
        'https://m.flashscore.com.mx/', # noqa
        ''
    ]])
    # main()
