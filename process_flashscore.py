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


def main(path_matches: str, overwrite: bool = False):
    web = Web()
    matches = get_json(path_matches)
    try:
        for match in matches:
            id = match['id']
            pais = match['pais']
            hora = match['hora']
            liga = match['liga']
            home = match['home']
            away = match['away']
            link = match['url']
            filename_match = match['filename_match']
            logging.info(f'#{id} ')
            momios = get_momios(
                path_html,
                filename_match,
                link,
                web,
                overwrite
            )
            if momios['OK']:
                logging.info(f'#{id} {hora}|{pais} {liga}| {home} - {away}\n')
            else:
                odds_1x2 = 'OK' if momios['odds_1x2']['OK'] else 'NO' # noqa
                odds_ambos = 'OK' if momios['odds_ambos']['OK'] else 'NO' # noqa
                odds_goles = 'OK' if momios['odds_goles']['OK'] else 'NO' # noqa
                odds_handicap = 'OK' if momios['odds_handicap']['OK'] else 'NO' # noqa
                logging.info(f'#{id} {hora}|{liga} | {home} - {away} MOMIOS 1x2: {odds_1x2}, GOLES: {odds_goles}, AMBOS: {odds_ambos}, HANDICAP: {odds_handicap}\n') # noqa
                # input('Presiona Enter para continuar')
    except KeyboardInterrupt:
        print('\nFin...')
    # web.close()


if __name__ == '__main__':
    args = parser.parse_args()
    filename = args.file
    filename_date = filename.split('.')[0]
    filename_date = filename_date[:8]
    path_file = path(path_cron, filename_date, filename)
    overwrite = args.over

    if not os.path.exists(path_file):
        print(f'Archivo {path_file} no existe')
        exit(1)

    main(path_file, overwrite)
