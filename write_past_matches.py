from utils import path
from time import sleep
from utils import gsheet
from utils import prepare_paths
from utils import get_jsons_folder
from sheet_utils import get_last_row
from send_flashscore import write_sheet_row

path_result, path_cron, path_csv, path_json, path_html = prepare_paths('write_past_flashscore.log') # noqa


def main():
    wks = gsheet('Bot2')
    path_ok = path(path_result, 'ok')
    past_matches = get_jsons_folder(path_ok)
    if len(past_matches) > 0:
        print(f'Matches {len(past_matches)}')
        for n, match in enumerate(past_matches):
            print(n, match['id'], match['fecha'], match['hora'])
            row = get_last_row(wks)
            write_sheet_row(wks, row, match)
            sleep(1)
    else:
        print('No Past Matches')


if __name__ == '__main__':
    main()
