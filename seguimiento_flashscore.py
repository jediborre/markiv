import re
import os
import sys
import time
import pprint # noqa
import logging
import argparse
import telebot
from web import Web
from utils import gsheet
from utils import send_text
from bs4 import BeautifulSoup
from utils import busca_id_bot
from utils import get_json_dict
from utils import path, pathexist
from utils import prepare_paths_ok

# https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json

url_matches_today = 'https://m.flashscore.com.mx/'

sys.stdout.reconfigure(encoding='utf-8')

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID').split(',')

path_result, path_ok = prepare_paths_ok()

parser = argparse.ArgumentParser(description="Solicita partidos de hoy o mañana de flashscore") # noqa
parser.add_argument('file', type=str, help='Archivo de Partidos Flashscore')
args = parser.parse_args()


def eliminar_publicidad(web: Web):
    if web.EXIST_ID('pmp-sticky-footer'):
        # print('Eliminando sticky footer...')
        web.REMOVE_ID('pmp-sticky-footer')
    else:
        print('Sticky footer no encontrado, continuando...')


def get_current_scores(web: Web):
    web.open(url_matches_today)
    web.wait_ID('main', 5)
    eliminar_publicidad(web)

    html = web.source()
    matches = {}
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
    domain = 'https://www.flashscore.com.mx'
    soup = BeautifulSoup(html, 'html.parser')
    ligas = soup.find_all('h4')
    for liga in ligas:
        tmp_liga = ''.join([str(content) for content in liga.contents if not content.name]) # noqa
        pais, nombre_liga = tmp_liga.split(': ')
        nombre_liga = re.sub(r'\s+$', '', nombre_liga)
        partido_actual = liga.find_next_sibling()

        if any([x in nombre_liga.lower() for x in filter_ligas]):
            continue

        while partido_actual and partido_actual.name != 'h4':
            if partido_actual.name == 'span':
                hora = partido_actual.get_text(strip=True)
                aplazado = 'Aplazado' in hora
                hora = hora[:5]
                equipos = partido_actual.find_next_sibling(string=True).strip() # noqa
                try:
                    home, away = equipos.split(' - ')
                    score = partido_actual.find_next_sibling('a').get_text(strip=True) # noqa
                    link = partido_actual.find_next_sibling('a')['href']
                    link = f'{domain}{link}#/h2h/overall'
                    if not aplazado:
                        if nombre_liga not in matches:
                            matches[nombre_liga] = []
                        matches[nombre_liga].append({
                            'hora': hora,
                            'home': home,
                            'away': away,
                            'score': score,
                            'url': link,
                        })
                except ValueError:
                    pass
            partido_actual = partido_actual.find_next_sibling()
    return matches


def get_score(m, _matches):
    liga = m["liga"]
    home = m["home"]
    away = m["away"]
    hora = m["hora"]
    pais = m["pais"]
    if liga in _matches:
        # [{'hora': '17:00', 'home': 'Juárez', 'away': 'Cruz Azul', 'score': '1:0', 'url': 'https://www.flashscore.com.mx/partido/OWSpVMH6/#/h2h/overall'}, {'hora': '19:00', 'home': 'Toluca', 'away': 'Monterrey', 'score': '1:1', 'url': 'https://www.flashscore.com.mx/partido/M7WTY4Is/#/h2h/overall'}, {'hora': "80'", 'home': 'Atlas', 'away': 'León', 'score': '1:0', 'url': 'https://www.flashscore.com.mx/partido/UXZyXrmf/#/h2h/overall'}] # noqa
        record = next((match for match in _matches[liga] if match['home'] == home and match['away'] == away), None) # noqa
        if record:
            home_score, away_score = record['score'].split(':') if record else (None, None) # noqa
            # todo implementa inicio juego
            home_score = int(home_score.strip()) if home_score != '-' else 0
            away_score = int(away_score.strip()) if away_score != '-' else 0
            record['hora'] == 'Aplazado'
            minuto = record['hora'] if ':' not in record['hora'] else None # noqa
            if minuto:
                # print(pais, hora, home, home_score, away, away_score, minuto) # noqa
                return [home_score, away_score, minuto]
            else:
                # print(pais, home, home_score, away, away_score, 'FT')
                return [home_score, away_score, 'FT']
        else:
            print(pais, home, away, 'No encontrado')
            return None
    else:
        print(pais, hora, home, away, 'No encontrado')
        return None

