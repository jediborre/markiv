import re
import os
import sys
import json
import base64
import pprint # noqa
import logging
import vertexai
import platform
import pygsheets
import pywintypes
if os.name == 'nt':
    import ctypes
    import win32com.client
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime
from text_unidecode import unidecode
from vertexai.generative_models import GenerativeModel, Part, SafetySetting

sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

matches_result = []
GSHEET_AUTH = os.getenv('GSHEET_AUTH', '')
SPREADSHEET_NAME = os.getenv('SPREADSHEET_NAME', 'Viernes')


def is_windows():
    """Verifica si el sistema operativo es Windows."""
    return platform.system() == 'Windows'


def close_console():
    """
    Cierra la ventana de consola actual si el script se está ejecutando en una.
    """
    try:
        if is_windows():
            import win32gui
            import win32con
            console_window = ctypes.windll.kernel32.GetConsoleWindow()
            if console_window != 0:
                print("Cerrando ventana de consola...")
                win32gui.PostMessage(console_window, win32con.WM_CLOSE, 0, 0)
                # os.system("exit")
                # os._exit(0)
    except Exception as e:
        print(f"Error al intentar cerrar la ventana de consola: {e}")


def safe_float(value, default=np.nan):
    if value in ('-', '', None) or pd.isna(value):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default=np.nan):
    if value in ('-', '', None) or pd.isna(value):
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def cls():
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')


def busca_id_bot(bot_regs, id: str):
    for row, value in enumerate(bot_regs):
        if value[0] == id:
            return row + 1
    return None


def convert_dt(dt_str):
    if len(dt_str) == 8: # noqa yy-mm-dd
        return datetime.strptime(dt_str, '%y-%m-%d')
    if len(dt_str) == 10:
        return datetime.strptime(dt_str, '%Y-%m-%d')
    elif len(dt_str) == 16:
        return datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
    return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')


def is_prod():
    SERVER = os.getenv('SERVER', 'dev').lower()
    return SERVER == 'prod'


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


