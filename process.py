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
    hechos = 0
    concedidos = 0
    p35, p45 = 0, 0
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
                    if ft <= 3:
                        p35 += 1
                    if ft <= 4:
                        p45 += 1
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
    result = {
        'matches': result_matches
    }
    juegos = len(result_matches)
    if juegos > 0:
        result['p35'] = p35 / juegos
        result['p45'] = p45 / juegos
    if match_home:
        result['hechos'] = hechos
        result['concedidos'] = concedidos,
        if juegos > 0:
            result['p_hechos'] = hechos / juegos
            result['p_concedidos'] = concedidos / juegos
        return result
    else:
        return result


def main(db_file):
    engine = create_engine(f'sqlite:///db/{db_file}.sqlite')
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
        id = str(match.id)
        home = match.home
        away = match.away
        time = match.time
        liga = match.league
        if all(v is None for v in [liga, time, home, away]):
            continue
        if match.stats is None:
            continue
        matchstats = match.stats
        if matchstats.fecha is None:
            continue
        fecha = matchstats.fecha
        home_matches_db = matchstats.home_matches
        away_matches_db = matchstats.away_matches
        face_matches_db = matchstats.face_matches
        if len(home_matches_db) == 0 or len(away_matches_db) == 0 or len(face_matches_db) == 0:  # noqa
            print(fecha, id, home, away, 'PARTIDOS H:', len(home_matches_db), 'A:', len(away_matches_db), 'F:', len(face_matches_db))  # noqa
            continue
        url = match.url
        tmp_pais = 'Unknown'
        if match.pais is not None:
            tmp_pais = re.search(r'/(\d+)\.png$', match.pais)
            tmp_pais = tmp_pais.group(1) if tmp_pais else 'Unknown'
        pais = dic_paises[tmp_pais]
        pais_l = pais.lower()
        home_matches = encuentros(home_matches_db, liga, home)
        if len(home_matches['matches']) < 5:
            print(fecha, home, away, 'HOME')
            continue
        away_matches = encuentros(away_matches_db, liga, away)
        if len(away_matches['matches']) < 5:
            print(fecha, home, away, 'AWAY')
            continue
        phP = home_matches['p_hechos']
        phM = home_matches['p_concedidos']
        paP = away_matches['p_hechos']
        paM = away_matches['p_concedidos']
        promedio_gol = (phP * phM) + (paP * paM)
        face_matches = encuentros(face_matches_db, '', '')
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
        # print(fecha, home, away)
    if len(result) > 0:
        print(f'Partidos Procesados {len(result)} - {len(matches)}')
        with open(f'{result_path}/{db_file}.json', 'w') as f:
            f.write(json.dumps(result))
    if len(result_pais) > 0:
        with open(f'{result_path}/{db_file}_pais.json', 'w') as f:
            f.write(json.dumps(result_pais))


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) > 0:
        db_file = args[0]
        if os.path.exists(f'db/{db_file}.sqlite'):
            main(db_file)
        else:
            print('Archivo de base no existe, lo escribiste bien?')
    else:
        print('Falta expecificar nombre de archivo sqlite')
