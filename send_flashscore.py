import os
import logging # noqa
import pprint # noqa
import telebot
import argparse
import pygsheets
from datetime import datetime
from utils import path
from telebot import types
from utils import get_json
from utils import send_text
from dotenv import load_dotenv
from utils import prepare_paths
from sheet_utils import get_last_row
from sheet_utils import get_hum_fecha
from sheet_utils import update_formula

load_dotenv()

path_result, path_cron, path_csv, path_json, path_html = prepare_paths('envio_flashcore.log') # noqa

parser = argparse.ArgumentParser(description="Envia Partidos Telegram, Sheets")
parser.add_argument('file', type=str, help='Archivo de Partidos Flashscore')

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID').split(',')


def write_sheet_row(wks, row, match):
    #                                                                                  Home                Away                VS                Ganador        Ambos Marcan   HandiCap 0/0.5     HandiCap -1    HandiCap -2   Momios FT     Linea de Gol   Roja		Total               Dif Anotaran	Momio GP	      Local				Visitante		Goles Esp	Prob %	 % L	 % V	 % A	 X2	   Asiatico             Linea del tiempo GOL	                                   # noqa
    # ID   Fecha	Hora	Local	Visitante	AP	RESULTADO	Pais	Liga	1	2	3	4	5	1	2	3	4	5	1	2	3	4	5   Home	Away	     Si     No        HM	  AM	   HM	  AM	  HM	AM    -3.5	-4.5  1 	2	3	4  L	V	Final    Mensajes  Dif	uno	          dos	   G+	G-	PG+	PG-	    G+	G-	PG+	PG-	      tres	    cuatro	cinco	seis	siete	ocho	nueve      1	LV1	2	LV2	3	LV3	4	LV4	Total  Correcto	Estatus	L/V	Rango  # noqa
    fecha = get_hum_fecha(match['fecha'])
    home_matches = match['home_matches']['matches']
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

        '',  # Correcto
        '',  # Estatus
        '',  # L/V  *F  BV
        '',  # Rango  *F  BW
    ]
    wks.update_row(row, reg)

    update_formula(wks, 'AS', row)
    update_formula(wks, 'AT', row)
    update_formula(wks, 'AU', row)
    update_formula(wks, 'AX', row)
    update_formula(wks, 'AY', row)
    update_formula(wks, 'BB', row)
    update_formula(wks, 'BC', row)
    update_formula(wks, 'BD', row)
    update_formula(wks, 'BE', row)
    update_formula(wks, 'BF', row)
    update_formula(wks, 'BG', row)
    update_formula(wks, 'BH', row)
    update_formula(wks, 'BI', row)
    update_formula(wks, 'BJ', row)

    mensaje = update_formula(wks, 'AR', row)  # Mensaje
    resultado = update_formula(wks, 'G', row)  # RESULTADO

    return {
        'row': row,
        'mensaje': mensaje,
        'resultado': resultado
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


def get_match_error(match: dict):
    id = match['id']
    fecha = get_hum_fecha(match['fecha'])
    pais = match['pais']
    hora = match['hora']
    liga = match['liga']
    home = match['home']
    away = match['away']
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    _1x2 = 'OK' if match['1x2']['OK'] else match['1x2']['msj'] if 'msj' in match['1x2'] else 'NO' # noqa
    _ambos = 'OK' if match['ambos']['OK'] else match['ambos']['msj'] if 'msj' in match['ambos'] else 'NO' # noqa
    _goles = 'OK' if match['goles']['OK'] else match['goles']['msj'] if 'msj' in match['goles'] else 'NO' # noqa
    _handicap = 'OK' if match['handicap']['OK'] else match['handicap']['msj'] if 'msj' in match['handicap'] else 'NO' # noqa

    return f'''{timestamp}
#{id} {fecha} {hora}
{pais} {liga}
{home} v {away}
MOMIOS
1x2: {_1x2}
AMBOS: {_ambos}
GOLES: {_goles}
HANDICAP: {_handicap}
'''


def get_match_ok(match: dict, resultado: str = '', mensaje: str = ''):
    id = match['id']
    pais = match['pais']
    hora = match['hora']
    liga = match['liga']
    home = match['home']
    away = match['away']
    fecha = get_hum_fecha(match['fecha'])

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    msj = f'''{timestamp}
#{id} {fecha} {hora}
{pais} {liga}
{home} v {away}'''
    if resultado:
        msj += f'\n{resultado}'
    if mensaje:
        msj += f'\n{mensaje}'

    return msj


def process_match(wks, bot, match: dict):
    link = match['url']

    row = get_last_row(wks)
    result = write_sheet_row(wks, row, match)
    resultado = result['resultado']
    mensaje = result['mensaje']

    markup = types.InlineKeyboardMarkup()
    if link:
        link_boton = types.InlineKeyboardButton('Partido', url=link) # noqa
        markup.add(link_boton)
    msj = get_match_ok(match, resultado, mensaje)

    for chat_id in TELEGRAM_CHAT_ID:
        send_text(
            bot,
            chat_id,
            msj,
            markup
        )

    update_optional_columns(wks, row)


def send_matches(path_matches: str):
    logging.info(f'MarkIV Envio {path_matches}') # noqa
    try:
        matches = get_json(path_matches)

        path_script = os.path.dirname(os.path.realpath(__file__))
        service_file = path(path_script, 'feroslebosgc.json')
        gc = pygsheets.authorize(service_file=service_file)

        spreadsheet = gc.open('Mark 4')
        wks = spreadsheet.worksheet_by_title('Bot')
        bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

        for match in matches:
            process_match(wks, bot, match)
    except KeyboardInterrupt:
        print('\nFin...')


if __name__ == '__main__':
    args = parser.parse_args()
    filename = args.file
    path_file = path(path_result, filename.split('.')[0][:8], filename)

    if not os.path.exists(path_file):
        logging.info(f'Archivo {path_file} no existe')
        exit(1)

    send_matches(path_file)