def ft(bot, id_partido, hora, pais, liga, home, away, home_score, away_score): # noqa
    print(f'{id_partido} {hora} | {pais} {liga} | {home} vs {away} {home_score} - {away_score} FT') # noqa
    markup = None
    # markup = types.InlineKeyboardMarkup()
    # if link:
    #     link_boton = types.InlineKeyboardButton('Apostar', url=link) # noqa
    #     markup.add(link_boton)
    ft = home_score + away_score
    gana = ''
    if ft < 4:
        gana = 'GANA'
    else:
        gana = 'PIERDE'

    msj = [
        f'FT {gana} -3.5',
        f'{home} - {away} | FT: {ft}',
        f'{home_score} - {away_score}',
    ]
    for chat_id in TELEGRAM_CHAT_ID:
        send_text(
            bot,
            chat_id,
            '\n'.join(msj),
            markup
        )


def gol(bot, id_partido, hora, minuto, pais, liga, home, away, home_score, away_score, quien): # noqa
    print(f'{id_partido} {hora} | {minuto} | {pais} {liga} | {home} vs {away} {home_score} - {away_score} GOL') # noqa
    markup = None
    # markup = types.InlineKeyboardMarkup()
    # if link:
    #     link_boton = types.InlineKeyboardButton('Apostar', url=link) # noqa
    #     markup.add(link_boton)
    msj = [
        f'GOL {minuto} {quien}',
        f'{home_score} - {away_score}',
        f'{home} - {away}',
    ]
    for chat_id in TELEGRAM_CHAT_ID:
        send_text(
            bot,
            chat_id,
            '\n'.join(msj),
            markup
        )


def seguimiento(path_file: str, filename: str, web, bot, botregs, matches, resultados=None): # noqa
    global TELEGRAM_CHAT_ID
    if resultados is None:
        resultados = {}
    _matches = get_current_scores(web)
    try:
        for m in matches:
            id_partido = m["id"]
            home = m["home"]
            away = m["away"]
            hora = m["hora"]
            liga = m["liga"]
            pais = m["pais"]
            hora = m["hora"]
            row = busca_id_bot(bot_regs, id_partido)
            if row:
                bot_reg = bot_regs[row - 1] # noqa

                # apuesta = bot_reg[6]
                # if 'OK' in apuesta:
                if id_partido not in resultados:
                    resultados[id_partido] = {
                        "liga": liga,
                        "home": home,
                        "away": away,
                        "hora": hora,
                        "pais": pais,
                        "home_score": 0,
                        "away_score": 0,
                        'termino': False,
                        'minuto': None,
                        'seguimiento': []
                    }
                score = get_score(m, _matches)
                if score:
                    home_score, away_score, minuto = score
                    if home_score != resultados[id_partido]['home_score'] or away_score != resultados[id_partido]['away_score']: # noqa
                        quien = ''
                        if resultados[id_partido]['home_score'] != home_score:
                            quien = home
                        if away_score != resultados[id_partido]['away_score']:
                            quien = away
                        gol(bot, id_partido, hora, minuto, pais, liga, home, away, home_score, away_score, quien) # noqa
                    else:
                        print(f'{id_partido} {hora} | {minuto} | {pais} {liga} | {home} vs {m["away"]} {home_score} - {away_score}') # noqa
                    resultados[id_partido]['home_score'] = home_score
                    resultados[id_partido]['away_score'] = away_score
                    resultados[id_partido]['minuto'] = minuto
                    if minuto == 'FT':
                        resultados[id_partido]['termino'] = True
                        ft(bot, id_partido, hora, pais, liga, home, away, home_score, away_score) # noqa
                    resultados[id_partido]['seguimiento'].append(score)
                # print(f'{id_partido} -> {m["liga"]} {home} vs {m["away"]} Hora: {hora}') # noqa
        complete = []
        for id_partido, data in resultados.items():
            complete.append(data['termino'])

        if all(complete):
            print('Todos los partidos han terminado.')
            web.close()
            return
        else:
            # pprint.pprint(resultados)
            time.sleep(60)  # Espera 1 minuto antes de volver a verificar
            seguimiento(path_file, filename, web, bot, botregs, matches, resultados) # noqa

    except KeyboardInterrupt:
        print('\nFin...')
        web.close()
        exit(0)
    web.close()


if __name__ == '__main__':
    args = parser.parse_args()
    filename = args.file
    fecha = filename.split('.')[0][:8]
    path_file = path(path_result, fecha, filename)

    if pathexist(path_file):
        logging.info(f'Seguimiento Friday {filename} > {path_file}\n')
        web = Web(multiples=True)
        matches = get_json_dict(path_file)
        wks = gsheet('Bot')
        bot_regs = wks.get_all_values(returnas='matrix')
        bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
        seguimiento(path_file, filename, web, bot, bot_regs, matches)
    else:
        logging.error(f'Seguimiento Friday Archivo {path_file} no encontrado')
        raise FileNotFoundError(f'Seguimiento Friday Archivo {path_file} no encontrado')
