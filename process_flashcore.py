import re
import os
import pprint # noqa
import logging
import datetime
import argparse
from web import Web
from utils import prepare
from utils import save_matches
from parse import parse_team_matches
from parse import parse_odds_ambos
from parse import parse_odds_1x2
from parse import parse_odds_goles
from parse import parse_all_matches


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


def get_tean_matches(filename, link, home, away, liga, overwrite=False):
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
    global path_tmp_html
    global opened_web, web, proxy_url
    nom = 'Ambos'
    filename = f'{filename}_{nom}.html'
    html_path = os.path.join(path_tmp_html, filename)
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
    global path_tmp_html
    global opened_web, web, proxy_url
    nom = '1x2'
    filename = f'{filename}_{nom}.html'
    html_path = os.path.join(path_tmp_html, filename)
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


def get_all_matches(filename, matches_link, overwrite=False):
    global path_html
    global opened_web, web, proxy_url

    html_path = os.path.join(path_html, filename)
    if overwrite:
        if os.path.exists(html_path):
            os.remove(html_path)

    if not os.path.exists(html_path):
        if not opened_web:
            web = Web(
                proxy_url=proxy_url,
                url=matches_link
            )
            opened_web = True
        else:
            web.open(matches_link)
            opened_web = False

        web.wait_ID('main', 5)
        opened_web = True
        web.save(html_path)

    with open(html_path, 'r', encoding='utf-8') as html:
        return parse_all_matches(html)


def main(hoy=False, overwrite=False):
    global opened_web, web, proxy_url
    global matches_today_url, matches_tomorrow_url
    global path_result, path_csv, path_json, path_html

    today = datetime.datetime.today()
    if hoy:
        tomorrow = today
        fecha = today.strftime('%Y-%m-%d')
        date_filename = today.strftime('%Y%m%d')
        url = matches_today_url
    else:
        fecha = tomorrow.strftime('%Y-%m-%d')
        tomorrow = (today + datetime.timedelta(days=1))
        date_filename = tomorrow.strftime('%Y%m%d')
        url = matches_tomorrow_url

    matches_csv = os.path.join(path_csv, f'{date_filename}_matches.csv')
    matches_html = os.path.join(path_html, f'{date_filename}_matches.html')
    matches_result = os.path.join(path_result, f'{date_filename}.json')
    matches_pais_result = os.path.join(path_result, f'{date_filename}_pais.json') # noqa

    n = 1
    result, result_pais = {}, {}
    day_matches = get_all_matches(matches_html, url, overwrite)
    if len(day_matches) == 0:
        return

    f = open(matches_csv, 'w', encoding='utf-8')
    f.write("fecha,hora,pais,liga,local,visitante,link\n")
    for pais, liga, hora, home, away, link, link_momios_1x2, link_momios_goles, link_momios_ambos in day_matches: # noqa
        match_filename = f'{n}_{date_filename}{re.sub(r":", "", hora)}'
        match_json = os.path.join(path_json, f'{match_filename}.json')
        matches = get_tean_matches(match_filename, link, home, away, liga, overwrite) # noqa
        if matches['OK']:
            momios = get_momios(match_filename, link_momios_1x2, link_momios_goles, link_momios_ambos, overwrite) # noqa
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
                save_matches(match_json, reg, overwrite)
                logging.info(f'OK {match_filename} {liga} | {home} - {away}')
                input('')
                print('Continuar')
            else:
                logging.info(f'DESCARTADO MOMIOS {liga} | {home}:{matches["home_nmatches"]} - {away}:{matches["away_nmatches"]} VS:{matches["face_nmatches"]}') # noqa
                pprint.pprint(momios)
        else:
            logging.info(f'DESCARTADO {liga} | {home}:{matches["home_nmatches"]} - {away}:{matches["away_nmatches"]} VS:{matches["face_nmatches"]}') # noqa
        n += 1
    f.close()

    logging.info(f'PARTIDOS {len(day_matches)} {fecha}')
    if len(result) > 0:
        save_matches(matches_result, result, overwrite)

    if len(result_pais) > 0:
        save_matches(matches_pais_result, result_pais, overwrite)


if __name__ == "__main__":
    overwrite = args.over
    if args.tomorrow:
        main(hoy=False, overwrite=overwrite)
    else:
        main(hoy=True, overwrite=overwrite)
