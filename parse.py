import re
import os
import random
import logging
from fuzzywuzzy import fuzz
from bs4 import BeautifulSoup
from utils import path
from utils import limpia_nombre
from utils import decimal_american


def get_all_matches(path_html, filename, matches_link, web, overwrite=False): # noqa
    html_path = os.path.join(path_html, filename)
    if overwrite:
        if os.path.exists(html_path):
            os.remove(html_path)

    if not os.path.exists(html_path):
        web.open(matches_link)
        web.wait_ID('main', 5)
        web.save(html_path)

    with open(html_path, 'r', encoding='utf-8') as html:
        return parse_all_matches(html)


def parse_all_matches(html):
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
                hora = hora[:5]
                equipos = partido_actual.find_next_sibling(string=True).strip() # noqa
                try:
                    local, visitante = equipos.split(' - ')
                    link = partido_actual.find_next_sibling('a')['href']
                    link = f'{domain}{link}#/h2h/overall'
                    # link_1x2 = f'{link}#/comparacion-de-momios/momios-1x2/partido' # noqa
                    # link_goles = f'{link}#/comparacion-de-momios/mas-de-menos-de/partido' # noqa
                    # link_ambos = f'{link}#/comparacion-de-momios/ambos-equipos-marcaran/partido' # noqa
                    # link_handicap = f'{link}#/comparacion-de-momios/handicap-asiatico/partido' # noqa
                    resultados.append((
                        pais,
                        nombre_liga,
                        hora,
                        local,
                        visitante,
                        link
                    ))
                except ValueError:
                    pass
            partido_actual = partido_actual.find_next_sibling()
    resultados_ordenados = sorted(resultados, key=lambda x: x[2])
    return resultados_ordenados


def get_team_matches(path_html, filename, link, home, away, liga, web, overwrite=False): # noqa
    filename_page_h2h = re.sub(r'-|:', '', filename) + '_h2h.html'
    html_path = path(path_html, filename_page_h2h)
    if overwrite:
        if os.path.exists(html_path):
            os.remove(html_path)

    if not os.path.exists(html_path):
        # print('Match', '→', filename_page_h2h) # noqa
        web.open(link)

        web.wait_Class('h2h__section', 20)
        result = parse_team_matches(web.source(), 'vs')
        if result['vs_nmatches'] > 3:
            try:
                print('\nHome Matches ', end="")
                click_more_matches(web, 'home', home, liga)
                print('Away Matches ', end="")
                click_more_matches(web, 'away', away, liga)
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
        logging.info(f'← {filename_page_h2h}')

    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as file:
            return parse_team_matches(file, 'all', home=home, away=away, liga=liga) # noqa


def click_more_matches(web, team, team_name, liga, retries=0):
    MAX_RETRIES = 25
    sections = web.CLASS('h2h__section', multiples=True)
    section = sections[0] if team == 'home' else sections[1]
    result = parse_team_matches(web.source(), team, team_name=team_name, liga=liga) # noqa
    if not result['OK'] and section.EXIST_CLASS('showMore'):
        btn_showMore = section.CLASS('showMore')
        btn_showMore.scroll_to()
        if btn_showMore.click():
            print('.', end="")
        else:
            web.scrollY(-150)
            btn_showMore.click()
            print('.', end="|")
        if retries < MAX_RETRIES:
            web.wait()
            click_more_matches(web, team, team_name, liga, retries + 1)
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
                        print(texto, 'click')
                        btn.click()
                        web.wait(1)
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
                        print(texto, 'click')
                    web.wait(random.randint(1, 3))
                    found = True
                    break
        if not found:
            print('Boton no encontrado:', name)
    return found


def parse_team_matches(html, team, team_name='', home='', away='', liga='', debug=False): # noqa
    soup = BeautifulSoup(html, 'html.parser')
    sections = soup.find_all('div', class_='h2h__section')

    tmp_matches_home = sections[0].find('div', class_='rows') if len(sections) > 0 else [] # noqa
    tmp_matches_away = sections[1].find('div', class_='rows') if len(sections) > 0 else [] # noqa
    tmp_matches_vs = sections[2].find('div', class_='rows') if len(sections) > 0 else [] # noqa

    tmp_matches_home = tmp_matches_home.find_all('div', class_='h2h__row')
    tmp_matches_away = tmp_matches_away.find_all('div', class_='h2h__row')
    tmp_matches_vs = tmp_matches_vs.find_all('div', class_='h2h__row')

    if team == 'all':
        home_matches = parse_team_section(tmp_matches_home, team, home, liga, debug) # noqa
        away_matches = parse_team_section(tmp_matches_away, team, away, liga, debug) # noqa
        vs_matches = parse_team_section(tmp_matches_vs, debug=debug)

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
        team_matches = parse_team_section(tmp_matches_home, team, team_name, liga, debug) # noqa
        ok = len(team_matches['matches']) == 5
    elif team == 'away':
        team_matches = parse_team_section(tmp_matches_away, team, team_name, liga, debug) # noqa
        ok = len(team_matches['matches']) == 5
    elif team == 'vs':
        team_matches = parse_team_section(tmp_matches_vs, debug=debug)
        ok = len(team_matches['matches']) > 3
    return {
        'OK': ok,
        f'{team}_matches': team_matches,
        f'{team}_nmatches': len(team_matches['matches']),
    }


def parse_team_section(matches, team=None, team_name=None, liga=None, debug=False): # noqa
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
    if team_name:
        result['hechos'] = hechos
        result['concedidos'] = concedidos
        if juegos > 0:
            result['p_hechos'] = hechos / juegos
            result['p_concedidos'] = concedidos / juegos
        return result
    else:
        return result


