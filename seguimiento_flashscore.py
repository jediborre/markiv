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


def get_current_scores(web):
    if pathexist('partidos_beta.htm'):
        html = open('partidos_beta.htm', 'r', encoding='utf-8').read()
    else: # noqa
        web.open(url_matches_today)
        web.wait_ID('main', 5)
        eliminar_publicidad(web)

        html = web.source()
        # open('partidos_beta.htm', 'w', encoding='utf-8').write(html)

    if not html:
        print('No se pudo obtener el HTML de la página.')
        return {}

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

                if ':' in hora:
                    hora_display = hora[:5]
                else:
                    hora_display = hora

                score_link_tag = partido_actual.find_next_sibling('a')

                if score_link_tag:
                    score = score_link_tag.get_text(strip=True)
                    id_match = score_link_tag['href']
                    link = f'{domain}{id_match}#/h2h/overall'

                    team_text_parts = []
                    home_red_card = False
                    away_red_card = False

                    current_node = partido_actual.next_sibling
                    while current_node and current_node != score_link_tag:
                        if isinstance(current_node, str):
                            team_text_parts.append(current_node.strip())
                        elif current_node.name == 'img':
                            img_classes = current_node.get('class', [])
                            if 'rcard-1' in img_classes:
                                home_red_card = True
                            elif 'rcard-2' in img_classes:
                                away_red_card = True
                        current_node = current_node.next_sibling

                    teams_raw = ' '.join(filter(None, team_text_parts)).strip()
                    teams_raw = re.sub(r'\s+', ' ', teams_raw)
                    # teams_raw = re.sub(r'\s*-\s*', ' - ', teams_raw)

                    try:
                        home, away = teams_raw.split(' - ')
                        home = home.strip()
                        away = away.strip()
                    except ValueError:
                        # print(f"Skipping match due to team parsing error: liga: {nombre_liga} | '{teams_raw}'") # noqa
                        partido_actual = score_link_tag.find_next_sibling()
                        continue

                    # print(
                    #     f"{nombre_liga} {hora_display} | {home} vs {away} {score} |"
                    #     f" RC Home: {'SI' if home_red_card else 'NO'},
                    #     f"RC Away: {'SI' if away_red_card else 'NO'} | {id_match}"
                    # )
                    if not aplazado:
                        if nombre_liga not in matches:
                            matches[nombre_liga] = []
                        match = {
                            'hora': hora_display,
                            'home': home,
                            'away': away,
                            'score': score,
                            'url': link,
                            'home_red_card': home_red_card,  # Added
                            'away_red_card': away_red_card,  # Added
                        }
                        matches[nombre_liga].append(match)
                    else:
                        pass
                        # Aplazado match
                        # print(f'{nombre_liga} {hora_display} | {home} vs {away} APLAZADO') # noqa
                else:
                    print(f"No score link (<a> tag) found immediately after span: {partido_actual.get_text(strip=True)}") # noqa

            partido_actual = partido_actual.find_next_sibling()
    return matches


def get_score(m, _matches):
    liga = m["liga"]
    home = m["home"]
    away = m["away"]
    if liga in _matches:
        # pprint.pprint(_matches[liga])  # noqa
        # [{
        #   'hora': '17:00',
        #   'home': 'Juárez',
        #   'away': 'Cruz Azul',
        #   'score': '1:0',
        #   'home_red_card': False,
        #   'away_red_card': False,
        #   'url': 'https://www.flashscore.com.mx/partido/OWSpVMH6/#/h2h/overall'
        # }] # noqa
        record = next((match for match in _matches[liga] if match['home'] == home and match['away'] == away), None) # noqa
        if record:
            home_score, away_score = record['score'].split(':') if record else (None, None) # noqa
            _home_score, _away_score = home_score, away_score
            home_score = int(home_score.strip()) if home_score != '-' else 0
            away_score = int(away_score.strip()) if away_score != '-' else 0
            red_card_home = record.get('home_red_card', False)  # Added
            red_card_away = record.get('away_red_card', False)
            record['hora'] == 'Aplazado'
            minuto = record['hora'] if ':' not in record['hora'] else None # noqa
            if minuto:
                # print(pais, hora, home, home_score, away, away_score, minuto) # noqa
                return [home_score, away_score, red_card_home, red_card_away, minuto]
            else:
                if _home_score == '-' and _away_score == '-':
                    return [_home_score, _away_score, red_card_home, red_card_away, 'NO']
                # print(pais, home, home_score, away, away_score, 'FT')
                return [home_score, away_score, red_card_home, red_card_away, 'FT']
        else:
            print('get_score no encontrado record', liga, home, away)
            return None
    else:
        print('get_score no encontrado liga para', liga, home, away)
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
        f'{gana} -3.5 | {home} - {away} | {home_score} - {away_score}',
    ]
    for chat_id in TELEGRAM_CHAT_ID:
        send_text(
            bot,
            chat_id,
            '\n'.join(msj),
            markup
        )


