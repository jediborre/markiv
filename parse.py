import re
import os
import random
import pprint
import logging
from web import Web
from fuzzywuzzy import fuzz
from bs4 import BeautifulSoup
from datetime import datetime
from utils import path
from utils import convert_dt
from utils import get_percent
from utils import save_matches
from utils import limpia_nombre
from utils import decimal_american
from text_unidecode import unidecode
from filtros import get_ligas_google_sheet
from send_flashscore import get_match_error_short

domain = 'https://www.flashscore.com.mx'


def get_marcador_ft(web, debug=False):
    goles_fallos = [
        'penalti fallado',
        'gol anulado',
        'fuera de juego',
        'fueras de juego'
    ]
    try:
        soup = BeautifulSoup(web.source(), 'html.parser')
        goles, rojas_home, rojas_away = [], [], []
        eventos_home = soup.find_all('div', class_='smv__participantRow smv__homeParticipant') # noqa
        if len(eventos_home) > 0:
            for evento in eventos_home:
                minuto = evento.find('div', class_='smv__timeBox').text.strip().replace("'", '') # noqa
                if minuto != '':
                    if ':' not in minuto:
                        minuto = int(minuto) if '+' not in minuto else int(minuto[:2]) # noqa
                    else:
                        minuto = minuto.split(':')
                        minuto = int(minuto[0]) if '+' not in minuto[0] else int(minuto[0][:2]) # noqa
                    icono = evento.find('div', class_='smv__incidentIcon') # noqa
                    if icono:
                        svg = icono.find('svg')
                        if svg:
                            incident_icon = svg.get('class')
                            # incident_icon_goal = svg.get('data-testid') # noqa
                            if 'card-ico' in incident_icon:
                                if 'yellowCard-ico' not in incident_icon: # noqa
                                    # incident_icon = 'redCard-ico'
                                    rojas_home.append([minuto, 'Home']) # noqa
                            else:
                                gol_text = icono.text.lower()
                                if debug:
                                    print('GOAL Home', gol_text, minuto)
                                if all([x not in gol_text for x in goles_fallos]): # noqa
                                    goles.append([minuto, 'Home'])

        eventos_away = soup.find_all('div', class_='smv__participantRow smv__awayParticipant') # noqa
        if len(eventos_away) > 0:
            for evento in eventos_away:
                minuto = evento.find('div', class_='smv__timeBox').text.strip().replace("'", '') # noqa
                if minuto != '':
                    if ':' not in minuto:
                        minuto = int(minuto) if '+' not in minuto else int(minuto[:2]) # noqa
                    else:
                        minuto = minuto.split(':')
                        minuto = int(minuto[0]) if '+' not in minuto[0] else int(minuto[0][:2]) # noqa
                    icono = evento.find('div', class_='smv__incidentIcon') # noqa
                    if icono:
                        svg = icono.find('svg')
                        if svg:
                            incident_icon = svg.get('class')
                            # incident_icon_goal = svg.get('data-testid') # noqa
                            if 'card-ico' in incident_icon:
                                if 'yellowCard-ico' not in incident_icon: # noqa
                                    rojas_away.append([minuto, 'Away']) # noqa
                            else:
                                gol_text = icono.text.lower()
                                if debug:
                                    print('GOAL Away', gol_text, minuto)
                                if all([x not in gol_text for x in goles_fallos]): # noqa
                                    goles.append([minuto, 'Away']) # noqa

        total_goles = str(len(goles))
        goles_ordenados = sorted(goles, key=lambda x: x[0])
        rojas_home_ordenadas = sorted(rojas_home, key=lambda x: x[0]) # noqa
        rojas_away_ordenadas = sorted(rojas_away, key=lambda x: x[0]) # noqa

        rojas_sheet = []
        goles_sheet = ['-', '-', '-', '-']
        if len(goles_ordenados) > 0:
            for n, (min, equipo) in enumerate(goles_ordenados): # noqa
                if n > 3:
                    break
                goles_sheet[n] = str(min) + 'L' if equipo == 'Home' else str(min) + '' # noqa

        if len(rojas_home_ordenadas) > 0:
            for n, (min, equipo) in enumerate(rojas_home_ordenadas): # noqa
                if n > 0:
                    break
                rojas_sheet.append(min)
        else:
            rojas_sheet.append('')

        if len(rojas_away_ordenadas) > 0:
            for n, (min, equipo) in enumerate(rojas_away_ordenadas): # noqa
                if n > 0:
                    break
                rojas_sheet.append(min)
        else:
            rojas_sheet.append('')

        sheet = goles_sheet + rojas_sheet
        # gol1, gol2, gol3, gol4, rojahome, rojas_away = sheet

        result = {
            'ft': total_goles,
            'sheet': sheet,
            'goles': goles_ordenados,
            'rojas_home': rojas_home_ordenadas,
            'rojas_away': rojas_away_ordenadas
        }
        if debug:
            if debug:
                pprint.pprint(result)
        return result

    except AttributeError:
        print("No se pudieron encontrar los goles. Revisa la estructura del HTML.") # noqa


