import json
import base64
import vertexai
from vertexai.generative_models import GenerativeModel, Part, SafetySetting

matches_result = []


def generate(image_filename):
    generation_config = {
        "max_output_tokens": 1500,
        "temperature": 1,
        "top_p": 0.95,
    }

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

    vertexai.init(project="gen-lang-client-0049656829", location="us-west4")
    model = GenerativeModel("gemini-1.5-flash-002")
    image_part = Part.from_data(
        mime_type="image/jpeg",
        data=base64.b64decode(image_data),
    )
    responses = model.generate_content(
        [image_part, """Momios en JSON"""],
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,
    )
    for response in responses:
        print(response.text, end="")
        return response.text


def save_match(matches_result_file, match):
    global matches_result
    matches_result.append(match)
    with open(matches_result_file, 'w') as file:
        json.dump(matches_result, file, indent=4)


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


def get_f1(val):
    ranges = [
        ((-32.04, -19.19), 1),
        ((-19.08, -11.22), 3),
        ((-10.07, 28.41), 2)
    ]
    if val in ['', '-']:
        return 'Sin clasificación'

    for (start, end), classification in ranges:
        if start >= val <= end:
            return classification

    return 'Sin clasificación'


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