def inicio(bot, id_partido, hora, minuto, pais, liga, home, away, home_score, away_score, quien): # noqa
    print(f'{id_partido} {hora} | {minuto} | {pais} {liga} | {home} vs {away} {home_score} - {away_score} INICIO') # noqa
    markup = None
    # markup = types.InlineKeyboardMarkup()
    # if link:
    #     link_boton = types.InlineKeyboardButton('Apostar', url=link) # noqa
    #     markup.add(link_boton)
    msj = [
        f'INICIO {hora} | {pais} {home} - {away}',
    ]
    for chat_id in TELEGRAM_CHAT_ID:
        send_text(
            bot,
            chat_id,
            '\n'.join(msj),
            markup
        )


def pierde(bot, id_partido, hora, minuto, pais, liga, home, away, home_score, away_score, quien): # noqa
    print(f'{id_partido} {hora} | {minuto} | {pais} {liga} | {home} vs {away} {home_score} - {away_score} GOL PIERDE') # noqa
    markup = None
    # markup = types.InlineKeyboardMarkup()
    # if link:
    #     link_boton = types.InlineKeyboardButton('Apostar', url=link) # noqa
    #     markup.add(link_boton)
    msj = [
        'PIERDE -3.5',
        f'GOL {minuto} {quien}',
        f'{home} - {away} | ',
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
        f'GOL {minuto} {quien} {home_score} - {away_score}',
    ]
    for chat_id in TELEGRAM_CHAT_ID:
        send_text(
            bot,
            chat_id,
            '\n'.join(msj),
            markup
        )


