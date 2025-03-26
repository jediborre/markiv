import os
import logging # noqa
import argparse
import pprint # noqa
from web import Web
from utils import path
from utils import get_json_list
from utils import basename
from parse import get_momios
from utils import save_matches
from utils import prepare_paths
from parse import status_partido
from send_flashscore import send_matches
from send_flashscore import get_match_ok
from send_flashscore import get_match_error

path_result, path_cron, path_csv, path_json, path_html = prepare_paths() # noqa

parser = argparse.ArgumentParser(
    description="Procesa Partidos de la hora Flashscore"
)
parser.add_argument('file', type=str, help='Archivo de Partidos Flashscore')
parser.add_argument('--over', action='store_true', help="Sobreescribir")


def main(path_matches: str, overwrite: bool = False):
    filename = basename(path_matches, True)
    logging.info(f'MarkIV {filename} {path_matches}') # noqa
    web = Web(multiples=True)
    result = []
    matches = get_json_list(path_matches)
    try:
        for match in matches:
            link = match['url']
            filename_match = match['filename_match']
            web.open(link)
            web.wait(1)
            status = status_partido(web)
            match['status'] = status
            if status in ['aplazado']:
                msj = get_match_error(match)
                # logging.info(msj + '\nAplazado\n')
            else:
                momios = get_momios(
                    path_html,
                    filename_match,
                    web,
                    overwrite
                )
                match['1x2'] = momios['odds_1x2']
                match['ambos'] = momios['odds_ambos']
                match['goles'] = momios['odds_goles']
                match['handicap'] = momios['odds_handicap']
                if momios['OK']:
                    msj = get_match_ok(match)
                    logging.info(msj + '\n')
                    result.append(match)
                else:
                    msj = get_match_error(match)
                    logging.info(msj + '\n')
        web.close()
        if len(result) > 0:
            filename_date = filename[:8]
            path_result_date = path(path_result, filename_date)
            if not os.path.exists(path_result_date):
                os.makedirs(path_result_date)
            path_result_filename = path(path_result_date, f'{filename}.json') # noqa
            save_matches(path_result_filename, result)
            send_matches(path_result_filename)
    except KeyboardInterrupt:
        print('\nFin...')


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

    main(path_file, overwrite)
