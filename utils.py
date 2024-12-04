import re
import os
import json
import base64
import pprint
import logging
import vertexai
if os.name == 'nt':
    import win32com.client
from datetime import datetime
from vertexai.generative_models import GenerativeModel, Part, SafetySetting
from text_unidecode import unidecode

matches_result = []


def wakeup(match_id: int, date_ht: str):
    try:
        if os.name == 'nt':
            WD = os.getcwd()
            trigger_time = datetime.strptime(date_ht, '%Y-%m-%d %H:%M:%S')
            match_id = str(match_id)
            script_path = os.path.join(WD, 'match_performance.py')
            python_path = os.path.join(WD, '.venv', 'Scripts', 'python.exe')
            if not os.path.exists(python_path):
                logging.error(f"Python executable not found at {python_path}")
                return
            if not os.path.exists(script_path):
                logging.error(f"Script not found at {script_path}")
                return
            logging.info(f"Scheduling task to run script at {script_path} with Python at {python_path}") # noqa

            create_task(
                f'MATCH_{match_id}',
                python_path,
                script_path,
                match_id,
                trigger_time
            )
    except Exception as e:
        logging.exception(f"Exception occurred in wakeup function: {e}")


def create_task(task_name, python_path, script_path, args, trigger_time):
    try:
        if os.name == 'nt':
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

            taskDef.RegistrationInfo.Description = f"Wakeup Match {args}"
            taskDef.Principal.UserId = "SYSTEM"
            taskDef.Principal.LogonType = 3

            rootFolder.RegisterTaskDefinition(
                task_name,
                taskDef,
                6,  # TASK_CREATE_OR_UPDATE
                None,  # No user
                None,  # No password
                3,  # TASK_LOGON_SERVICE_ACCOUNT
                None
            )

            logging.info(f"Task '{task_name}' has been created successfully and will run at {trigger_time}") # noqa
        else:
            logging.error("Unsupported operating system")

    except Exception as e:
        logging.exception(f"Exception occurred while creating the task: {e}")


def limpia_nombre(nombre, post=True):
    nombre = re.sub(r'\s+', ' ', re.sub(r'\.|\/|\(|\)', '', nombre)).strip()
    nombre = unidecode(nombre)
    return nombre


def prepare():
    script_path = os.path.dirname(os.path.abspath(__file__))
    path_tmp = os.path.join(script_path, 'tmp')
    log_filepath = os.path.join(script_path, 'web_markiv.log')
    path_result = os.path.join(script_path, 'result', 'matches')
    path_csv = os.path.join(path_tmp, 'csv')
    path_html = os.path.join(path_tmp, 'html')
    path_json = os.path.join(path_tmp, 'json')
    if not os.path.exists(path_result):
        os.makedirs(path_result)
    if not os.path.exists(path_tmp):
        os.makedirs(path_tmp)
    if not os.path.exists(path_csv):
        os.makedirs(path_csv)
    if not os.path.exists(path_html):
        os.makedirs(path_html)
    if not os.path.exists(path_json):
        os.makedirs(path_json)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filepath),
            logging.StreamHandler()
        ]
    )
    return [
        path_result,
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


def get_momios_image(img_filename):
    img_filepath = os.path.join('img', img_filename)
    if os.path.exists(img_filepath):
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


def save_matches(filename, matches, overwrite=False):
    if overwrite:
        os.remove(filename)

    if not os.path.exists(filename) or overwrite:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(matches, f, indent=4)


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


if __name__ == '__main__':
    for n in range(6):
        momios = get_momios_image(f'momios_{n}.jpg')
        pprint.pprint(momios)
