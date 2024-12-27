import os
import json
import pytz
import logging # noqa
import argparse
from utils import path
from utils import prepare_paths
from datetime import datetime, timedelta

path_result, path_cron, path_csv, path_json, path_html = prepare_paths('cron_flashcore.log') # noqa

parser = argparse.ArgumentParser(
    description="Solicita partidos de hoy o mañana de flashscore"
)
parser.add_argument(
    'file',
    type=str,
    help='Archivo de Partidos Flashscore'
)


def get_json(path_file: str):
    return json.loads(open(path_file, 'r').read())


def main(path_matches: str):
    result = {
        'fecha': '',
        'matches': [],
        'filename_matches': ''
    }
    matches = get_json(path_matches)
    if len(matches) == 0:
        print('No hay Partidos')
        return

    descartados = 0
    print(f'Procesando {len(matches)} partidos\n\n')
    for m in matches:
        match = matches[m]
        match['hora'] = match['hora'][:5]
        hora = match['hora']
        fecha = match['fecha']
        filename_fecha = match['filename_fecha']
        result['fecha'] = fecha
        result['filename_matches'] = path(path_result, f'{filename_fecha}.json') # noqa
        una_hora = timedelta(hours=1)
        hora_actual = datetime.now(pytz.timezone('America/Mexico_City')) # noqa
        fechahora_partido = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M").replace(tzinfo=pytz.timezone('America/Mexico_City')) # noqa
        fechahora_partido_m1h = fechahora_partido - una_hora
        match['programacion'] = fechahora_partido_m1h.strftime('%Y-%m-%d %H:%M:%S') # noqa

        if hora_actual <= fechahora_partido_m1h:
            result['matches'].append(match)
        else:
            descartados += 1 

    print(f'Partidos {result["fecha"]}: {len(result["matches"])}')
    for m in result['matches']:
        print(f'{m["id"]}|{m["programacion"]}|{m["hora"]}|{m["pais"]} : {m["liga"]}|{m["home"]} - {m["away"]}') # noqa
    print(f'Descartados: {descartados}')


if __name__ == '__main__':
    args = parser.parse_args()
    path_file = path(path_result, args.file)

    if not os.path.exists(path_file):
        print(f'Archivo {path_file} no existe')
        exit(1)

    main(path_file)
