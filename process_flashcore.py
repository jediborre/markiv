import re
import os
import json
import pprint # noqa
import logging
import datetime
import argparse
from web import Web
from fuzzywuzzy import fuzz
from bs4 import BeautifulSoup
from text_unidecode import unidecode
# https://app.dataimpulse.com/plans/create-new
# https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json
# 131.0.6778.85
# .venv/Scripts/Activate.ps1
# chrome --remote-debugging-port=9222 --user-data-dir="C:\Log"
# python db/flashcore.py
web = None
opened_web = False
parser = argparse.ArgumentParser(description="Solicita partidos de hoy o mañana de flashscore") # noqa
parser.add_argument('--today', action='store_true', help="Partidos Hoy")
parser.add_argument('--tomorrow', action='store_true', help="Partidos Mañana")
parser.add_argument('--over', action='store_true', help="Sobreescribir")
args = parser.parse_args()
script_path = os.path.dirname(os.path.abspath(__file__))
log_filepath = os.path.join(script_path, 'web_markiv.log')
result_path = os.path.join(script_path, 'result', 'matches')
source_path = os.path.join(script_path, 'db', 'flashscore')
tmp_path = os.path.join(script_path, 'tmp')
if not os.path.exists(result_path):
    os.makedirs(result_path)
if not os.path.exists(tmp_path):
    os.makedirs(tmp_path)
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


def limpia_nombre(nombre, post=True):
    nombre = re.sub(r'\s+', ' ', re.sub(r'\.|\/|\(|\)', '', nombre)).strip()
    nombre = unidecode(nombre)
    return nombre


def parse_section(matches, team=None, team_name=None, liga=None):
    hechos = 0
    concedidos = 0
    p35, p45 = 0, 0
    result_matches = []
    for match in matches:
        date = match.find('span', class_='h2h__date').text

        event = match.find('span', class_='h2h__event')
        league_name = event['title']
        league_name = re.sub(r'\s*\([^)]*\)$', '', league_name)
        league_name = re.sub(r'\s+$', '', league_name)

        home_team = match.find('span', class_='h2h__homeParticipant')
        home_team_name = home_team.find('span', class_='h2h__participantInner').text # noqa

        away_team = match.find('span', class_='h2h__awayParticipant')
        away_team_name = away_team.find('span', class_='h2h__participantInner').text # noqa

        result_span = match.find('span', class_='h2h__result')
        scores = result_span.find_all('span')

        home_FT = int(scores[0].text)
        away_FT = int(scores[1].text)

        FT = home_FT + away_FT

        if liga:
            similarity_threshold = 80
            liga_clean = limpia_nombre(liga)
            league_name_clean = limpia_nombre(league_name)
            liga_similarity = fuzz.ratio(liga_clean, league_name_clean)
            liga_psimilarity = fuzz.partial_ratio(liga_clean, league_name_clean) # noqa
            liga_similar = liga_similarity >= similarity_threshold
            liga_psimilar = liga_psimilarity >= similarity_threshold
            if liga_similar or liga_psimilar:
                if len(result_matches) < 5:
                    if FT <= 3:
                        p35 += 1
                    if FT <= 4:
                        p45 += 1

                    if team_name:
                        if home_team_name == team_name:
                            hechos = hechos + home_FT
                            concedidos = concedidos + away_FT
                        else:
                            hechos = hechos + away_FT
                            concedidos = concedidos + home_FT

                    print(f'{team}: {len(result_matches)} | "{league_name}" "{home_team_name}"') # noqa
                    result_matches.append({
                        'ft': FT,
                        'date': date,
                        'liga': league_name,
                        'home': home_team_name,
                        'home_ft': home_FT,
                        'away': away_team_name,
                        'away_ft': away_FT,
                    })
            else:
                if len(result_matches) < 5:
                    print(f'{team}: {len(result_matches)} | Liga no coincide: "{liga}":{liga_similarity} "{league_name}":{liga_psimilarity}') # noqa
        else:
            if len(result_matches) < 5:
                result_matches.append({
                    'ft': FT,
                    'date': date,
                    'liga': league_name,
                    'home': home_team_name,
                    'home_ft': home_FT,
                    'away': away_team_name,
                    'away_ft': away_FT,
                })
            else:
                break
    result = {
        'matches': result_matches
    }
    juegos = len(result_matches)
    if juegos > 0:
        result['p35'] = p35 / juegos
        result['p45'] = p45 / juegos
    result['match_home'] = team_name
    if team_name:
        result['hechos'] = hechos
        result['concedidos'] = concedidos
        if juegos > 0:
            result['p_hechos'] = hechos / juegos
            result['p_concedidos'] = concedidos / juegos
        return result
    else:
        return result


def click_more(web, team, team_name, liga):
    sections = web.CLASS('h2h__section', multiples=True)
    section = sections[0] if team == 'home' else sections[1]
    result = parse_matches_html(web.source(), team, team_name=team_name, liga=liga) # noqa
    num_matches = result['home_nmatches'] if team == 'home' else result['away_nmatches'] # noqa
    print(f'{team} matches: {num_matches} {result["OK"]}')
    if not result['OK'] and section.EXIST_CLASS('showMore'):
        btn_showMore = section.CLASS('showMore')
        btn_showMore.scroll_to()
        if not btn_showMore.click():
            web.scrollY(-150)
            btn_showMore.click()
            print('ShowMore can\'t click')
        else:
            print('ShowMore click')
        web.wait()
        click_more(web, team, team_name, liga)
    else:
        print(f'{team} matches: {num_matches} DONE')