def process_full_matches(matches_, dt, web, path_html, overwrite=False): # noqa
    ok = 0
    matches = []
    fecha = dt.strftime('%Y-%m-%d')
    filename_fecha = dt.strftime('%Y%m%d')

    TS = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f'{TS} - Procesando {len(matches_)} partidos {fecha}\n\n')
    for m, match in enumerate(matches_):
        total_matches = len(matches_)
        percent = get_percent(m + 1, total_matches)
        str_percent = f'{m + 1}-{total_matches} → {percent}'
        TS = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        [
            pais,
            liga,
            liga_mod,
            hora,
            home,
            away,
            partido_id,
            link
        ] = match

        resumen_link = link.replace('h2h/overall', 'resumen-del-partido')
        web.open(resumen_link)
        web.wait(1)

        if not web.EXIST_CLASS('duelParticipant__startTime'):
            logging.info(f'{TS}|{str_percent}|{partido_id}|{hora} {liga} : {home} - {away} NO DISPONIBLE\n') # noqa
            continue

        status = status_partido(web)
        if status == 'finalizado':
            fecha_hora = web.CLASS('duelParticipant__startTime')
            fecha, hora = fecha_hora.text().split(' ')
            day, month, year = fecha.split('.')
            fecha = f'{year}-{month}-{day}'

            dt = convert_dt(f'{fecha} {hora}')

            marcadores = get_marcador_ft(web)

            web.open(link)
            web.wait(1)

            filename_hora = re.sub(r":", "", hora)
            filename_match = f'{m}_{filename_fecha}{filename_hora}_{partido_id}' # noqa

            logging.info(f'{str_percent}|{ok}|{partido_id}|{fecha} {hora}|{liga} : {home} - {away}') # noqa

            team_matches = get_team_matches(
                path_html,
                filename_match,
                dt,
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
                momios = get_momios(
                    path_html,
                    filename_match,
                    web,
                    overwrite
                )
                reg = {
                    'id': partido_id,
                    'hora': hora,
                    'fecha': fecha,
                    'pais': pais,
                    'liga': liga,
                    'liga_mod': liga_mod,
                    'home': home,
                    'away': away,
                    'ft': marcadores['goles'],
                    'sheet_goles': marcadores['sheet'],
                    'rojas_home': marcadores['rojas_home'],
                    'rojas_away': marcadores['rojas_away'],
                    'url': link,
                    '1x2': momios['odds_1x2'],
                    'goles': momios['odds_goles'],
                    'ambos': momios['odds_ambos'],
                    'handicap': momios['odds_handicap'],
                    'home_matches': team_matches['home_matches'],
                    'away_matches': team_matches['away_matches'],
                    'vs_matches': team_matches['vs_matches'],
                    'filename_fecha': filename_fecha,
                    'filename_match': filename_match
                }
                if momios['OK']:
                    ok += 1
                    matches.append(reg)
                    logging.info(' OK\n')
                else:
                    error = get_match_error_short(reg)
                    logging.info(f' DESCARTADO {error}\n')

            else:
                logging.info(f' DESCARTADO H:{n_h}, A→{n_a}, VS→{n_vs}\n')
        else:
            logging.info(f'{TS}|{str_percent}|{partido_id}|{hora} {liga} : {home} - {away} {status}\n') # noqa

    return matches


def process_matches(matches_, dt, web, path_json, path_html, path_result, overwrite=False): # noqa
    ok = 0
    matches = {}
    fecha = dt.strftime('%Y-%m-%d')
    filename_fecha = dt.strftime('%Y%m%d')
    path_matches = path(path_result, f'{filename_fecha}.json')

    TS = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f'{TS} - Procesando {len(matches_)} partidos {fecha}\n\n')
    for m, match in enumerate(matches_):
        total_matches = len(matches_)
        percent = get_percent(m + 1, total_matches)
        str_percent = f'{m + 1}-{total_matches} → {percent}'
        TS = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        [
            pais,
            liga,
            liga_mod,
            hora,
            home,
            away,
            partido_id,
            link
        ] = match

        web.open(link)
        web.wait(1)

        if not web.EXIST_CLASS('duelParticipant__startTime'):
            logging.info(f'{TS}|{str_percent}|{partido_id}|{hora} {liga} : {home} - {away} NO DISPONIBLE\n') # noqa
            continue

        fecha_hora = web.CLASS('duelParticipant__startTime')
        fecha, hora = fecha_hora.text().split(' ')
        day, month, year = fecha.split('.')
        fecha = f'{year}-{month}-{day}'

        dt = convert_dt(f'{fecha} {hora}')

        filename_hora = re.sub(r":", "", hora)
        filename_match = f'{m}_{filename_fecha}{filename_hora}_{partido_id}'
        path_match = path(path_json, f'{filename_match}.json')

        logging.info(f'{TS}|{str_percent}|{ok}|{partido_id}|{fecha} {hora} {liga} : {home} - {away}') # noqa

        team_matches = get_team_matches(
            path_html,
            filename_match,
            dt,
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
                'id': partido_id,
                'hora': hora,
                'fecha': fecha,
                'pais': pais,
                'liga': liga,
                'liga_mod': liga_mod,
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

            matches[partido_id] = reg

            save_matches(path_match, reg, overwrite)
            save_matches(path_matches, matches, True)

            logging.info(' OK\n')
        else:
            logging.info(f' DESCARTADO H:{n_h}, A→{n_a}, VS→{n_vs}\n')

    logging.info(f'\nPARTIDOS {len(matches)} {fecha}')
    if len(matches) > 0:
        save_matches(path_matches, matches, True)
        return path_matches


def get_all_matches(path_html, filename, matches_link, web, ligas=None, overwrite=False): # noqa
    html_path = os.path.join(path_html, filename)
    if overwrite:
        if os.path.exists(html_path):
            os.remove(html_path)

    if not os.path.exists(html_path):
        web.open(matches_link)
        web.wait_ID('main', 5)
        web.save(html_path)

    with open(html_path, 'r', encoding='utf-8') as html:
        return parse_all_matches(html, ligas)


def parse_all_matches(html, pais_ligas=None):
    global domain
    resultados = []
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
        'sudamerica',
        'women',
    ]
    if not pais_ligas:
        pais_ligas = get_ligas_google_sheet()

    soup = BeautifulSoup(html, 'html.parser')
    ligas = soup.find_all('h4')
    for liga in ligas:
        tmp_liga = ''.join([str(content) for content in liga.contents if not content.name]) # noqa
        pais, nombre_liga = tmp_liga.split(': ')
        pais = unidecode(pais).upper()
        nombre_liga = re.sub(r'\s+$', '', nombre_liga)
        nombre_liga_ = nombre_liga.lower()
        partido_actual = liga.find_next_sibling()

        # Elimina ligas por default
        if any([x in unidecode(nombre_liga.lower()) for x in filter_ligas]):
            continue

        if pais in pais_ligas:
            # print(f'{pais} {nombre_liga_} {pais_ligas[pais]}')
            if nombre_liga in pais_ligas[pais]:
                quitar_liga = pais_ligas[pais][nombre_liga][0]
                if quitar_liga:
                    # print(f'{pais} {nombre_liga_} → Quitar')
                    continue
                if len(pais_ligas[pais][nombre_liga]) > 1:
                    # print(f'{pais} {nombre_liga} → {pais_ligas[pais][nombre_liga][1]}') # noqa
                    nombre_liga_ = pais_ligas[pais][nombre_liga][1]
                else:
                    nombre_liga_ = unidecode(nombre_liga)

        while partido_actual and partido_actual.name != 'h4':
            aplazado = False
            if partido_actual.name == 'span':
                hora = partido_actual.get_text(strip=True)
                if 'Aplazado' in hora:
                    aplazado = True
                hora = hora[:5]
                equipos = partido_actual.find_next_sibling(string=True).strip() # noqa
                try:
                    local, visitante = equipos.split(' - ')
                    link = partido_actual.find_next_sibling('a')['href']
                    partido_id = link.split('/')[-2]
                    # print(link, partido_id)
                    link = f'{domain}/partido/{partido_id}/#/h2h/overall'
                    if not aplazado:
                        resultados.append((
                            pais,
                            nombre_liga,
                            nombre_liga_,
                            hora,
                            local,
                            visitante,
                            partido_id,
                            link
                        ))
                    else:
                        # print(local, visitante, 'Aplazado')
                        break
                except ValueError:
                    pass
            partido_actual = partido_actual.find_next_sibling()
    resultados_ordenados = sorted(resultados, key=lambda x: x[2])
    # print(f'Partidos encontrados: {len(resultados_ordenados)}')
    return resultados_ordenados


