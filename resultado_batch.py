import time

from gspread.exceptions import APIError
from utils import gsheet
from parse import get_marcador_ft


def main():
    wks = gsheet('Bot')
    bot_regs = wks.get_all_values()
    updates = []

    for row, value in enumerate(bot_regs):
        row_number = row + 1
        event_id = value[0]
        if not event_id or value[42]:
            continue

        home = value[3]
        away = value[4]
        hora = value[2]
        pais = value[7]
        liga = value[8]

        try:
            marcador = get_marcador_ft(event_id=event_id)
        except Exception as error:
            print(row_number, event_id, pais, liga, hora, home, away,
                  f'Error consultando feed: {error}; hoja sin cambios')
            continue

        if marcador is None:
            print(row_number, event_id, pais, liga, hora, home, away,
                  'Feed incompleto o inconsistente; hoja sin cambios')
            continue

        goal_1, goal_2, goal_3, goal_4, red_home, red_away = marcador['sheet']
        values = [[goal_1, goal_2, goal_3, goal_4, red_home, red_away, marcador['ft']]]
        updates.append({'range': f'AK{row_number}:AQ{row_number}', 'values': values})
        print(row_number, event_id, pais, liga, hora, home, away,
              'Finalizado', marcador['score'], marcador['sheet'])

    if updates:
        for attempt in range(3):
            try:
                wks.batch_update(updates, value_input_option='RAW')
                print(f'Google Sheets actualizado: {len(updates)} filas')
                break
            except APIError as error:
                if error.response.status_code != 429 or attempt == 2:
                    raise
                delay = 60 * (attempt + 1)
                print(f'Límite de Google Sheets; reintento en {delay}s')
                time.sleep(delay)


if __name__ == '__main__':
    main()
