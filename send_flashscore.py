import os
import pytz
import logging # noqa
import pprint # noqa
import telebot
import argparse
import pygsheets
from utils import path
from utils import wakeup
from utils import pathexist
from telebot import types
from utils import basename
from utils import get_json
from utils import send_text
from dotenv import load_dotenv
from utils import save_matches
from utils import prepare_paths
from sheet_utils import get_last_row
from sheet_utils import get_hum_fecha
from sheet_utils import update_formula
from datetime import datetime, timedelta

# https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json

load_dotenv()

path_result, path_cron, path_csv, path_json, path_html = prepare_paths('envio_flashcore.log') # noqa

parser = argparse.ArgumentParser(description="Envia Partidos Telegram, Sheets")
parser.add_argument('file', type=str, help='Archivo de Partidos Flashscore')
parser.add_argument('--cron', action='store_true', help="Programar")

cron = True
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID').split(',')


def write_sheet_row(wks, row, match):
    #                                                                                  Home                Away                VS                Ganador        Ambos Marcan   HandiCap 0/0.5     HandiCap -1    HandiCap -2   Momios FT     Linea de Gol   Roja		Total               Dif Anotaran	Momio GP	      Local				Visitante		Goles Esp	Prob %	 % L	 % V	 % A	 X2	   Asiatico             Linea del tiempo GOL	                                   # noqa
    # ID   Fecha	Hora	Local	Visitante	AP	RESULTADO	Pais	Liga	1	2	3	4	5	1	2	3	4	5	1	2	3	4	5   Home	Away	     Si     No        HM	  AM	   HM	  AM	  HM	AM    -3.5	-4.5  1 	2	3	4  L	V	Final    Mensajes  Dif	uno	          dos	   G+	G-	PG+	PG-	    G+	G-	PG+	PG-	      tres	    cuatro	cinco	seis	siete	ocho	nueve      1	LV1	2	LV2	3	LV3	4	LV4	Total  Correcto	Estatus	L/V	Rango  # noqa
    fecha = get_hum_fecha(match['fecha'])
    home_matches = match['home_matches']['matches']
    link = match['url']
    hmft_1 = home_matches[0]['ft']
    hmft_2 = home_matches[1]['ft']
    hmft_3 = home_matches[2]['ft']
    hmft_4 = home_matches[3]['ft']
    hmft_5 = home_matches[4]['ft']

    hgh = match['home_matches']['hechos']
    hgc = match['home_matches']['concedidos']

    away_matches = match['away_matches']['matches']
    awft_1 = away_matches[0]['ft']
    awft_2 = away_matches[1]['ft']
    awft_3 = away_matches[2]['ft']
    awft_4 = away_matches[3]['ft']
    awft_5 = away_matches[4]['ft']

    agh = match['away_matches']['hechos']
    agc = match['away_matches']['concedidos']

    vs_matches = match['vs_matches']['matches']
    vsft_1 = vs_matches[0]['ft']
    vsft_2 = vs_matches[1]['ft']
    vsft_3 = vs_matches[2]['ft']
    vsft_4 = vs_matches[3]['ft'] if len(vs_matches) > 3 else ''
    vsft_5 = vs_matches[4]['ft'] if len(vs_matches) > 4 else ''

    _1x2_h, _1x2_d, _1x2_a = match['1x2']['american']
    ambos_si, ambos_no = match['ambos']['american']
    handicap_h_1, handicap_a_1 = match['handicap']['odds']['0, -0.5']['decimal'] # noqa
    handicap_h_2, handicap_a_2 = match['handicap']['odds']['-1']['decimal']
    handicap_h_3, handicap_a_3 = match['handicap']['odds']['-2']['decimal'] if '-2' in match['handicap']['odds'] else ('', '') # noqa
    gol_35_p, gol_35_m = match['goles']['odds']['3.5']['american']
    gol_45_p, gol_45_m = match['goles']['odds']['4.5']['american'] if '4.5' in match['goles']['odds'] else ('', '') # noqa

    reg = [
        match['id'],  # ID,
        fecha,  # Fecha,
        match['hora'],  # Hora,
        match['home'],  # Home,
        match['away'],  # Away,
        '3.5',  # AP,
        '',  # RESULTADO,   *F   G
        match['pais'],  # Pais,
        match['liga'],  # Liga,
        hmft_1,  # home_matches 1,
        hmft_2,  # home_matches 2,
        hmft_3,  # home_matches 3,
        hmft_4,  # home_matches 4,
        hmft_5,  # home_matches 5,

        awft_1,  # away_matches 1,
        awft_2,  # away_matches 2,
        awft_3,  # away_matches 3,
        awft_4,  # away_matches 4,
        awft_5,  # away_matches 5,

        vsft_1,  # vs_matches 1,
        vsft_2,  # vs_matches 2,
        vsft_3,  # vs_matches 3,
        vsft_4,  # vs_matches 4,
        vsft_5,  # vs_matches 5,

        _1x2_h,  # Momios Home,
        _1x2_a,  # Momios Away,
        ambos_si,  # Momios Si,
        ambos_no,  # Momios No,
        handicap_h_1,  # Momios Handicap Home 0/-0.5,
        handicap_a_1,  # Momios Handicap Away 0/-0.5,
        handicap_h_2,  # Momios Handicap Home -1,
        handicap_a_2,  # Momios Handicap Away -1,
        handicap_h_3,  # Momios Handicap Home -2,
        handicap_a_3,  # Momios Handicap Away -2,
        gol_35_m,  # Momios -3.5,
        gol_45_m,  # Momios -4.5,

        '',  # Min Gol 1
        '',  # Min Gol 2
        '',  # Min Gol 3
        '',  # Min Gol 4
        '',  # ROJA Home
        '',  # ROJA Away
        '',  # TOTAL

        '',  # Mensaje  *F  AR
        '',  # Dif Anotaran  *F  AS
        '',  # uno  *F  AT
        '',  # Momio GP  *F  AU

        hgh,  # Home G+
        hgc,  # Home G-
        '',  # Home PG+  *F  AX
        '',  # Home PG-  *F  AY

        agh,  # Away G+
        agc,  # Away G-
        '',  # Away PG+  *F  BB
        '',  # Away PG-  *F  BC

        '',  # Goles Esperados Tres  *F  BD
        '',  # Prob % Cuatro  *F  BE
        '',  # % L Cinco  *F  BF
        '',  # % V Seis  *F  BG
        '',  # % A Siete  *F  BH
        '',  # X2 Ocho  *F  BI
        '',  # Asiatico Nueve  *F  BJ

        '',  # Linea del tiempo GOL 1  *F  BK
        '',  # Linea del tiempo GOL LV1  *F  BL
        '',  # Linea del tiempo GOL 2  *F  BM
        '',  # Linea del tiempo GOL LV2  *F  BN
        '',  # Linea del tiempo GOL 3  *F  BO
        '',  # Linea del tiempo GOL LV3  *F  BP
        '',  # Linea del tiempo GOL 4  *F  BQ
        '',  # Linea del tiempo GOL LV4  *F  BR
        '',  # Linea del tiempo GOL TOTAL  *F  BS

        '',  # Correcto BT
        '',  # Estatus
        '',  # L/V  *F  BV
        '',  # Rango  *F  BW
        '',  # X2    BX
        '',  # Hoja  BY
        '',  # CRango  BZ,
        '',  # Arc 3    CA
        '',
        link
    ]
    wks.update_row(row, reg)
    wks.update_value(f'BT{row}', 'SI')

    return {
        'row': row,
        'mensaje': '',
        'resultado': 'OK'
    }


