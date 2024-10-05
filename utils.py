import re
import os
import json
import base64
import pprint
import logging
import vertexai
from vertexai.generative_models import GenerativeModel, Part, SafetySetting

matches_result = []


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
        if not os.path.exists(response_filepath):
            gemini_response = get_gemini_response(img_filepath)
            with open(response_filepath, 'w', encoding='utf-8') as f:
                f.write(gemini_response)
        result = parse_gemini_response(response_filepath)
        with open(processed_filepath, 'w') as f:
            json.dump(result, f)
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
        momio_si = ambos['Y'] if 'Y' in ambos else '-'
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
    # text_response = re.sub(r'^U (\d+\.\d+)', r'UNDER \1', text_response)
    # text_response = re.sub(r'^O (\d+\.\d+)', r'OVER \1', text_response)
    return text_response


def save_match(matches_result_file, match):
    global matches_result
    matches_result.append(match)
    with open(matches_result_file, 'w') as f:
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
    home_gP = home_matches['hechos']
    home_gM = home_matches['concedidos'][0]
    home_pgP = home_matches['p_hechos']
    home_pgM = home_matches['p_concedidos']
    # home_n_games = len(home_matches)
    home_games = '\n'.join(f'{m["ft"]}    {m["home_ft"]} - {m["away_ft"]}    {m["home"][:5]} - {m["away"][:5]}' for m in home_matches['matches']) # noqa
    away_gP = away_matches['hechos']
    away_gM = away_matches['concedidos'][0]
    away_pgP = away_matches['p_hechos']
    away_pgM = away_matches['p_concedidos']
    # away_n_games = len(away_matches)
    away_games = '\n'.join(f'{m["ft"]}    {m["home_ft"]} - {m["away_ft"]}    {m["home"][:5]} - {m["away"][:5]}' for m in away_matches['matches']) # noqa
    face_games = '\n'.join(f'{m["ft"]}    {m["home_ft"]} - {m["away_ft"]}    {m["home"][:5]} - {m["away"][:5]}' for m in face_matches['matches']) # noqa
    result = f'''
#{id} {fecha}
{pais}{liga}
{home} v {away}

G PARTIDO: {pGol}
{home}
+: {home_gP} -: {home_gM} P+: {home_pgP} P-: {home_pgM}
{home_games}

{away}
+: {away_gP} -: {away_gM} P+: {away_pgP} P-: {away_pgM}
{away_games}

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
Gol FT: {momio_ft_05} {momio_ft_15} {momio_ft_25} {momio_ft_35} {momio_ft_45}''' # noqa
    return result


if __name__ == '__main__':
    momios = get_momios_image('momios_1.jpg')
    pprint.pprint(momios)
    momios = get_momios_image('momios_2.jpg')
    pprint.pprint(momios)
    momios = get_momios_image('momios_3.jpg')
    pprint.pprint(momios)
    momios = get_momios_image('momios_4.jpg')
    pprint.pprint(momios)
