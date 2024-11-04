import os
import json
import logging
import datetime
import argparse
from web import Web
from bs4 import BeautifulSoup
# https://app.dataimpulse.com/plans/create-new
# https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json

# .venv/Scripts/Activate.ps1
# chrome --remote-debugging-port=9222 --user-data-dir="C:\Log"
# python db/flashcore.py
parser = argparse.ArgumentParser(
    description="Solicita partidos de hoy o ma;ana de flashscore"
)
parser.add_argument('--today', action='store_true', help="Partidos Hoy")
parser.add_argument('--tomorrow', action='store_true', help="Partidos Mañana")
parser.add_argument('--over', action='store_true', help="Sobreescribir")
args = parser.parse_args()
script_path = os.path.dirname(os.path.abspath(__file__))
log_filepath = os.path.join(script_path, 'web_markiv.log')
source_path = os.path.join(script_path, 'db', 'flashscore')
if not os.path.exists(source_path):
    os.makedirs(source_path)
today = datetime.datetime.today()
tomorrow = (today + datetime.timedelta(days=1))
db_file = tomorrow.strftime('%Y%m%d')
domain = 'https://www.flashscore.com.mx'
mobile_today_url = 'https://m.flashscore.com.mx/'
mobile_tomorrow_url = 'https://m.flashscore.com.mx/?d=1'
proxy_url = 'https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&country=mx,us,ca&protocol=http&proxy_format=ipport&format=text&timeout=4000' # noqa

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filepath),
        logging.StreamHandler()
    ]
)


def main(hoy=False, reescribir=False):
    global today, tomorrow, db_file
    global mobile_today_url, mobile_tomorrow_url
    global source_path, flashcore_page_filename

    if hoy:
        fecha = today.strftime('%Y-%m-%d')
        tomorrow = today
        db_file = today.strftime('%Y%m%d')
        flashcore_page_filename = f'{source_path}/{today.strftime("%Y%m%d")}.html' # noqa
        mobile_url = mobile_today_url
    else:
        fecha = tomorrow.strftime('%Y-%m-%d')
        tomorrow = (today + datetime.timedelta(days=1))
        db_file = tomorrow.strftime('%Y%m%d')
        flashcore_page_filename = f'{source_path}/{tomorrow.strftime("%Y%m%d")}.html' # noqa
        mobile_url = mobile_tomorrow_url

    if not os.path.exists(flashcore_page_filename) and not reescribir:
        web = Web(proxy_url=proxy_url, url=mobile_url)
        web.wait_idElement('main', 5)
        open(flashcore_page_filename, 'w', encoding='utf-8').write(web.source()) # noqa
        web.close()
    else:
        if reescribir:
            web = Web(proxy_url=proxy_url, url=mobile_url)
            web.wait_idElement('main', 5)
            open(flashcore_page_filename, 'w', encoding='utf-8').write(web.source()) # noqa
            web.close()

    resultados = []
    with open(flashcore_page_filename, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    ligas = soup.find_all('h4')
    for liga in ligas:
        tmp_liga = liga.get_text(strip=True)
        pais, nombre_liga = tmp_liga.split(': ')
        partido_actual = liga.find_next_sibling()

        while partido_actual and partido_actual.name != 'h4':
            if partido_actual.name == 'span':
                hora = partido_actual.get_text(strip=True)
                equipos = partido_actual.find_next_sibling(text=True).strip() # noqa
                try:
                    local, visitante = equipos.split(' - ')
                    link = partido_actual.find_next_sibling('a')['href']
                    url = f'{domain}{link}#/h2h/overall'
                    url_momios_1x2 = f'{domain}{link}#/comparacion-de-momios/momios-1x2/partido' # noqa
                    url_momios_goles = f'{domain}{link}#/comparacion-de-momios/mas-de-menos-de/partido' # noqa
                    url_momios_ambos = f'{domain}{link}#/comparacion-de-momios/ambos-equipos-marcaran/partido' # noqa
                    resultados.append((
                        pais,
                        nombre_liga,
                        hora,
                        local,
                        visitante,
                        url,
                        url_momios_1x2,
                        url_momios_goles,
                        url_momios_ambos
                    )) # noqa
                except ValueError:
                    pass
            partido_actual = partido_actual.find_next_sibling()

    n = 1
    result = {}
    result_pais = {}
    fecha = tomorrow.strftime('%Y-%m-%d')
    resultados_ordenados = sorted(resultados, key=lambda x: x[2])
    for pais, liga, hora, home, away, link, link_momios_1x2, link_momios_goles, link_momios_ambos in resultados_ordenados: # noqa
        print(f"{hora} {pais} {liga} {home} - {away} {link}")
        reg = {
            'id': str(n),
            'time': hora,
            'fecha': fecha,
            'pais': pais,
            'liga': liga,
            'home': home,
            'away': away,
            'url': link,
            'momios_1x2': link_momios_1x2,
            'momios_goles': link_momios_goles,
            'momios_ambos': link_momios_ambos,
            'promedio_gol': '',
            'home_matches': [],
            'away_matches': [],
            'face_matches': []
        }
        n = n + 1
        if pais not in result_pais:
            result_pais[pais] = []
        result[reg['id']] = reg
        result_pais[pais].append(reg)

    if len(result) > 0:
        print(f'Partidos Procesados {len(resultados_ordenados)} {fecha}')
        with open(f'{source_path}/{db_file}.json', 'w') as f:
            f.write(json.dumps(result))
    if len(result_pais) > 0:
        with open(f'{source_path}/{db_file}_pais.json', 'w') as f:
            f.write(json.dumps(result_pais))


if __name__ == "__main__":
    rescribir = args.over
    if args.today:
        main(hoy=True, reescribir=rescribir)
    elif args.tomorrow:
        main(reescribir=rescribir)
    else:
        main(hoy=True, reescribir=rescribir)