def get_team_matches(path_html, filename, dt, home, away, liga, web, overwrite=False): # noqa
    filename_page_h2h = re.sub(r'-|:', '', filename) + '_h2h.html'
    html_path = path(path_html, filename_page_h2h)
    if overwrite:
        if os.path.exists(html_path):
            os.remove(html_path)

    if not os.path.exists(html_path):
        web.wait_Class('h2h__section', 20)
        result = parse_team_matches(web.source(), dt, 'vs')
        if result['vs_nmatches'] > 3:
            try:
                print('\nHome Matches ', end="")
                click_more_matches(web, dt, 'home', home, liga)
                print('Away Matches ', end="")
                click_more_matches(web, dt, 'away', away, liga)
            except RecursionError:
                print('RecursionError')
            web.save(html_path)
        else:
            web.save(html_path)
            return {
                'OK': False,
                'home_nmatches': '-',
                'away_nmatches': '-',
                'vs_nmatches': result['vs_nmatches']
            }
    else:
        logging.info(' ← CACHE | | ')

    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as file:
            return parse_team_matches(file, dt, 'all', home=home, away=away, liga=liga) # noqa


def click_more_matches(web, dt, team, team_name, liga, retries=0):
    MAX_RETRIES = 25
    sections = web.CLASS('h2h__section', multiples=True)
    section = sections[0] if team == 'home' else sections[1]
    result = parse_team_matches(web.source(), dt, team, team_name=team_name, liga=liga) # noqa
    if not result['OK'] and section.EXIST_CLASS('showMore'):
        btn_showMore = section.CLASS('showMore')
        btn_showMore.scroll_to()
        if btn_showMore.click():
            print('.', end="")
        else:
            web.scrollY(-150)
            btn_showMore.click()
            print('.', end="")
        if retries < MAX_RETRIES:
            web.wait()
            click_more_matches(web, dt, team, team_name, liga, retries + 1)
        else:
            print(' DONE MAX RETRIES')
    else:
        print(' DONE')