def update_optional_columns(wks, row):
    update_formula(wks, 'BK', row)
    update_formula(wks, 'BL', row)
    update_formula(wks, 'BM', row)
    update_formula(wks, 'BN', row)
    update_formula(wks, 'BO', row)
    update_formula(wks, 'BP', row)
    update_formula(wks, 'BQ', row)
    update_formula(wks, 'BR', row)
    update_formula(wks, 'BS', row)
    update_formula(wks, 'BV', row)
    update_formula(wks, 'BW', row)


def get_match_error(match: dict):
    id = match['id']
    fecha = get_hum_fecha(match['fecha'])
    pais = match['pais']
    hora = match['hora']
    liga = match['liga']
    home = match['home']
    away = match['away']
    status = match['status'] if 'status' in match else ''
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    _1x2, _ambos, _goles, _handicap = 'NO', 'NO', 'NO', 'NO'
    if status != 'aplazado':
        _1x2 = 'OK' if match['1x2']['OK'] else match['1x2']['msj'] if 'msj' in match['1x2'] else 'NO' # noqa
        _ambos = 'OK' if match['ambos']['OK'] else match['ambos']['msj'] if 'msj' in match['ambos'] else 'NO' # noqa
        _goles = 'OK' if match['goles']['OK'] else match['goles']['msj'] if 'msj' in match['goles'] else 'NO' # noqa
        _handicap = 'OK' if match['handicap']['OK'] else match['handicap']['msj'] if 'msj' in match['handicap'] else 'NO' # noqa
    momios = f'''
MOMIOS
1x2: {_1x2}
AMBOS: {_ambos}
GOLES: {_goles}
HANDICAP: {_handicap}
'''
    msj = f'''{timestamp}
#{id} {fecha} {hora} {status}
{pais} {liga}
{home} v {away}'''
    if status == '':
        msj += momios
    return msj


