import os
import logging # noqa
import argparse
import pprint # noqa
from web import Web
from utils import path
from utils import basename
from parse import get_momios
from utils import save_matches
from utils import prepare_paths
from utils import get_json_list
from utils import get_match_ok
from utils import get_match_error
from parse import status_partido
from parse import get_marcador_ft
from parse import click_momios_btn
from parse import remueve_anuncios
from parse import click_OK_cookies_btn
from send_flashscore import send_matches

path_result, path_cron, path_csv, path_json, path_html = prepare_paths() # noqa

parser = argparse.ArgumentParser(
    description="Procesa Partidos de la hora Flashscore"
)
parser.add_argument('file', type=str, help='Archivo de Partidos Flashscore')
parser.add_argument('--over', action='store_true', help="Sobreescribir")


def main(path_matches: str, overwrite: bool = False):
    filename = basename(path_matches, True)
    logging.info(f'Momios MarkIV {filename} {path_matches}') # noqa
    web = Web(multiples=True)
    result = []
    matches = get_json_list(path_matches)
    try:
        for n, match in enumerate(matches):
            link = match['url']
            filename_match = match['filename_match']
            web.open(link)
            web.wait(1)
            if n == 0:
                click_OK_cookies_btn(web) # noqa

            remueve_anuncios(web)

            status = status_partido(web)
            match['status'] = status
            if status == 'finalizado':
                web.wait(1)
                btn_resumen = click_momios_btn('resumen', web)
                if btn_resumen:
                    input('hay resumen')
                    try:
                        web.wait(3)
                        marcador = get_marcador_ft(web)
                        sheet = marcador['sheet']
                        total_goles = marcador['ft']
                        gol1, gol2, gol3, gol4, rojahome, rojas_away = sheet
                        match['ft'] = total_goles
                        match['sheet_goles'] = sheet
                        match['rojas_home'] = rojahome
                        match['rojas_away'] = rojas_away
                        match['status'] = 'finalizado'
                    except Exception as e:
                        web.wait(1)
                        logging.error(f'Error al obtener marcador: {e}')
                else:
                    input('No hay resumen')
                click_momios_btn('momios', web)
                web.wait(3)
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
