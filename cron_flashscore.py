import os
import pytz
import logging # noqa
import argparse
from utils import path
from utils import wakeup
from utils import save_matches
from utils import get_json_list
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
    matches = get_json_list(path_matches)
    if len(matches) == 0:
        print('No hay Partidos')
        return

    descartados = 0
    print(f'\nProcesando {len(matches)} partidos\n\n')
    for match_id in matches:
        match = matches[match_id]
        match['hora'] = match['hora'][:5]
        hora = match['hora']
        fecha = match['fecha']
        filename_fecha = match['filename_fecha']
        result['fecha'] = fecha
        result['filename_matches'] = path(path_result, f'{filename_fecha}.json') # noqa

        if ':' not in hora:
            continue

        # Programacion Hora Partido - 1 hora
        una_hora = timedelta(hours=1)
        zona_horaria = pytz.timezone('America/Mexico_City')
        dt_horaactual = datetime.now(zona_horaria)

        dt_partido = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
        dt_partido = zona_horaria.localize(dt_partido)

        dt_partido_m1h = dt_partido - una_hora
        fechahora_partido_m1h = dt_partido_m1h.strftime('%Y%m%d%H%M')
        if debug_hora:
            print(match_id, fecha, hora, '->', dt_partido_m1h.strftime('%Y-%m-%d %H:%M'), dt_partido_m1h.isoformat()) # noqa

        if dt_horaactual <= dt_partido_m1h:
            if fechahora_partido_m1h not in result:
                result[fechahora_partido_m1h] = []
                result['cron'].append(dt_partido_m1h) # noqa
            match['programacion'] = dt_partido_m1h.strftime('%Y-%m-%d %H:%M:%S') # noqa
            result[fechahora_partido_m1h].append(match)
        else:
            descartados += 1

    print(f'PARTIDOS {result["fecha"]}: {len(matches)}')
    for dt_partido in result['cron']:
        work = True
        hora = dt_partido.strftime('%H:%M')
        fecha = dt_partido.strftime('%Y-%m-%d')
        fecha_ = dt_partido.strftime('%Y%m%d')
        fechahora = dt_partido.strftime('%Y%m%d%H%M')
        cron_matches = result[fechahora]

        if debug_hora:
            if hora != debug_hora:
                work = False
        if work:
            print(f'{hora} {len(cron_matches)}')

            path_cron_date = path(path_cron, fecha_)
            if not os.path.exists(path_cron_date):
                os.makedirs(path_cron_date)
            filename_cron = f'{fechahora}.json'
            path_cron_matches = path(path_cron_date, filename_cron) # noqa

            save_matches(path_cron_matches, cron_matches, True)
            task_result = wakeup(
                'ODDS',
                'process_flashscore.py',
                dt_partido,
                filename_cron,
                len(cron_matches)
            )
            if len(cron_matches) > 1:
                for m in cron_matches:
                    print(f'{m["hora"]}|{m["id"]}|{m["pais"]} : {m["liga"]}|{m["home"]} - {m["away"]}') # noqa
                logging.info(task_result)
            else:
                for m in cron_matches:
                    logging.info(f'{m["hora"]}|{m["id"]}|{m["pais"]} : {m["liga"]}|{m["home"]} - {m["away"]} {task_result}') # noqa

    print(f"\nPARTIDOS CANDIDATOS {result["fecha"]}: {len(matches)}") # noqa
    if descartados > 0:
        print(f'Descartados: {descartados}')


if __name__ == '__main__':
    args = parser.parse_args()
    path_file = path(path_result, args.file)

    if not os.path.exists(path_file):
        print(f'Archivo {path_file} no existe')
        exit(1)

    cron_matches(path_file)