def click_momios_btn(name, web, debug=False):
    found = False
    btn_momios = web.CLASS('wcl-tab_y-fEC', True)
    if len(btn_momios) > 0:
        for btn in btn_momios:
            texto = btn.text().lower()
            if type(name) is list:
                if debug:
                    print(f'BOTON: {texto} in "{name}" -> {any([x in texto for x in name])}') # noqa
                if any([x in texto for x in name]):
                    btn.scroll_top()
                    if debug:
                        btn.click()
                        web.wait(1)
                        logging.info(f'{texto} → Click')
                    btn.click()
                    web.wait(random.randint(1, 3))
                    found = True
                    break
            elif type(name) is str:
                if debug:
                    print(f'BOTON: {texto} == "{name}" -> {texto == name}')
                if texto == name:
                    btn.scroll_top()
                    btn.click()
                    if debug:
                        logging.info(f'{texto} → Click')
                    web.wait(random.randint(1, 3))
                    found = True
                    break
        if not found:
            print('Boton no encontrado:', name)
    return found


def parse_team_matches(html, dt, team, team_name='', home='', away='', liga='', debug=False): # noqa
    soup = BeautifulSoup(html, 'html.parser')
    sections = soup.find_all('div', class_='h2h__section')

    tmp_matches_home = sections[0].find('div', class_='rows') if len(sections) > 0 else [] # noqa
    tmp_matches_away = sections[1].find('div', class_='rows') if len(sections) > 0 else [] # noqa
    tmp_matches_vs = sections[2].find('div', class_='rows') if len(sections) > 0 else [] # noqa

    tmp_matches_home = tmp_matches_home.find_all('div', class_='h2h__row')
    tmp_matches_away = tmp_matches_away.find_all('div', class_='h2h__row')
    tmp_matches_vs = tmp_matches_vs.find_all('div', class_='h2h__row')

    if team == 'all':
        home_matches = parse_team_section(tmp_matches_home, dt, team, home, liga, debug) # noqa
        away_matches = parse_team_section(tmp_matches_away, dt, team, away, liga, debug) # noqa
        vs_matches = parse_team_section(tmp_matches_vs, dt, debug=debug)

        OK = len(home_matches['matches']) == 5 and len(away_matches['matches']) == 5 and len(vs_matches['matches']) > 3 # noqa
        return {
            'OK': OK,
            'home_matches': home_matches,
            'away_matches': away_matches,
            'vs_matches': vs_matches,
            'home_nmatches': len(home_matches['matches']),
            'away_nmatches': len(away_matches['matches']),
            'vs_nmatches': len(vs_matches['matches'])
        }
    elif team == 'home':
        team_matches = parse_team_section(tmp_matches_home, dt, team, team_name, liga, debug) # noqa
        ok = len(team_matches['matches']) == 5
    elif team == 'away':
        team_matches = parse_team_section(tmp_matches_away, dt, team, team_name, liga, debug) # noqa
        ok = len(team_matches['matches']) == 5
    elif team == 'vs':
        team_matches = parse_team_section(tmp_matches_vs, dt, debug=debug)
        ok = len(team_matches['matches']) > 3
    return {
        'OK': ok,
        f'{team}_matches': team_matches,
        f'{team}_nmatches': len(team_matches['matches']),
    }


