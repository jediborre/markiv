import os
import logging # noqa
import argparse
import pprint
from web import Web
from utils import path
from utils import get_json
from parse import get_momios
from utils import prepare_paths

path_result, path_cron, path_csv, path_json, path_html = prepare_paths('procesa_flashcore.log') # noqa

parser = argparse.ArgumentParser(
    description="Procesa Partidos de la hora Flashscore"
)
parser.add_argument('file', type=str, help='Archivo de Partidos Flashscore')
parser.add_argument('--over', action='store_true', help="Sobreescribir")


def main(path_matches: str):
    web = Web()
    matches = get_json(path_matches)
    for match in matches:
        id = match['id']
        pais = match['pais']
        hora = match['hora']
        liga = match['liga']
        home = match['home']
        away = match['away']
        link_1x2 = match['l_1x2']
        link_goles = match['l_goles']
        link_ambos = match['l_ambos']
        link_handicap = match['l_handicap']
        filename_match = match['filename_match']
        momios = get_momios(
            path_html,
            filename_match,
            link_1x2,
            link_goles,
            link_ambos,
            link_handicap,
            web,
            True
        )
        if momios['OK']:
            logging.info(f'#{id} {hora}|{liga} | {home} - {away}')
        else:
            logging.info(f'#{id} {hora}|{liga} | {home} - {away} MOMIOS')
            pprint.pprint(momios)
    # web.close()


if __name__ == '__main__':
    args = parser.parse_args()
    path_file = path(path_cron, args.file)

    if not os.path.exists(path_file):
        print(f'Archivo {path_file} no existe')
        exit(1)

    main(path_file)
