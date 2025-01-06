import os
import json
import logging # noqa
import argparse
import pprint # noqa
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


def main(path_matches: str, filename_result: str, overwrite: bool = False):
    logging.info(f'MarkIV {filename_result} {path_matches} overwrite: {'SI' if overwrite else 'NO'}') # noqa
    web = Web()
    result = []
    matches = get_json(path_matches)
    logging.info(f'Matches {len(matches)}')
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
                ganador = momios['odds_1x2']
                goles = momios['odds_goles']
                ambos = momios['odds_ambos']
                handicap = momios['odds_handicap']
                match['1x2'] = ganador
                match['goles'] = goles
                match['ambos'] = ambos
                match['handicap'] = handicap
                logging.info(f'#{id} {hora}|{pais} {liga}| {home} - {away} OK\n') # noqa
                result.append(match)
            else:
                odds_1x2 = 'OK' if momios['odds_1x2']['OK'] else 'NO' # noqa
                odds_ambos = 'OK' if momios['odds_ambos']['OK'] else 'NO' # noqa
                odds_goles = 'OK' if momios['odds_goles']['OK'] else 'NO' # noqa
                odds_handicap = 'OK' if momios['odds_handicap']['OK'] else 'NO' # noqa
                logging.info(f'#{id} {hora}|{liga} | {home} - {away} MOMIOS 1x2: {odds_1x2}, GOLES: {odds_goles}, AMBOS: {odds_ambos}, HANDICAP: {odds_handicap}\n') # noqa
                # input('Presiona Enter para continuar')
        if len(result) > 0:
            filename_date = filename_result[:8]
            path_result_ok = path(path_result, filename_date)
            if not os.path.exists(path_result_ok):
                os.makedirs(path_result_ok)
            path_result_file = path(path_result_ok, f'{filename_result}.json')
            with open(path_result_file, 'w') as file:
                file.write(json.dumps(result, indent=4))
                logging.info(f'Archivo {path_result_file} creado')
    except KeyboardInterrupt:
        print('\nFin...')
    # web.close()


if __name__ == '__main__':
    args = parser.parse_args()
    filename = args.file
    filename_noext = filename.split('.')[0]
    filename_date = filename_noext[:8]
    path_file = path(path_cron, filename_date, filename)
    overwrite = args.over
    overwrite = True

    if not os.path.exists(path_file):
        logging.info(f'Archivo {path_file} no existe')
        exit(1)

    main(path_file, filename_noext, overwrite)