def parse_team_section(matches, dt, team=None, team_name=None, liga=None, debug=False): # noqa
    hechos = 0
    concedidos = 0
    p35, p45 = 0, 0
    result_matches = []
    # fecha_partido_actual = dt.strftime('%d.%m.%Y')
    for match in matches:
        date = match.find('span', class_='h2h__date').text # noqa formato dd.mm.yyyy
        dd, mm, yy = date.split('.')
        dt_match = convert_dt(f'{yy}-{mm}-{dd}')

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

        es_partido_anterior = dt_match < dt
        if not es_partido_anterior:
            continue

        if scores[0].text == '-':
            continue

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
            ## print(fecha_partido_actual, date, liga_clean, league_name_clean, liga_similar, liga_psimilar , 'PARTIDO ANTERIOR' if es_partido_anterior else 'POSTERIOR') # noqa
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

                    if debug:
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
                    if debug:
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
    # print(juegos)
    if team_name:
        result['hechos'] = hechos
        result['concedidos'] = concedidos
        if juegos > 0:
            result['p_hechos'] = hechos / juegos
            result['p_concedidos'] = concedidos / juegos
        return result
    else:
        return result


def status_partido(web):
    try:
        soup = BeautifulSoup(web.source(), 'html.parser')
        resultado = soup.find('div', class_='duelParticipant__score').text.strip() # noqa
        if 'Finalizado' in resultado:
            return 'finalizado'
        elif 'Aplazado' in resultado:
            return 'aplazado'
        else:
            return ''
    except AttributeError:
        print("No se pudo encontrar el resultado. Revisa la estructura del HTML.") # noqa
        return ''