def parse_matches_html(html, team, team_name='', home='', away='', liga=''):
    soup = BeautifulSoup(html, 'html.parser')
    sections = soup.find_all('div', class_='h2h__section')

    tmp_matches_home = sections[0].find('div', class_='rows') if len(sections) > 0 else [] # noqa
    tmp_matches_away = sections[1].find('div', class_='rows') if len(sections) > 0 else [] # noqa
    tmp_matches_face = sections[2].find('div', class_='rows') if len(sections) > 0 else [] # noqa

    tmp_matches_home = tmp_matches_home.find_all('div', class_='h2h__row')
    tmp_matches_away = tmp_matches_away.find_all('div', class_='h2h__row')
    tmp_matches_face = tmp_matches_face.find_all('div', class_='h2h__row')

    if team == 'all':
        home_matches = parse_section(tmp_matches_home, team, home, liga)
        away_matches = parse_section(tmp_matches_away, team, away, liga)
        face_matches = parse_section(tmp_matches_face)

        OK = len(home_matches['matches']) == 5 and len(away_matches['matches']) == 5 and len(face_matches['matches']) > 3 # noqa
        return {
            'OK': OK,
            'home_matches': home_matches,
            'away_matches': away_matches,
            'face_matches': face_matches,
            'home_nmatches': len(home_matches['matches']),
            'away_nmatches': len(away_matches['matches']),
            'face_nmatches': len(face_matches['matches'])
        }
    elif team == 'home':
        team_matches = parse_section(tmp_matches_home, team, team_name, liga)
        ok = len(team_matches['matches']) == 5
        # print(f'Home Matches: {len(team_matches["matches"])} {ok}')
    elif team == 'away':
        team_matches = parse_section(tmp_matches_away, team, team_name, liga)
        ok = len(team_matches['matches']) == 5
        # print(f'Away Matches: {len(team_matches["matches"])} {ok}')
    elif team == 'face':
        team_matches = parse_section(tmp_matches_face)
        ok = len(team_matches['matches']) > 3
        # print(f'Face Matches: {len(team_matches["matches"])} {ok}')
    return {
        'OK': ok,
        f'{team}_matches': team_matches,
        f'{team}_nmatches': len(team_matches['matches']),
    }


def get_partidos(link, filename, home, away, liga, overwrite=False):
    global tmp_path
    global opened_web, web, proxy_url
    filename = re.sub(r'-|:', '', filename)
    html_path = os.path.join(tmp_path, filename) + '.html'
    print('Procesando Partido', link, html_path, os.path.exists(html_path))
    if not os.path.exists(html_path) or overwrite:
        if not opened_web:
            web = Web(proxy_url=proxy_url, url=link)
        else:
            web.open(link, True)
        web.wait_Class('h2h__section', 20)
        result = parse_matches_html(web.source(), 'face')
        print(f'VS Matches: {result["face_nmatches"]}')
        if result['face_nmatches'] > 3:
            print('More Home matches...')
            click_more(web, 'home', home, liga)
            print('More Away matches...')
            click_more(web, 'away', away, liga)
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(web.source())
    with open(html_path, 'r', encoding='utf-8') as file:
        return parse_matches_html(file, 'all', home=home, away=away, liga=liga)


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
        open(flashcore_page_filename, 'w', encoding='utf-8').write(web.source()) # noqa
    else:
        if overwrite:
            web = Web(proxy_url=proxy_url, url=mobile_url)
            web.wait_ID('main', 5)
            opened_web = True
            open(flashcore_page_filename, 'w', encoding='utf-8').write(web.source()) # noqa

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
        matches = get_partidos(link, f'{fecha}{hora}_{n}', home, away, liga, overwrite) # noqa
        if matches['OK']:
            f.write(f"{fecha},{hora},{pais},{liga},{home},{away},{link}\n")
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
                'home_matches': matches['home_matches'],
                'away_matches': matches['away_matches'],
                'face_matches': matches['face_matches']
            }
            if pais not in result_pais:
                result_pais[pais] = []
            result[reg['id']] = reg
            result_pais[pais].append(reg)
            match_filename = f'{re.sub(r"-", "", fecha)}{re.sub(r":", "", hora)}_{n}.json' # noqa
            result_file = f'{result_path}/{match_filename}'
            if os.path.exists(result_file) and overwrite: # noqa
                os.remove(result_file)
            g = open(result_file, 'w', encoding='utf-8') # noqa
            g.write(json.dumps(reg))
            g.close()
            print('OK', match_filename, liga, home, away)
        else:
            print(f'DESCARTADO home: {matches["home_nmatches"]} away: {matches["away_nmatches"]} face: {matches["face_nmatches"]}', liga, home, away) # noqa
        n += 1
        print('Pausa')
        input('')
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