def get_match_ok(match: dict, resultado: str = '', mensaje: str = ''):
    pais = match['pais']
    hora = match['hora']
    liga = match['liga']
    home = match['home']
    away = match['away']
    fecha = get_hum_fecha(match['fecha'])
    # timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    msj = f'''{fecha} {hora}
{pais} {liga}
{home} v {away}'''
    if resultado:
        msj += f'\n{resultado}'

    return msj


def process_match(wks, bot, match: dict):
    link = match['url']

    msj = get_match_ok(match, '', '')
    markup = types.InlineKeyboardMarkup()
    if link:
        link_boton = types.InlineKeyboardButton('Apostar', url=link) # noqa
        markup.add(link_boton)
    for chat_id in TELEGRAM_CHAT_ID:
        send_text(
            bot,
            chat_id,
            msj,
            markup
        )

    row = get_last_row(wks)
    result = write_sheet_row(wks, row, match)
    mensaje = result['mensaje']
    resultado = result['resultado']
    match['mensaje'] = mensaje
    match['resultado'] = resultado
    match['row'] = row

    return match


def send_matches(path_matches: str):
    global cron
    filename = basename(path_matches)
    filename_fechahora = basename(path_matches, True)
    dt_filename = datetime.strptime(filename_fechahora, "%Y%m%d%H%M")
    fecha = dt_filename.strftime('%Y%m%d')
    path_ok = path(path_result, fecha, 'ok')
    if not pathexist(path_ok):
        os.makedirs(path_ok)
    path_filename = path(path_ok, filename)
    logging.info(f'MarkIV Envio {filename}') # noqa
    print('')
    try:
        matches = get_json(path_matches)

        path_script = os.path.dirname(os.path.realpath(__file__))
        service_file = path(path_script, 'feroslebosgc.json')
        gc = pygsheets.authorize(service_file=service_file)

        spreadsheet = gc.open('Mark 4')
        wks = spreadsheet.worksheet_by_title('Bot')
        bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

        matches_, rows = [], []

        for n, match in enumerate(matches):
            logging.info(f'{match["home"]} v {match["away"]} {match["fecha"]} {match["hora"]} | {n}-{len(matches)}') # noqa
            print('')
            match = process_match(wks, bot, match)
            matches_.append(match)
            if match['row'] is not None:
                rows.append(match['row'])

        save_matches(path_filename, matches_, True, debug=False)

        tres_hora = timedelta(hours=4)
        fechahora_partidos = dt_filename.replace(tzinfo=pytz.timezone('America/Mexico_City')) # noqa
        dt_partidos_p3h = fechahora_partidos + tres_hora

        task_result = wakeup(
            'Resultado',
            'resultado_flashscore.py',
            dt_partidos_p3h,
            filename,
            len(matches_)
        )
        print(task_result)

        # if len(rows) > 0:
        #     for row in rows:
        #         update_optional_columns(wks, row)
    except Exception as e:
        logging.error(f'Error: {e}')
    except KeyboardInterrupt:
        print('\nFin...')


if __name__ == '__main__':
    args = parser.parse_args()
    filename = args.file
    date = filename.split('.')[0][:8]
    path_file = path(path_result, date, filename)

    if not os.path.exists(path_file):
        logging.info(f'Archivo {path_file} no existe')
        exit(1)

    send_matches(path_file)