def roja(bot, id_partido, hora, minuto, pais, liga, home, away, home_score, away_score, quien): # noqa
    print(
        f"{id_partido} {hora} |"
        f"{minuto} | {pais} {liga} | "
        f"{home} vs {away} {home_score} - {away_score} ROJA"
    )
    markup = None
    # markup = types.InlineKeyboardMarkup()
    # if link:
    #     link_boton = types.InlineKeyboardButton('Apostar', url=link) # noqa
    #     markup.add(link_boton)
    msj = [
        f'ROJA {minuto} {quien} {home_score} - {away_score}',
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
                        "red_card_home": False,
                        "red_card_away": False,
                        "termino": False,
                        "gana": None,
                        "sigue": True,
                        "minuto": None,
                        "seguimiento": []
                    }
                if resultados[id_partido]['sigue']:
                    score = get_score(m, _matches)
                    if score:
                        home_score, away_score, red_card_home, red_card_away, minuto = score # noqa
                        if  resultados[id_partido]['red_card_home'] != red_card_home or resultados[id_partido]['red_card_away'] != red_card_away: # noqa
                            resultados[id_partido]['red_card_home'] = red_card_home
                            resultados[id_partido]['red_card_away'] = red_card_away
                            quien = home if red_card_home else away
                            roja(bot, id_partido, hora, minuto, pais, liga, home, away, home_score, away_score, quien) # noqa

                        if home_score != resultados[id_partido]['home_score'] or away_score != resultados[id_partido]['away_score']: # noqa
                            quien = ''
                            if resultados[id_partido]['home_score'] == '-':
                                inicio(bot, id_partido, hora, minuto, pais, liga, home, away, home_score, away_score, quien) # noqa
                            else:
                                score = home_score + away_score
                                if resultados[id_partido]['home_score'] != home_score:
                                    quien = home
                                if away_score != resultados[id_partido]['away_score']:
                                    quien = away
                                if type(score) is int and score < 4:
                                    gol(bot, id_partido, hora, minuto, pais, liga, home, away, home_score, away_score, quien) # noqa
                                else:
                                    if type(score) is str:
                                        print(f'{id_partido} {hora} | {minuto} | {pais} {liga} | {home} vs {away} AUN NO COMIENZA') # noqa
                                    else:
                                        resultados[id_partido]['gana'] = False
                                        resultados[id_partido]['sigue'] = False
                                        pierde(bot, id_partido, hora, minuto, pais, liga, home, away, home_score, away_score, quien) # noqa

                        else:
                            score = home_score + away_score
                            if type(score) is str:
                                print(f'{id_partido} {hora} | {minuto} | {pais} {liga} | {home} vs {away} AUN NO COMIENZA') # noqa
                            else:
                                print(f'{id_partido} {hora} | {minuto} | {pais} {liga} | {home} vs {m["away"]} {home_score} - {away_score}') # noqa

                        resultados[id_partido]['minuto'] = minuto
                        resultados[id_partido]['home_score'] = home_score
                        resultados[id_partido]['away_score'] = away_score
                        if minuto == 'FT':
                            resultados[id_partido]['sigue'] = False
                            resultados[id_partido]['termino'] = True
                            # Set gana based on final score
                            final_total = home_score + away_score
                            resultados[id_partido]['gana'] = final_total < 4
                            ft(bot, id_partido, hora, pais, liga, home, away, home_score, away_score) # noqa
                        resultados[id_partido]['seguimiento'].append(score)
                    else:
                        resultados[id_partido]['sigue'] = False
                        print(f'{id_partido} -> {m["liga"]} {home} vs {m["away"]} Hora: {hora} No encontrado') # noqa
                        # input('Continuar?')

        lost = []
        complete = []
        _seguimiento = []
        for id_partido, data in resultados.items():
            complete.append(data['termino'])
            if data['gana'] is not None:
                lost.append(data['gana'])  # Add True if won, False if lost
            else:
                _seguimiento.append(data['sigue'])

        # Only exit if ALL matches have been decided (gana is not None) AND ALL have lost
        if len(lost) == len(resultados) and not any(lost):
            print('Todos los partidos han perdido -3.5')
            if web is not None:
                web.close()
            return

        if all(complete):
            print('Todos los partidos han terminado.')
            if web is not None:
                web.close()
            return
        else:
            if any(_seguimiento):
                time.sleep(60)  # Espera 1 minuto antes de volver a verificar
                seguimiento(path_file, filename, web, bot, botregs, matches, resultados) # noqa
            else:
                print('No hay partidos en seguimiento.')
                if web is not None:
                    web.close()
                return

    except KeyboardInterrupt:
        print('\nFin...')
        if web is not None:
            web.close()

    if web is not None:
        web.close()


if __name__ == '__main__':
    args = parser.parse_args()
    filename = args.file
    fecha = filename.split('.')[0][:8]
    path_file = path(path_result, fecha, 'seguimiento', filename)

    if pathexist(path_file):
        logging.info(f'Seguimiento Friday {filename} > {path_file}\n')
        if not pathexist('partidos_beta.htm'):
            web = Web(multiples=True)
        else:
            web = None
        matches = get_json_dict(path_file)
        wks = gsheet('Bot')
        bot_regs = wks.get_all_values(returnas='matrix')
        bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
        seguimiento(path_file, filename, web, bot, bot_regs, matches)
        if web is not None:
            print('Cerrando WebDriver...')
            web.quit()

    else:
        logging.error(f'Seguimiento Friday Archivo {path_file} no encontrado')
        raise FileNotFoundError(f'Seguimiento Friday Archivo {path_file} no encontrado')
