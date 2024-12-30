import os
import logging # noqa
import argparse
from utils import path
from utils import get_json
from utils import prepare_paths

path_result, path_cron, path_csv, path_json, path_html = prepare_paths('procesa_flashcore.log') # noqa

parser = argparse.ArgumentParser(
    description="Procesa Partidos de la hora Flashscore"
)
parser.add_argument(
    'file',
    type=str,
    help='Archivo de Partidos Flashscore'
)


def main(path_matches: str):
    matches = get_json(path_matches)
    for match in matches:
        print(match)


if __name__ == '__main__':
    args = parser.parse_args()
    path_file = path(path_cron, args.file)

    if not os.path.exists(path_file):
        print(f'Archivo {path_file} no existe')
        exit(1)

    main(path_file)
