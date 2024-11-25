import re
from fuzzywuzzy import fuzz
from bs4 import BeautifulSoup
from utils import limpia_nombre


def parse_odds_ambos(html):
    soup = BeautifulSoup(html, 'html.parser')
    odds_row = soup.find_all('div', class_='ui-table__row')
    if odds_row:
        print('ODDS Ambos Marcan')
        for row in odds_row:
            prematchLogo = row.find('img', class_='prematchLogo')
            casa_apuesta = prematchLogo['title'] if prematchLogo and 'title' in prematchLogo.attrs else '' # noqa
            odds = [span.text for span in row.find_all('span') if span.text]
            if casa_apuesta == 'Calientemx':
                return {
                    'OK': True,
                    'casa': casa_apuesta,
                    'odds': odds
                }
    return {
        'OK': False
    }


def parse_odds_1x2(html):
    soup = BeautifulSoup(html, 'html.parser')
    odds_row = soup.find_all('div', class_='ui-table__row')
    if odds_row:
        print('ODDS 1x2')
        for row in odds_row:
            prematchLogo = row.find('img', class_='prematchLogo')
            casa_apuesta = prematchLogo['title'] if prematchLogo and 'title' in prematchLogo.attrs else '' # noqa
            odds = [span.text for span in row.find_all('span') if span.text]
            if casa_apuesta == 'Calientemx':
                return {
                    'OK': True,
                    'casa': casa_apuesta,
                    'odds': odds
                }
    return {
        'OK': False
    }


def parse_odds_goles(html):
    result = []
    soup = BeautifulSoup(html, 'html.parser')
    odds_row = soup.find_all('div', class_='ui-table__row')
    if odds_row:
        print('ODDS Goles')
        for row in odds_row:
            prematchLogo = row.find('img', class_='prematchLogo')
            casa_apuesta = prematchLogo['title'] if prematchLogo and 'title' in prematchLogo.attrs else '' # noqa
            odds = [span.text for span in row.find_all('span') if span.text]
            if casa_apuesta == 'Calientemx':
                result.append({
                    'casa': casa_apuesta,
                    'odds': odds
                })
    if len(result) > 0:
        return {
            'OK': True,
            'odds': result
        }
    else:
        return {
            'OK': False
        }


def parse_section(matches, team=None, team_name=None, liga=None, debug=False):
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


def parse_team_matches(html, team, team_name='', home='', away='', liga='', debug=False): # noqa
    soup = BeautifulSoup(html, 'html.parser')
    sections = soup.find_all('div', class_='h2h__section')

    tmp_matches_home = sections[0].find('div', class_='rows') if len(sections) > 0 else [] # noqa
    tmp_matches_away = sections[1].find('div', class_='rows') if len(sections) > 0 else [] # noqa
    tmp_matches_face = sections[2].find('div', class_='rows') if len(sections) > 0 else [] # noqa

    tmp_matches_home = tmp_matches_home.find_all('div', class_='h2h__row')
    tmp_matches_away = tmp_matches_away.find_all('div', class_='h2h__row')
    tmp_matches_face = tmp_matches_face.find_all('div', class_='h2h__row')

    if team == 'all':
        home_matches = parse_section(tmp_matches_home, team, home, liga, debug)
        away_matches = parse_section(tmp_matches_away, team, away, liga, debug)
        face_matches = parse_section(tmp_matches_face, debug=debug)

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
        team_matches = parse_section(tmp_matches_home, team, team_name, liga, debug) # noqa
        ok = len(team_matches['matches']) == 5
        # print(f'Home Matches: {len(team_matches["matches"])} {ok}')
    elif team == 'away':
        team_matches = parse_section(tmp_matches_away, team, team_name, liga, debug) # noqa
        ok = len(team_matches['matches']) == 5
        # print(f'Away Matches: {len(team_matches["matches"])} {ok}')
    elif team == 'face':
        team_matches = parse_section(tmp_matches_face, debug=debug)
        ok = len(team_matches['matches']) > 3
        # print(f'Face Matches: {len(team_matches["matches"])} {ok}')
    return {
        'OK': ok,
        f'{team}_matches': team_matches,
        f'{team}_nmatches': len(team_matches['matches']),
    }
