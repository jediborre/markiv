import re
import os
import json
import pprint # noqa
import datetime
import argparse
from web import Web
from utils import prepare
from utils import save_matches
from bs4 import BeautifulSoup
from parse import parse_team_matches, parse_odds_ambos, parse_odds_1x2, parse_odds_goles # noqa

# https://app.dataimpulse.com/plans/create-new
# https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json
# 131.0.6778.85
# .venv/Scripts/Activate.ps1
# chrome --remote-debugging-port=9222 --user-data-dir="C:\Log"
# python db/flashcore.py

prepare()
web = None
opened_web = False
parser = argparse.ArgumentParser(description="Solicita partidos de hoy o mañana de flashscore") # noqa
parser.add_argument('--today', action='store_true', help="Partidos Hoy")
parser.add_argument('--tomorrow', action='store_true', help="Partidos Mañana")
parser.add_argument('--over', action='store_true', help="Sobreescribir")
args = parser.parse_args()
today = datetime.datetime.today()
tomorrow = (today + datetime.timedelta(days=1))
db_file = tomorrow.strftime('%Y%m%d')
domain = 'https://www.flashscore.com.mx'
mobile_today_url = 'https://m.flashscore.com.mx/'
mobile_tomorrow_url = 'https://m.flashscore.com.mx/?d=1'
proxy_url = 'https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&country=mx,us,ca&protocol=http&proxy_format=ipport&format=text&timeout=4000' # noqa


def click_more(web, team, team_name, liga):
    sections = web.CLASS('h2h__section', multiples=True)
    section = sections[0] if team == 'home' else sections[1]
    result = parse_team_matches(web.source(), team, team_name=team_name, liga=liga) # noqa
    num_matches = result['home_nmatches'] if team == 'home' else result['away_nmatches'] # noqa
    if not result['OK'] and section.EXIST_CLASS('showMore'):
        btn_showMore = section.CLASS('showMore')
        btn_showMore.scroll_to()
        if btn_showMore.click():
            print(f'{team} matches: {num_matches} MORE')
        else:
            web.scrollY(-150)
            btn_showMore.click()
            print(f'{team} matches: {num_matches} CANT CLICK MORE')
        web.wait()
        click_more(web, team, team_name, liga)
    else:
        print(f'{team} matches: {num_matches} DONE')


def get_tean_matches(link, filename, home, away, liga, overwrite=False):
    global tmp_path
    global opened_web, web, proxy_url
    filename = re.sub(r'-|:', '', filename) + '_h2h.html'
    html_path = os.path.join(tmp_path, filename)
    if not os.path.exists(html_path) or overwrite:
        print('Partido', link, '→', filename) # noqa
        if not opened_web:
            opened_web = True
            web = Web(proxy_url=proxy_url, url=link)
        else:
            web.open(link)

        web.wait_Class('h2h__section', 20)
        result = parse_team_matches(web.source(), 'face')
        if result['face_nmatches'] > 3:
            print('More Home matches...')
            click_more(web, 'home', home, liga)
            print('More Away matches...')
            click_more(web, 'away', away, liga)
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(web.source())
        else:
            return {
                'OK': False,
                'home_nmatches': '-',
                'away_nmatches': '-',
                'face_nmatches': result['face_nmatches']
            }
    else:
        print('Partido', '←', filename)

    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as file:
            return parse_team_matches(file, 'all', home=home, away=away, liga=liga) # noqa


def getmGoles(filename, link, overwrite=False):
    global tmp_path
    global opened_web, web, proxy_url
    nom = 'Goles'
    filename = re.sub(r'-|:', '', filename) + f'_{nom}.html'
    html_path = os.path.join(tmp_path, filename)
    if not os.path.exists(html_path) or overwrite:
        print(f'Momios {nom}', link, '→', filename)
        if not opened_web:
            opened_web = True
            web = Web(proxy_url=proxy_url, url=link)
        else:
            web.open(link)

        web.save(html_path)
    else:
        print(f'Momios {nom}', '←', filename)

    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as file:
            odds = parse_odds_goles(file)
            return odds
    else:
        return {
            'OK': False
        }


def getAmbos(filename, link, overwrite=False):
    global tmp_path
    global opened_web, web, proxy_url
    nom = 'Ambos'
    filename = re.sub(r'-|:', '', filename) + f'_{nom}.html'
    html_path = os.path.join(tmp_path, filename)
    if not os.path.exists(html_path) or overwrite:
        print(f'Momios {nom}', link, '→', filename)
        if not opened_web:
            opened_web = True
            web = Web(proxy_url=proxy_url, url=link)
        else:
            web.open(link)

        web.save(html_path)
    else:
        print(f'Momios {nom}', '←', filename)

    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as file:
            odds = parse_odds_ambos(file)
            return odds
    else:
        return {
            'OK': False
        }


def get1x2(filename, link, overwrite=False):
    global tmp_path
    global opened_web, web, proxy_url
    nom = '1x2'
    filename = re.sub(r'-|:', '', filename) + f'_{nom}.html'
    html_path = os.path.join(tmp_path, filename)
    if not os.path.exists(html_path) or overwrite:
        print(f'Momios {nom}', link, '→', filename)
        if not opened_web:
            opened_web = True
            web = Web(proxy_url=proxy_url, url=link)
        else:
            web.open(link)

        web.save(html_path)
    else:
        print(f'Momios {nom}', '←', filename)

    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as file:
            odds = parse_odds_1x2(file)
            return odds
    else:
        return {
            'OK': False
        }