def get_momios(path_html, filename, web, overwrite=False): # noqa
    btn_momios = click_momios_btn('momios', web)
    if not btn_momios:
        return {
            'OK': False,
            'odds_1x2': {'OK': False, 'msj': 'No evaluado'},
            'odds_goles': {'OK': False, 'msj': 'No evaluado'},
            'odds_ambos': {'OK': False, 'msj': 'No evaluado'},
            'odds_handicap': {'OK': False, 'msj': 'No evaluado'},
        }

    momios_1x2 = get1x2(path_html, filename, web, overwrite) # noqa
    if not momios_1x2['OK']:
        return {
            'OK': False,
            'odds_1x2': momios_1x2,
            'odds_goles': {'OK': False, 'msj': 'No evaluado'},
            'odds_ambos': {'OK': False, 'msj': 'No evaluado'},
            'odds_handicap': {'OK': False, 'msj': 'No evaluado'},
        }

    momios_goles = getmGoles(path_html, filename, web, overwrite) # noqa
    if not momios_goles['OK']:
        return {
            'OK': False,
            'odds_1x2': momios_1x2,
            'odds_goles': momios_goles,
            'odds_ambos': {'OK': False, 'msj': 'No evaluado'},
            'odds_handicap': {'OK': False, 'msj': 'No evaluado'}
        }

    momios_ambos = getAmbos(path_html, filename, web, overwrite) # noqa
    if not momios_ambos['OK']:
        return {
            'OK': False,
            'odds_1x2': momios_1x2,
            'odds_ambos': momios_ambos,
            'odds_goles': momios_goles,
            'odds_handicap': {'OK': False, 'msj': 'No evaluado'},
        }

    momios_handicap = getHandicap(path_html, filename, web, overwrite) # noqa
    if not momios_handicap['OK']:
        return {
            'OK': False,
            'odds_1x2': momios_1x2,
            'odds_goles': momios_goles,
            'odds_ambos': momios_ambos,
            'odds_handicap': momios_handicap,
        }

    return {
        'OK': momios_ambos['OK'] and momios_goles['OK'] and momios_1x2['OK'],
        'odds_1x2': momios_1x2,
        'odds_goles': momios_goles,
        'odds_ambos': momios_ambos,
        'odds_handicap': momios_handicap,
    }


def getAmbos(path_html, filename, web, overwrite=False):
    nom = 'Ambos'
    filename = f'{filename}_{nom}.html'
    html_path = os.path.join(path_html, filename)
    if overwrite:
        if os.path.exists(html_path):
            os.remove(html_path)

    if not os.path.exists(html_path):
        # logging.info(f'{nom} → {filename} ')
        click_momios_btn('ambos equipos marcarán', web)
        web.save(html_path)
    else:
        logging.info(f'{nom} ← CACHE | ')

    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as file:
            return parse_odds_ambos(file)
    else:
        return {
            'OK': False
        }


def parse_odds_ambos(html):
    soup = BeautifulSoup(html, 'html.parser')
    odds_row = soup.find_all('div', class_='ui-table__row')
    if odds_row:
        for row in odds_row:
            prematchLogo = row.find('img', class_='prematchLogo')
            casa_apuesta = prematchLogo['title'].lower() if prematchLogo and 'title' in prematchLogo.attrs else '' # noqa
            odds = [span.text for span in row.find_all('span') if span.text]
            if casa_apuesta == '1xbet':
                odds_american = [decimal_american(odd) for odd in odds]
                return {
                    'OK': True,
                    'casa': casa_apuesta,
                    'decimal': odds,
                    'american': odds_american
                }
    # logging.info('Fallo → Ambos 1xBet')
    return {
        'OK': False,
        'msj': 'No hay 1xBet'
    }


