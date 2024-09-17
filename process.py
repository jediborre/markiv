import os
import re
import sys
import json
from model import Match
from model.db import Base
from catalogos import dic_paises
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

script_path = os.path.dirname(os.path.abspath(__file__))
result_path = os.path.join(script_path, 'result')
if not os.path.exists(result_path):
    os.makedirs(result_path)
matches = {}
pais_matches = {}


def encuentros(matches, match_liga, match_home):
    global result_path
    result_matches = []
    hechos, concedidos = 0, 0
    for match in matches:
        liga = match.league
        date = match.date
        home = match.home
        away = match.away
        home_FT = int(match.home_FT)
        away_FT = int(match.away_FT)
        ft = home_FT + away_FT
        if match_liga:
            if liga == match_liga:
                if len(result_matches) < 5:
                    if match_home:
                        if home == match_home:
                            hechos += home_FT
                            concedidos += away_FT
                        else:
                            hechos += away_FT
                            concedidos += home_FT
                    result_matches.append({
                        'ft': ft,
                        'date': date,
                        'liga': liga,
                        'home': home,
                        'home_ft': home_FT,
                        'away': away,
                        'away_ft': away_FT,
                    })
                else:
                    break
        else:
            if len(result_matches) < 5:
                result_matches.append({
                    'ft': ft,
                    'date': date,
                    'liga': liga,
                    'home': home,
                    'home_ft': home_FT,
                    'away': away,
                    'away_ft': away_FT,
                })
            else:
                break
    if match_home:
        juegos = len(result_matches)
        result = {
            'hechos': hechos,
            'concedidos': concedidos,
            'matches': result_matches
        }
        if juegos > 0:
            result['p_hechos'] = hechos / juegos
            result['p_concedidos'] = concedidos / juegos
        return result
    else:
        return result_matches


def main(db_file):
    filename, ext = db_file.split('.')
    engine = create_engine(f'sqlite:///db/{db_file}')
    Base.metadata.create_all(engine)
    Session = scoped_session(sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False
    ))
    matches = Match.get_all(Session)
    print(f'Extrayendo {len(matches)} partidos.')
    result = {}
    result_pais = {}
    for match in matches:
        if match.stats is None:
            continue
        matchstats = match.stats
        if matchstats.fecha is None:
            continue
        home_matches_db = matchstats.home_matches
        away_matches_db = matchstats.away_matches
        if len(home_matches_db) == 0 or len(away_matches_db) == 0:
            continue
        id = str(match.id)
        fecha = matchstats.fecha
        time = match.time
        liga = match.league
        url = match.url
        tmp_pais = re.search(r'/(\d+)\.png$', match.pais)
        tmp_pais = tmp_pais.group(1) if tmp_pais else 'Unknown'
        pais = dic_paises[tmp_pais]
        pais_l = pais.lower()
        home = match.home
        away = match.away
        home_matches = encuentros(home_matches_db, liga, home)
        if len(home_matches['matches']) < 5:
            continue
        away_matches = encuentros(away_matches_db, liga, away)
        if len(away_matches['matches']) < 5:
            continue
        phP = home_matches['p_hechos']
        phM = home_matches['p_concedidos']
        paP = away_matches['p_hechos']
        paM = away_matches['p_concedidos']
        promedio_gol = (phP * phM) + (paP * paM)
        face_matches = encuentros(home_matches_db, '', '')
        reg = {
            'id': id,
            'time': time,
            'fecha': fecha,
            'pais': pais,
            'liga': liga,
            'home': home,
            'away': away,
            'url': url,
            'promedio_gol': promedio_gol,
            'home_matches': home_matches,
            'away_matches': away_matches,
            'face_matches': face_matches
        }
        if pais_l not in result_pais:
            result_pais[pais_l] = []
        result[id] = reg
        result_pais[pais_l].append(reg)
        print(fecha, home, away)
    if len(result) > 0:
        with open(f'{result_path}/{filename}.json', 'w') as f:
            f.write(json.dumps(result))
    if len(result_pais) > 0:
        with open(f'{result_path}/{filename}_pais.json', 'w') as f:
            f.write(json.dumps(result_pais))


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) > 0:
        db_file = args[0]
        if '.sqlite' in db_file:
            if os.path.exists(f'db/{db_file}'):
                main(db_file)
            else:
                print('Archivo de base no existe, lo escribiste bien?')
        else:
            print('Archivo de base sqlite invalido')
    else:
        print('Falta expecificar nombre de archivo sqlite')