def get_momios(filename, link_momios_1x2, link_momios_goles, link_momios_ambos, overwrite=False): # noqa
    momios_1x2 = get1x2(filename, link_momios_1x2, overwrite)
    if not momios_1x2['OK']:
        return {
            'OK': False,
            'odds_1x2': momios_1x2,
            'odds_goles': {},
            'odds_ambos': {},
        }

    momios_goles = getmGoles(filename, link_momios_goles, overwrite)
    if not momios_goles['OK']:
        return {
            'OK': False,
            'odds_1x2': momios_1x2,
            'odds_goles': momios_goles,
            'odds_ambos': {},
        }

    momios_ambos = getAmbos(filename, link_momios_ambos, overwrite)
    if not momios_ambos['OK']:
        return {
            'OK': False,
            'odds_1x2': momios_1x2,
            'odds_goles': momios_goles,
            'odds_ambos': momios_ambos,
        }

    return {
        'OK': momios_ambos['OK'] and momios_goles['OK'] and momios_1x2['OK'],
        'odds_1x2': momios_1x2,
        'odds_goles': momios_goles,
        'odds_ambos': momios_ambos,
    }


def main(hoy=False, overwrite=False):
    global opened_web, web, proxy_url
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

    if not os.path.exists(flashcore_page_filename) and not overwrite:
        web = Web(proxy_url=proxy_url, url=mobile_url)
        web.wait_ID('main', 5)
        opened_web = True
        web.save(flashcore_page_filename)
    else:
        if overwrite:
            web = Web(proxy_url=proxy_url, url=mobile_url)
            web.wait_ID('main', 5)
            opened_web = True
            web.save(flashcore_page_filename)

    resultados = []
    with open(flashcore_page_filename, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

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

    ligas = soup.find_all('h4')
    for liga in ligas:
        tmp_liga = ''.join([str(content) for content in liga.contents if not content.name]) # noqa
        pais, nombre_liga = tmp_liga.split(': ')
        nombre_liga = re.sub(r'\s+$', '', nombre_liga)
        partido_actual = liga.find_next_sibling()

        if any([x in nombre_liga.lower() for x in filter_ligas]):
            # print(f'Liga no deseada: "{nombre_liga}"------------------')
            continue

        while partido_actual and partido_actual.name != 'h4':
            if partido_actual.name == 'span':
                hora = partido_actual.get_text(strip=True)
                equipos = partido_actual.find_next_sibling(string=True).strip() # noqa
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

    print(f'{source_path}/{db_file}.csv')
    f = open(f'{source_path}/{db_file}.csv', 'w', encoding='utf-8')
    f.write("fecha,hora,pais,liga,local,visitante,link\n")
    for pais, liga, hora, home, away, link, link_momios_1x2, link_momios_goles, link_momios_ambos in resultados_ordenados: # noqa
        filename = f'{n}_{re.sub(r"-", "", fecha)}{re.sub(r":", "", hora)}'
        matches = get_tean_matches(link, filename, home, away, liga, overwrite) # noqa
        if matches['OK']:
            momios = get_momios(filename, link_momios_1x2, link_momios_goles, link_momios_ambos, overwrite) # noqa
            if momios['OK']:
                f.write(','.join([
                    fecha,
                    hora,
                    pais,
                    liga,
                    home,
                    away,
                    link
                ]) + '\n')
                reg = {
                    'id': str(n),
                    'time': hora,
                    'fecha': fecha,
                    'pais': pais,
                    'liga': liga,
                    'home': home,
                    'away': away,
                    'url': link,
                    '1x2': momios['odds_1x2'],
                    'goles': momios['odds_goles'],
                    'ambos': momios['odds_ambos'],
                    'link_1x2': link_momios_1x2,
                    'link_goles': link_momios_goles,
                    'link_ambos': link_momios_ambos,
                    'promedio_gol': '',
                    'home_matches': matches['home_matches'],
                    'away_matches': matches['away_matches'],
                    'face_matches': matches['face_matches']
                }
                if pais not in result_pais:
                    result_pais[pais] = []
                result[reg['id']] = reg
                result_pais[pais].append(reg)
                match_filename = f'{filename}.json'
                result_file = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    'result',
                    'match',
                    match_filename
                )
                save_matches(result_file, reg)
                print('OK', match_filename, liga, home, away)
                input('')
                print('Continuar')
            else:
                print(
                    'DESCARTADO MOMIOS',
                    liga,
                    home,
                    away,
                    f'home: {matches["home_nmatches"]}',
                    f'away: {matches["away_nmatches"]}',
                    f'face: {matches["face_nmatches"]}'
                )
                pprint.pprint(momios)
        else:
            print(
                'DESCARTADO',
                liga,
                home,
                away,
                f'home: {matches["home_nmatches"]}',
                f'away: {matches["away_nmatches"]}',
                f'face: {matches["face_nmatches"]}'
            )
        n += 1
    f.close()

    if len(result) > 0:
        print(f'Partidos Procesados {len(resultados_ordenados)} {fecha}')
        with open(f'{source_path}/{db_file}.json', 'w') as f:
            f.write(json.dumps(result))
    if len(result_pais) > 0:
        with open(f'{source_path}/{db_file}_pais.json', 'w') as f:
            f.write(json.dumps(result_pais))


if __name__ == "__main__":
    overwrite = args.over
    if args.tomorrow:
        main(hoy=False, overwrite=overwrite)
    else:
        main(hoy=True, overwrite=overwrite)