def get1x2(path_html, filename, web, overwrite=False):
    nom = '1x2'
    filename = f'{filename}_{nom}.html'
    html_path = os.path.join(path_html, filename)
    # filename_img = f'{filename}_img.png'
    # image_path = os.path.join(path_html, filename_img)
    if overwrite:
        if os.path.exists(html_path):
            os.remove(html_path)

    if not os.path.exists(html_path):
        # logging.info(f'{nom} → {filename} ')
        click_momios_btn('1x2', web)
        # web.save_screenshot(image_path)
        web.save(html_path)
    else:
        logging.info(f'{nom} ← CACHE | ')

    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as file:
            return parse_odds_1x2(file)
    else:
        return {'OK': False}


def parse_odds_1x2(html):
    soup = BeautifulSoup(html, 'html.parser')
    odds_row = soup.find_all('div', class_='ui-table__row')
    if odds_row:
        for row in odds_row:
            prematchLogo = row.find('img', class_='prematchLogo')
            casa_apuesta = prematchLogo['title'].lower() if prematchLogo and 'title' in prematchLogo.attrs else '' # noqa
            odds = [
                span.text
                for span in row.find_all('span')
                if span.text.strip() and span.text.strip() != '-'
            ]
            if casa_apuesta == '1xbet' and len(odds) == 3:
                odds_american = [decimal_american(odd) for odd in odds]
                return {
                    'OK': True,
                    'casa': casa_apuesta,
                    'decimal': odds,
                    'american': odds_american
                }
    # logging.info('Fallo → 1x2 1xbet')
    return {
        'OK': False,
        'msj': 'No hay 1xbet'
    }


def getmGoles(path_html, filename, web, overwrite=False):
    nom = 'Goles'
    filename = re.sub(r'-|:', '', filename) + f'_{nom}.html'
    html_path = os.path.join(path_html, filename)
    if overwrite:
        if os.path.exists(html_path):
            os.remove(html_path)

    if not os.path.exists(html_path):
        # logging.info(f'{nom} → {filename} ')
        click_momios_btn(['más/menos de', 'más de/menos de'], web)
        web.save(html_path)
    else:
        logging.info(f'{nom} ← CACHE | ')

    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as file:
            return parse_odds_goles(file)
    else:
        return {'OK': False}


def parse_odds_goles(html):
    result = {}
    soup = BeautifulSoup(html, 'html.parser')
    odds_row = soup.find_all('div', class_='ui-table__row')
    if odds_row:
        casas = []
        for row in odds_row:
            prematchLogo = row.find('img', class_='prematchLogo')
            casa_apuesta = prematchLogo['title'].lower() if prematchLogo and 'title' in prematchLogo.attrs else '' # noqa
            if casa_apuesta not in casas:
                casas.append(casa_apuesta)
            odds = [
                span.text
                for span in row.find_all('span')
                if span.text.strip() and span.text.strip() != '-'
            ]
            if casa_apuesta == '1xbet' and len(odds) == 3:
                goals = odds[0]
                odds_decimal = odds[1:]
                odds_american = [decimal_american(odd) for odd in odds_decimal] # noqa
                result[goals] = {
                    'casa': casa_apuesta,
                    'decimal': odds_decimal,
                    'american': odds_american
                }
    if len(result) > 0:
        if '3.5' not in result:
            # str_casas = ', '.join(casas)
            # logging.info(f"Fallo → No hay -3.5 '{str_casas}'")
            return {
                'OK': False,
                'msj': 'No hay 3.5',
                'casas': casas,
                'odds': result
            }
        else:
            # -3.5 rango entre -450 a -700
            menos = int(result['3.5']['american'][1])
            if menos <= -450 and menos >= -700:
                return {
                    'OK': True,
                    'odds': result
                }
            else:
                # logging.info(f'Fallo → Momio -3.5 no esta en rango Rango "{menos}"') # noqa
                print('')
                return {
                    'OK': False,
                    'msj': f'MOMIO -3.5 no está en rango "{menos}"',
                    'odds': result
                }
    else:
        # str_casas = ', '.join(casas)
        # logging.info(f'Fallo → No hay Goles "{str_casas}"')
        return {
            'OK': False,
            'msj': 'No hay Casas'
        }


