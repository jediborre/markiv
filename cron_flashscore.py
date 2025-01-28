import os
import json
import pytz
import logging # noqa
import argparse
from utils import path
from utils import wakeup
from utils import get_json
# from utils import is_admin
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
parser.add_argument(
    '--admin',
    action='store_true',
    help='Is Admin'
)


def cron_matches(path_matches: str, debug_hora=None):
    result = {
        'fecha': '',
        'cron': [],
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
        cron_m1h = fechahora_partido_m1h.strftime('%Y%m%d%H%M')
        match['programacion'] = fechahora_partido_m1h.strftime('%Y-%m-%d %H:%M:%S') # noqa

        if hora_actual <= fechahora_partido_m1h:
            if cron_m1h not in result:
                result[cron_m1h] = []
                result['cron'].append([match['programacion'], cron_m1h])
            result[cron_m1h].append(match)
        else:
            descartados += 1

    print(f'Partidos {result["fecha"]}: {len(matches)}')
    for fecha_programacion, ts in result['cron']:
        date = ts[:8]
        cron_matches = result[ts]
        hora = fecha_programacion[11:]
        fecha_hora_programacion = result["fecha"] + ' ' + fecha_programacion[11:] # noqa
        work = True
        if debug_hora:
            if hora != debug_hora:
                work = False
        if work:
            print(f'{date} {hora} {len(cron_matches)}')
            path_cron_date = path(path_cron, date)
            if not os.path.exists(path_cron_date):
                os.makedirs(path_cron_date)
            path_cron_matches = path(path_cron_date, f'{ts}.json')
            with open(path_cron_matches, 'w') as f:
                f.write(json.dumps(cron_matches, indent=4))
                task_result = wakeup('process_flashscore.py', fecha_hora_programacion, ts, len(cron_matches)) # noqa
                if len(cron_matches) > 1:
                    for m in cron_matches:
                        print(f'{m["hora"]}|{m["id"]}|{m["pais"]} : {m["liga"]}|{m["home"]} - {m["away"]}') # noqa
                    logging.info(task_result)
                else:
                    for m in cron_matches:
                        logging.info(f'{m["hora"]}|{m["id"]}|{m["pais"]} : {m["liga"]}|{m["home"]} - {m["away"]} {task_result}') # noqa

    print(f"\nDescartados: {descartados}")


if __name__ == '__main__':
    args = parser.parse_args()
    path_file = path(path_result, args.file)

    if not os.path.exists(path_file):
        print(f'Archivo {path_file} no existe')
        exit(1)

    cron_matches(path_file)