class StreamHandlerNoNewLine(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            stream.write(msg)
            stream.flush()
        except Exception:
            self.handleError(record)


def gsheet(sheet_name):
    global SPREADSHEET_NAME, GSHEET_AUTH
    if not GSHEET_AUTH:
        logging.error("Google Sheets authentication file not found.")
        return None

    if not SPREADSHEET_NAME:
        logging.error("Google Sheets spreadsheet name not set.")
        return None

    if not sheet_name:
        logging.error("Google Sheets sheet name not set.")
        return None

    path_script = os.path.dirname(os.path.realpath(__file__))
    service_file = path(path_script, GSHEET_AUTH)
    gc = pygsheets.authorize(service_file=service_file)

    spreadsheet = gc.open(SPREADSHEET_NAME)
    return spreadsheet.worksheet_by_title(sheet_name)


def get_jsons_folder(folder_path):
    merged_list = []

    for filename in os.listdir(folder_path):
        if filename.endswith('.json'):  # Only process JSON files
            file_path = os.path.join(folder_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as json_file:
                    data = json.load(json_file)

                    if isinstance(data, list):
                        merged_list.extend(data)  # Merge lists
                    else:
                        print(f"Warning: {filename} does not contain a list.")
            except Exception as e:
                print(f"Error reading {filename}: {e}")

    return merged_list


def get_json_dict(path_file: str):
    if not pathexist(path_file):
        return {}
    return json.loads(open(path_file, 'r').read())


def get_json_list(path_file: str):
    if not pathexist(path_file):
        return []
    return json.loads(open(path_file, 'r').read())


def wakeup(operation: str, script: str, dt_programacion: datetime, filename: str, num_matches: int): # noqa
    try:
        hr = dt_programacion.strftime('%H%M')
        if os.name == 'nt':
            WD = os.path.dirname(os.path.abspath(__file__))
            script_path = os.path.join(WD, script)
            python_path = os.path.join(WD, '.venv', 'Scripts', 'python.exe')
            if not pathexist(python_path):
                logging.error(f"Python executable not found at {python_path}")
                return
            if not pathexist(script_path):
                logging.error(f"Script not found at {script_path}")
                return

            return create_task(
                f'{operation} {hr} {num_matches}',
                dt_programacion,
                python_path,
                script_path,
                filename
            )
    except Exception as e:
        logging.exception(f"Exception occurred in wakeup function: {e}")


def create_task(task_name, trigger_time, python_path, script_path, args):
    try:
        if not os.name == 'nt':
            logging.exception("Unsupported operating system")
            return

        scheduler = win32com.client.Dispatch('Schedule.Service')
        scheduler.Connect()

        rootFolder = scheduler.GetFolder('\\')

        taskDef = scheduler.NewTask(0)

        trigger = taskDef.Triggers.Create(1)
        trigger.StartBoundary = trigger_time.isoformat()
        trigger.Enabled = True

        action = taskDef.Actions.Create(0)
        action.Path = python_path
        action.Arguments = f'"{script_path}" {args}'

        taskDef.RegistrationInfo.Description = f'Friday Match {args}'
        taskDef.Principal.UserId = r'ROBOT\\Robot'
        taskDef.Principal.LogonType = 3

        rootFolder.RegisterTaskDefinition(
            task_name,
            taskDef,
            6,  # TASK_CREATE_OR_UPDATE
            '',  # No user
            '',  # No password
            3,  # TASK_LOGON_SERVICE_ACCOUNT
            None
        )
        return f"New Task '{task_name}' @{trigger_time}"

    except pywintypes.com_error:
        logging.error(f"COM error occurred while creating task '{task_name}': "
                      f"Access Denied\n")
    except Exception as e:
        logging.exception(f"Exception occurred while creating the task: {e}")
    return None


def limpia_nombre(nombre, post=True):
    nombre = re.sub(r'\s+', ' ', re.sub(r'\.|\/|\(|\)', '', nombre)).strip()
    nombre = unidecode(nombre)
    return nombre


def get_percent(n, total):
    return f'{round(n / total * 100, 2)}%'


def basename(filename, noext=False):
    if pathexist(filename):
        if noext:
            return os.path.basename(filename).split('.')[0]
        return os.path.basename(filename)
    else:
        return filename


def path(*paths):
    return os.path.join(*paths)


def pathexist(*paths):
    return os.path.exists(path(*paths))


def prepare_paths_ok(log_filename='seguimiento_friday.log'):
    script_path = os.path.dirname(os.path.abspath(__file__))
    log_path = path(script_path, 'logs')
    log_filepath = path(log_path, log_filename)
    path_result = path(script_path, 'result')
    path_ok = path(path_result, 'ok')

    if not pathexist(path_result):
        os.makedirs(path_result)

    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=[
            logging.FileHandler(log_filepath, encoding='utf-8'),
            StreamHandlerNoNewLine(sys.stdout)
        ]
    )
    return [path_result, path_ok]


def prepare_paths(log_filename=''):
    script_path = os.path.dirname(os.path.abspath(__file__))
    path_tmp = path(script_path, 'tmp')
    path_log = path(script_path, 'logs')
    path_csv = path(path_tmp, 'csv')
    path_html = path(path_tmp, 'html')
    path_json = path(path_tmp, 'json')

    log_filepath = path(path_log, log_filename)
    path_result = path(script_path, 'result')
    path_cron = path(script_path, 'cron')

    if not pathexist(path_result):
        os.makedirs(path_result)
    if not pathexist(path_log):
        os.makedirs(path_log)
    if not pathexist(path_cron):
        os.makedirs(path_cron)
    if not pathexist(path_tmp):
        os.makedirs(path_tmp)
    if not pathexist(path_csv):
        os.makedirs(path_csv)
    if not pathexist(path_html):
        os.makedirs(path_html)
    if not pathexist(path_json):
        os.makedirs(path_json)

    if log_filename:
        logging.basicConfig(
            level=logging.INFO,
            format='%(message)s',
            handlers=[
                logging.FileHandler(log_filepath, encoding='utf-8'),
                StreamHandlerNoNewLine(sys.stdout)
            ]
        )
    return [
        path_result,
        path_cron,
        path_csv,
        path_json,
        path_html
    ]


def keys_uppercase(json_data):
    if isinstance(json_data, dict):
        return {key.upper(): keys_uppercase(value) for key, value in json_data.items()} # noqa
    elif isinstance(json_data, list):
        return [keys_uppercase(item) for item in json_data]
    else:
        return json_data


def decimal_american(odds_decimal):
    if odds_decimal == '-':
        return '-'

    odds_float = float(odds_decimal)

    if odds_float == 1.0:
        return '-'
        # raise ValueError("Decimal odds cannot be 1.0 (division by zero).")

    if odds_float >= 2.0:
        return f"+{int((odds_float - 1) * 100)}"
    else:
        return f"{int(round(-100 / (odds_float - 1) / 50) * 50)}"


def get_momios_image(img_filename):
    img_filepath = os.path.join('img', img_filename)
    if pathexist(img_filepath):
        response_dir = 'gemini'
        response_filename = os.path.splitext(os.path.basename(img_filepath))[0]
        response_filepath = os.path.join(response_dir, f'{response_filename}_gemini.json') # noqa
        processed_filepath = os.path.join(response_dir, f'{response_filename}_ok.json') # noqa
        os.makedirs(response_dir, exist_ok=True)
        logging.info(f'Obteniendo momios desde {img_filepath}')
        gemini_response = get_gemini_response(img_filepath)
        with open(response_filepath, 'w', encoding='utf-8') as f:
            f.write(gemini_response)
        result = parse_gemini_response(response_filepath)
        with open(processed_filepath, 'w') as f:
            json.dump(result, f)
        logging.info('Momios Procesados')
        return result
    else:
        logging.error(f'get_momios_image {img_filepath} not exist')


def parse_gemini_response(filepath):
    with open(filepath, encoding='utf-8') as my_file:
        result = my_file.read()
        json_data = json.loads(result)
        json_data = keys_uppercase(json_data)
        # pprint.pprint(json_data)
        ht_gol = json_data['1RA MITAD TOTAL DE GOLES OVER UNDER']
        ft_gol = json_data['TOTAL GOLES OVER UNDER']
        ft = json_data['RESULTADO FINAL TIEMPO REGULAR']
        ambos = json_data['AMBOS EQUIPOS ANOTAN']
        ht_u05 = ht_gol['U 0.5'] if 'U 0.5' in ht_gol else '-'
        ht_u15 = ht_gol['U 1.5'] if 'U 1.5' in ht_gol else '-'
        ht_u25 = ht_gol['U 2.5'] if 'U 2.5' in ht_gol else '-'
        ft_u05 = ft_gol['U 0.5'] if 'U 0.5' in ft_gol else '-'
        ft_u15 = ft_gol['U 1.5'] if 'U 1.5' in ft_gol else '-'
        ft_u25 = ft_gol['U 2.5'] if 'U 2.5' in ft_gol else '-'
        ft_u35 = ft_gol['U 3.5'] if 'U 3.5' in ft_gol else '-'
        ft_u45 = ft_gol['U 4.5'] if 'U 4.5' in ft_gol else '-'
        momio_home = ft['1'] if '1' in ft else '-'
        momio_away = ft['2'] if '2' in ft else '-'
        momio_si = ambos['SI'] if 'SI' in ambos else '-'
        momio_no = ambos['NO'] if 'NO' in ambos else '-'
        res = {
            'momio_home': momio_home,
            'momio_away': momio_away,
            'momio_si': momio_si,
            'momio_no': momio_no,
            'momio_ht_05': ht_u05,
            'momio_ht_15': ht_u15,
            'momio_ht_25': ht_u25,
            'momio_ft_05': ft_u05,
            'momio_ft_15': ft_u15,
            'momio_ft_25': ft_u25,
            'momio_ft_35': ft_u35,
            'momio_ft_45': ft_u45,
        }
        return res


def get_gemini_response(image_filename):
    safety_settings = [
        SafetySetting(
            category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=SafetySetting.HarmBlockThreshold.OFF
        ),
        SafetySetting(
            category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, # noqa
            threshold=SafetySetting.HarmBlockThreshold.OFF
        ),
        SafetySetting(
            category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, # noqa
            threshold=SafetySetting.HarmBlockThreshold.OFF
        ),
        SafetySetting(
            category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=SafetySetting.HarmBlockThreshold.OFF
        ),
    ]
    with open(image_filename, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode("utf-8")

    vertexai.init(project="feroslebos", location="us-west4")
    model = GenerativeModel("gemini-1.5-flash-002")
    image_part = Part.from_data(
        mime_type="image/jpeg",
        data=base64.b64decode(image_data),
    )
    response = model.generate_content(
        [image_part, "Momios en JSON valido"],
        generation_config={
            'max_output_tokens': 1500,
            'temperature': 1,
            'top_p': 0.95,
        },
        safety_settings=safety_settings,
        stream=False,
    )

    text_response = response.text.strip('```json').strip()
    text_response = re.sub(r'\+', '', text_response)
    text_response = re.sub(r'\(|\)', '', text_response)
    text_response = re.sub(r'\/', ' ', text_response)
    logging.info('Momios Recibidos...')
    # text_response = re.sub(r'^U (\d+\.\d+)', r'UNDER \1', text_response)
    # text_response = re.sub(r'^O (\d+\.\d+)', r'OVER \1', text_response)
    return text_response


def save_matches(filename, matches, overwrite=False, debug=False):
    if overwrite:
        if pathexist(filename):
            os.remove(filename)

    if not pathexist(filename):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(matches, f, indent=4)
            if debug:
                print(f'Guardado → {filename}')


def save_match(filename, match):
    global matches_result
    matches_result.append(match)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(matches_result, f, indent=4)


def send_text(telegram_bot, chat_id, text, markup=None):
    if len(text) <= 4096:
        telegram_bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=markup
        )
    else:
        parts = [text[i:i + 4096] for i in range(0, len(text), 4096)]
        for part in parts:
            telegram_bot.send_message(
                chat_id=chat_id,
                text=part
            )


def decimal_americano(momio_decimal):
    momio_decimal = float(momio_decimal)
    if momio_decimal == 1:
        return "0"
    elif momio_decimal >= 2:
        momio_americano = (momio_decimal - 1) * 100
    else:
        momio_americano = -100 / (momio_decimal - 1)
    return int(round(momio_americano, 0))


def es_momio_americano(texto):
    try:
        if texto == '-':
            return True
        momio = int(texto) # noqa
        if momio < -99 or momio > 99:
            return True
        else:
            return False
    except ValueError:
        return False


def get_paises_count(paises):
    result = []
    num_juegos = 0
    pais_cuenta = []
    for pais in paises:
        n_juegos_pais = len(paises[pais])
        pais_cuenta.append([pais, n_juegos_pais])
        num_juegos += n_juegos_pais
    result.append(f'Juegos de hoy: {num_juegos}')
    pais_cuenta_sorted = sorted(
        pais_cuenta,
        key=lambda x: x[1],
        reverse=True
    )
    if len(pais_cuenta_sorted) > 0:
        for pais, n in pais_cuenta_sorted:
            result.append(f'{pais} [{n}]')
    return '\n'.join(result)


def get_match_paises(matches) -> str:
    result = []
    for match in matches:
        id = match["id"]
        time = match["time"]
        liga = match["liga"]
        home = match["home"]
        away = match["away"]
        result.append(f'#{id} {time} {liga} {home} - {away}')

    return '\n'.join(result)


def get_match_details(match, with_momios=False) -> str:
    # print(match)
    id = match['id']
    fecha = match['fecha']
    home = match['home']
    away = match['away']
    liga = match['liga']
    pais = match['pais'] + ' ' if match['pais'] != 'sinpais' else ''
    pGol = match['promedio_gol']
    home_matches = match['home_matches']
    away_matches = match['away_matches']
    face_matches = match['face_matches']

    home_games, home_gP, home_gM, home_pgP, home_pgM = '', '', '', '', ''
    if len(home_matches) > 0:
        home_gP = home_matches['hechos']
        home_gM = home_matches['concedidos'][0]
        home_pgP = home_matches['p_hechos']
        home_pgM = home_matches['p_concedidos']
        home_games = '\n'.join(f'{m["ft"]}    {m["home_ft"]} - {m["away_ft"]}    {m["home"][:5]} - {m["away"][:5]}' for m in home_matches['matches']) # noqa

    away_gP, away_gM, away_pgP, away_pgM, away_games = '', '', '', '', ''
    if len(away_matches) > 0:
        away_gP = away_matches['hechos']
        away_gM = away_matches['concedidos'][0]
        away_pgP = away_matches['p_hechos']
        away_pgM = away_matches['p_concedidos']
        away_games = '\n'.join(f'{m["ft"]}    {m["home_ft"]} - {m["away_ft"]}    {m["home"][:5]} - {m["away"][:5]}' for m in away_matches['matches']) # noqa

    face_games = ''
    if len(face_matches) > 0:
        face_games = '\n'.join(f'{m["ft"]}    {m["home_ft"]} - {m["away_ft"]}    {m["home"][:5]} - {m["away"][:5]}' for m in face_matches['matches']) # noqa

    result = f'''
#{id} {fecha}
{pais}{liga}
{home} v {away}'''

    if all([pGol != '', home_gP != '', home_gM != '', home_pgP != '', home_pgM != '', home_games != '']): # noqa
        result += f'''G PARTIDO: {pGol}
{home}
+: {home_gP} -: {home_gM} P+: {home_pgP} P-: {home_pgM}
{home_games}'''

    if all([away_gP != '', away_gM != '', away_pgP != '', away_pgM != '', away_games != '']): # noqa
        result += f'''
{away}
+: {away_gP} -: {away_gM} P+: {away_pgP} P-: {away_pgM}
{away_games}'''
    if face_games != '':
        result += f'''
vs
{face_games}''' # noqa
    if with_momios:
        momio_home = match['momio_home'] if 'momio_home' in match else ''
        momio_away = match['momio_away'] if 'momio_away' in match else ''
        momio_si = match['momio_si'] if 'momio_si' in match else ''
        momio_no = match['momio_no'] if 'momio_no' in match else ''
        momio_ht_05 = match['momio_ht_05'] if 'momio_ht_05' in match else ''
        momio_ht_15 = match['momio_ht_15'] if 'momio_ht_15' in match else ''
        momio_ht_25 = match['momio_ht_25'] if 'momio_ht_25' in match else ''
        momio_ft_05 = match['momio_ft_05'] if 'momio_ft_05' in match else ''
        momio_ft_15 = match['momio_ft_15'] if 'momio_ft_15' in match else ''
        momio_ft_25 = match['momio_ft_25'] if 'momio_ft_25' in match else ''
        momio_ft_35 = match['momio_ft_35'] if 'momio_ft_35' in match else ''
        momio_ft_45 = match['momio_ft_45'] if 'momio_ft_45' in match else ''
        result += f'''

Ganador: {momio_home} {momio_away}
Ambos Anotan: {momio_si} {momio_no}
Gol HT: {momio_ht_05} {momio_ht_15} {momio_ht_25}
 bvnGol FT: {momio_ft_05} {momio_ft_15} {momio_ft_25} {momio_ft_35} {momio_ft_45}''' # noqa
    return result


def get_hum_fecha(fecha):
    mes = {
        '01': 'Ene',
        '02': 'Feb',
        '03': 'Mar',
        '04': 'Abr',
        '05': 'May',
        '06': 'Jun',
        '07': 'Jul',
        '08': 'Ago',
        '09': 'Sep',
        '10': 'Oct',
        '11': 'Nov',
        '12': 'Dic',
    }
    if fecha:
        y, m, d = fecha.split('-')
        return f'{mes[m]} {d} {y}'
    else:
        return fecha


def get_match_ok(match: dict, resultado: str = '', mensaje: str = ''):
    pais = match['pais']
    hora = match['hora']
    liga = match['liga_mod'] if 'liga_mod' in match else match['liga']
    home = match['home']
    away = match['away']
    fecha = get_hum_fecha(match['fecha'])
    # timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    msj = f'''{fecha} {hora}
{pais} {liga}
{home} v {away}'''
    if resultado:
        msj += f'\n{resultado}'
    if mensaje:
        msj += f'\n{mensaje}'

    return msj


def get_match_error(match: dict):
    id = match['id']
    link = match['url']
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
{link}
#{id} {fecha} {hora} {status}
{pais} {liga}
{home} v {away}'''
    if status == '':
        msj += momios
    return msj


def get_match_error_short(match: dict):
    status = match['status'] if 'status' in match else ''
    _1x2, _ambos, _goles, _handicap = 'NO', 'NO', 'NO', 'NO'
    if status != 'aplazado':
        _1x2 = 'OK' if match['1x2']['OK'] else match['1x2']['msj'] if 'msj' in match['1x2'] else 'NO' # noqa
        _ambos = 'OK' if match['ambos']['OK'] else match['ambos']['msj'] if 'msj' in match['ambos'] else 'NO' # noqa
        _goles = 'OK' if match['goles']['OK'] else match['goles']['msj'] if 'msj' in match['goles'] else 'NO' # noqa
        _handicap = 'OK' if match['handicap']['OK'] else match['handicap']['msj'] if 'msj' in match['handicap'] else 'NO' # noqa
    return f' 1x2: {_1x2} AMBOS: {_ambos} GOLES: {_goles} HANDICAP: {_handicap}' # noqa


if __name__ == '__main__':
    # decimal = 1.615
    # print(decimal, decimal_american(decimal))
    # decimal = 1.222
    # print(decimal, decimal_american(decimal))
    # decimal = 1.25
    # print(decimal, decimal_american(decimal))
    # decimal = 1.083
    # print(decimal, decimal_american(decimal))
    # decimal = 3.85
    # print(decimal, decimal_american(decimal))
    # decimal = 3.65  # +265
    # print(decimal, decimal_american(decimal))
    # decimal = 4.5  # +350
    # print(decimal, decimal_american(decimal))
    # decimal = 6.25  # +525
    # print(decimal, decimal_american(decimal))
    # decimal = 6.5  # +550
    # print(decimal, decimal_american(decimal))
    # decimal = 1
    # print(decimal, decimal_american(decimal))
    gsheet('Ligas')