def getHandicap(path_html, filename, web, overwrite=False):
    nom = 'Handicap'
    filename = re.sub(r'-|:', '', filename) + f'_{nom}.html'
    html_path = os.path.join(path_html, filename)
    if overwrite:
        if os.path.exists(html_path):
            os.remove(html_path)

    if not os.path.exists(html_path):
        # logging.info(f'{nom} → {filename}')
        click_momios_btn('handicap asiático', web)
        web.save(html_path)
    else:
        logging.info(f'{nom} ← CACHE | ')

    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as file:
            return parse_handicap(file)
    else:
        return {'OK': False}


def parse_handicap(html):
    result = {}
    soup = BeautifulSoup(html, 'html.parser')
    odds_row = soup.find_all('div', class_='ui-table__row')
    if odds_row:
        descartados = []
        for row in odds_row:
            prematchLogo = row.find('img', class_='prematchLogo')
            casa_apuesta = prematchLogo['title'].lower() if prematchLogo and 'title' in prematchLogo.attrs else '' # noqa
            odds = [
                span.text
                for span in row.find_all('span')
                if span.text.strip() and span.text.strip() != '-'
            ]
            handicap = odds[0]
            if casa_apuesta in ['1xbet', 'bet365'] and len(odds) == 3:
                odds_decimal = odds[1:]
                odds_american = [decimal_american(odd) for odd in odds_decimal] # noqa
                result[handicap] = {
                    'casa': casa_apuesta,
                    'decimal': odds_decimal,
                    'american': odds_american
                }
            else:
                descartados.append(
                    f"{casa_apuesta} → '{handicap}'"
                )
                pass
    # HandiCap Asiatico -0/-0.5 (OBLIGATORIO)
    # HandiCap Asiatico -1 (OBLIGATORIO)
    # HandiCap Asiatico -2 (OPCIONAL)
    str_descartados = ', '.join(descartados)
    if len(result) > 0:
        if '0, -0.5' in result and '-1' in result:
            return {
                'OK': True,
                'odds': result
            }
        else:
            _0 = 'SI' if '0, -0.5' in result else 'NO'
            _1 = 'SI' if '-1' in result else 'NO'
            _2 = 'SI' if '-2' in result else 'NO'
            msj = f'Fallo → Handicap Asiatico 0/-0.5: {_0}, -1: {_1}, -2: {_2}'
            # logging.info(msj) # noqa
            logging.info(f'Fallo → Handicap "{str_descartados}"')
            return {
                'OK': False,
                'msj': msj,
                'odds': result
            }
    else:
        msj = f'Fallo → Handicap "{str_descartados}"'
        logging.info(msj)
        return {
            'OK': False,
            'msj': msj
        }


if __name__ == '__main__':
    web = Web(multiples=True)
    ids = [
        # 'viwDtPCi',
        # 'n7eyYwcJ',
        # 'xxxgL0DD',  # PENALTI FALLADO
        # 'vsOtJ9xh',  # sumo goles de mas
        # 'UipXRFJ6'
        # 'UDmMQjLi',  # noqa no se porque adjudico el robot a Visitante los 3 goles cuando era a Local "L"
        # 'fu7cERHc'  # El robot mando 0 - 0 pero quedaron 0 - 1
        # 'CMALI2TH'  # solo esta contando los goles de LOCAL
        # 'IPEFOmxJ',
        # 'j5RO0J86',
        # 'l24Tp224',
        'U72xxSLE'
    ]
    for partido_id in ids:
        link = f'https://www.flashscore.com.mx/partido/{partido_id}/?d=1#/resumen-del-partido/resumen-del-partido' # noqa
        print(link)
        web.open(link) # noqa 
        web.wait(1)
        print(partido_id)
        marcador = get_marcador_ft(web, True)
        pprint.pprint(marcador)
    # web.close()
