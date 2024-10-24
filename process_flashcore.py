import os
import json
import logging
import datetime
# import requests
from web import Web
from bs4 import BeautifulSoup
# https://app.dataimpulse.com/plans/create-new
# https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json

# .venv/Scripts/Activate.ps1
# chrome --remote-debugging-port=9222 --user-data-dir="C:\Log"
# python db/flashcore.py

script_path = os.path.dirname(os.path.abspath(__file__))
log_filepath = os.path.join(script_path, 'web_markiv.log')
source_path = os.path.join(script_path, 'db', 'flashscore')
if not os.path.exists(source_path):
    os.makedirs(source_path)
today = datetime.datetime.today()
tomorrow = (today + datetime.timedelta(days=1))
db_file = tomorrow.strftime('%Y%m%d')
flashcore_page_filename = f'{source_path}/{tomorrow.strftime("%Y%m%d")}.html'
domain = 'https://www.flashscore.com.mx'
mobile_url = 'https://m.flashscore.com.mx/?d=1'
proxy_url = 'https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&country=mx,us,ca&protocol=http&proxy_format=ipport&format=text&timeout=4000' # noqa

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filepath),
        logging.StreamHandler()
    ]
)

# url = 'https://www.flashscore.com.mx/'
# web = Web(proxy_url=proxy_url, url=url)
# web.click_id('hamburger-menu')
# web.click_class('contextMenu__row')
# label        class="radioButton settings__label" Hora de Inicioi
# div cerrar   class="header__button header__button--active"


def main():
    global today, tomorrow, db_file
    global source_path, flashcore_page_filename
    if not os.path.exists(flashcore_page_filename):
        web = Web(proxy_url=proxy_url, url=mobile_url)
        web.wait_idElement('main', 5)
        open(flashcore_page_filename, 'w', encoding='utf-8').write(web.source()) # noqa

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
                    resultados.append((pais, nombre_liga, hora, local, visitante, url)) # noqa
                except ValueError:
                    pass
            partido_actual = partido_actual.find_next_sibling()

    n = 1
    result = {}
    result_pais = {}
    fecha = today.strftime('%Y-%m-%d')
    resultados_ordenados = sorted(resultados, key=lambda x: x[2])
    for pais, liga, hora, home, away, link in resultados_ordenados: # noqa
        print(f"{hora} {pais} {liga} {home} - {away} {url}")
        reg = {
            'id': str(n),
            'time': hora,
            'fecha': fecha,
            'pais': pais,
            'liga': liga,
            'home': home,
            'away': away,
            'url': url,
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
        print(f'Partidos Procesados {len(resultados_ordenados)}')
        with open(f'{source_path}/{db_file}.json', 'w') as f:
            f.write(json.dumps(result))
    if len(result_pais) > 0:
        with open(f'{source_path}/{db_file}_pais.json', 'w') as f:
            f.write(json.dumps(result_pais))

    print(f'{len(resultados_ordenados)} Partidos')


if __name__ == "__main__":
    main()