def get_momios(path_html, filename, link_match, web, overwrite=False): # noqa
    web.open(link_match)
    web.wait(1)
    btn_momios = click_momios_btn('momios', web, True)
    if not btn_momios:
        return {
            'OK': False,
            'odds_1x2': {'OK': False},
            'odds_goles': {'OK': False},
            'odds_ambos': {'OK': False},
            'odds_handicap': {'OK': False},
        }

    momios_1x2 = get1x2(path_html, filename, web, overwrite) # noqa
    if not momios_1x2['OK']:
        return {
            'OK': False,
            'odds_1x2': momios_1x2,
            'odds_goles': {'OK': False},
            'odds_ambos': {'OK': False},
            'odds_handicap': {'OK': False},
        }
    momios_ambos = getAmbos(path_html, filename, web, overwrite) # noqa
    if not momios_ambos['OK']:
        return {
            'OK': False,
            'odds_1x2': momios_1x2,
            'odds_goles': {'OK': False},
            'odds_ambos': momios_ambos,
            'odds_handicap': {'OK': False},
        }

    momios_goles = getmGoles(path_html, filename, web, overwrite) # noqa
    if not momios_goles['OK']:
        return {
            'OK': False,
            'odds_1x2': momios_1x2,
            'odds_goles': momios_goles,
            'odds_ambos': momios_ambos,
            'odds_handicap': {'OK': False},
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
        print(f'{nom}', '→', filename, end=" ")
        click_momios_btn('ambos equipos marcarán', web)
        web.save(html_path)
    else:
        print(f'{nom}', '←', filename, end=" ")

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
    return {
        'OK': False,
        'ERROR': 'No hay 1xBet'
    }


def get1x2(path_html, filename, web, overwrite=False):
    nom = '1x2'
    filename = f'{filename}_{nom}.html'
    html_path = os.path.join(path_html, filename)
    if overwrite:
        if os.path.exists(html_path):
            os.remove(html_path)

    if not os.path.exists(html_path):
        print(f'{nom}', '→', filename, end=" ")
        click_momios_btn('1x2', web)
        web.save(html_path)
    else:
        print(f'{nom}', '←', filename)

    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as file:
            return parse_odds_1x2(file)
    else:
        return {
            'OK': False
        }


def parse_odds_1x2(html):
    soup = BeautifulSoup(html, 'html.parser')
    odds_row = soup.find_all('div', class_='ui-table__row')
    if odds_row:
        for row in odds_row:
            prematchLogo = row.find('img', class_='prematchLogo')
            casa_apuesta = prematchLogo['title'].lower() if prematchLogo and 'title' in prematchLogo.attrs else '' # noqa
            odds = [span.text for span in row.find_all('span') if span.text]
            if casa_apuesta == 'calientemx':
                odds_american = [decimal_american(odd) for odd in odds]
                return {
                    'OK': True,
                    'casa': casa_apuesta,
                    'decimal': odds,
                    'american': odds_american
                }
    return {
        'OK': False,
        'ERROR': 'No hay Caliente'
    }


def getmGoles(path_html, filename, web, overwrite=False):
    nom = 'Goles'
    filename = re.sub(r'-|:', '', filename) + f'_{nom}.html'
    html_path = os.path.join(path_html, filename)
    if overwrite:
        if os.path.exists(html_path):
            os.remove(html_path)

    if not os.path.exists(html_path):
        print(f'{nom}', '→', filename, end=" ")
        click_momios_btn(['más/menos de', 'más de/menos de'], web)
        web.save(html_path)
    else:
        print(f'{nom}', '←', filename)

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
            casas.append(casa_apuesta)
            odds = [span.text for span in row.find_all('span') if span.text]
            if casa_apuesta == 'calientemx':
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
            return {
                'OK': False,
                'ERROR': 'No hay 3.5',
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
                return {
                    'OK': False,
                    'ERROR': 'MOMIO -3.5 no está en rango',
                    'odds': result
                }
    else:
        print(f'ODDS Goles No hay Caliente {casas}')
        return {
            'OK': False,
            'ERROR': 'No hay Caliente'
        }


def getHandicap(path_html, filename, web, overwrite=False):
    nom = 'Handicap'
    filename = re.sub(r'-|:', '', filename) + f'_{nom}.html'
    html_path = os.path.join(path_html, filename)
    if overwrite:
        if os.path.exists(html_path):
            os.remove(html_path)

    if not os.path.exists(html_path):
        print(f'{nom}', '→', filename, end=" ")
        click_momios_btn('handicap asiático', web)
        web.save(html_path)
    else:
        print(f'{nom}', '←', filename, end=" ")

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
        for row in odds_row:
            prematchLogo = row.find('img', class_='prematchLogo')
            casa_apuesta = prematchLogo['title'].lower() if prematchLogo and 'title' in prematchLogo.attrs else '' # noqa
            odds = [span.text for span in row.find_all('span') if span.text]
            if casa_apuesta == '1xbet':
                handicap = odds[0]
                odds_decimal = odds[1:]
                odds_american = [decimal_american(odd) for odd in odds_decimal] # noqa
                result[handicap] = {
                    'casa': casa_apuesta,
                    'decimal': odds_decimal,
                    'american': odds_american
                }
    # HandiCap Asiatico -0/-0.5 (OBLIGATORIO)
    # HandiCap Asiatico -1 (OBLIGATORIO)
    # HandiCap Asiatico -2 (OPCIONAL)
    if len(result) > 0:
        if '0, -0.5' in result and '-1' in result:
            return {
                'OK': True,
                'odds': result
            }
        else:
            return {
                'OK': False,
                'ERROR': 'No hay Handicap Asiatico -0/-0.5 y -1',
                'odds': result
            }
    else:
        return {
            'OK': False,
            'ERROR': 'No hay Bet365'
        }
