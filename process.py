import os
import re
import sys
from model import Match
from model.db import Base
from catalogos import dic_paises
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session


def encuentros(matches, match_liga, match_home):
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
        if liga == match_liga:
            if len(result_matches) < 5:
                if match_home:
                    if home == match_home:
                        hechos += home_FT
                    else:
                        concedidos += away_FT
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
        return {
            'hechos': hechos,
            'concedidos': concedidos,
            'matches': result_matches
        }
    else:
        return result_matches


def main(db_file):
    engine = create_engine(f'sqlite:///db/{db_file}')
    Base.metadata.create_all(engine)
    Session = scoped_session(sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False
    ))
    matches = Match.get_all(Session)
    print(f'Extrayendo {len(matches)} partidos.')
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
        home_matches = []
        away_matches = []
        face_matches = []
        liga = match.league
        tmp_pais = re.search(r'/(\d+)\.png$', match.pais)
        tmp_pais = tmp_pais.group(1) if tmp_pais else 'Unknown'
        pais = dic_paises[tmp_pais]
        home = match.home
        away = match.home
        home_matches 
        if len(home_matches) < 5:
            continue
        print(pais, liga, home, away)


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
