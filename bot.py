import os
import re
import sys
import json
import telebot
import logging
import pygsheets
from telebot import types
from dotenv import load_dotenv
from utils import es_momio_americano
from utils import send_text, save_match
from sheet_utils import write_sheet_match
from catalogos import paises, user_data, preguntas_momios
from requests.exceptions import ConnectionError, ReadTimeout
from utils import get_match_details, get_match_paises, get_paises_count

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID').split(',')

gc = pygsheets.authorize(service_file='feorslebosgc.json')
spreadsheet = gc.open('Mark 4')
wks = spreadsheet.worksheet_by_title('Bot')

matches_result_file = ''
filename = 'partidos_totalcorner'
script_path = os.path.dirname(os.path.abspath(__file__))
result_path = os.path.join(script_path, 'result')
if not os.path.exists(result_path):
    os.makedirs(result_path)
log_file_path = os.path.join(script_path, 'log_markiv.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
db_matches = {}
matches_result = []
db_pais_matches = {}

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


@bot.message_handler(func=lambda message: True)
def handle(message):
    global db_matches, db_pais_matches, preguntas_momios
    user_id = message.chat.id
    user = user_data[user_id]
    nombre = user['nombre']
    pattern = r'^#\d{1,}$'
    msj = message.text
    if msj:
        msj_l = msj.lower()
        if msj_l == 'paises':
            if db_pais_matches:
                paises_count = get_paises_count(db_pais_matches)
                send_text(
                    bot,
                    user_id,
                    paises_count
                )
            else:
                send_text(
                    bot,
                    user_id,
                    f'{nombre}\nNo hay partidos, falla la Base?'
                )

        if msj_l in paises:
            pais = msj_l
            if pais in db_pais_matches:
                matches = db_pais_matches[pais]
                str_paises = get_match_paises(matches)
                send_text(
                    bot,
                    user_id,
                    str_paises
                )
            else:
                send_text(
                    bot,
                    user_id,
                    f'{nombre}\nNo hay partidos en {pais}'
                )

        if re.fullmatch(pattern, msj):
            id = str(re.sub(r'\#', '', msj))
            if id in db_matches:
                match = db_matches[id]
                user_data[user_id]['match_selected'] = id
                match_url = match['url']

                markup = types.InlineKeyboardMarkup()
                si_boton = types.InlineKeyboardButton('Sí', callback_data='si')
                no_boton = types.InlineKeyboardButton('No', callback_data='no')
                markup.add(si_boton, no_boton)
                if match_url:
                    link_boton = types.InlineKeyboardButton('Partido', url=match_url) # noqa
                    markup.add(link_boton)

                str_match_detail = get_match_details(match)
                logging.info(str_match_detail)
                send_text(
                    bot,
                    user_id,
                    str_match_detail + f'\n\n ¿{nombre}, Los datos son correctos?', # noqa
                    markup
                )
            else:
                send_text(
                    bot,
                    user_id,
                    f'{nombre}\nPartido #{id} no encontrado.'
                )
    else:
        send_text(
            bot,
            user_id,
            'Instruccion vacia'
        )


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    global db_matches, preguntas_momios, wks
    user_id = call.message.chat.id
    user = user_data[user_id]
    nombre = user['nombre']
    if call.data == 'si':
        match_selected = user['match_selected']
        match = db_matches[match_selected]
        match['intentos'] = 0
        match['pregunta_actual'] = 0
        for p in preguntas_momios:
            campo, _ = p
            match[campo] = ''
        user_data[user_id][match_selected] = match
        write_sheet_match(wks, match)
        preguntar_momio(call.message)
    elif call.data == 'no':
        send_text(
            bot,
            user_id,
            f'{nombre}\nIngresa otro ID o pais'
        )


def preguntar_momio(message):
    user_id = message.chat.id
    user = user_data[user_id]
    nombre = user['nombre']
    match_selected = user['match_selected']
    match = db_matches[match_selected]
    match['intentos'] = 0
    match_url = match['url']
    user_data[user_id][match_selected] = match
    pregunta_actual = match['pregunta_actual']

    if pregunta_actual < len(preguntas_momios):
        _, texto_pregunta = preguntas_momios[pregunta_actual]
        send_text(
            bot,
            user_id,
            f'{nombre}\n¿{texto_pregunta}? (- Si no hay)'
        )
        bot.register_next_step_handler(message, obtener_momio)
    else:
        msj = get_match_details(match, True)
        save_match(match)
        markup = types.InlineKeyboardMarkup()
        if match_url:
            link_boton = types.InlineKeyboardButton('Partido', url=match_url) # noqa
            markup.add(link_boton)
        send_text(
            bot,
            user_id,
            f'{nombre}\n{msj}',
            markup
        )


def obtener_momio(message):
    chat_id = message.chat.id
    momio = message.text
    user = user_data[chat_id]
    nombre = user['nombre']
    match_selected = user['match_selected']
    match = db_matches[match_selected]
    pregunta_actual = match['pregunta_actual']

    if es_momio_americano(momio):
        campo = preguntas_momios[pregunta_actual][0]
        match[campo] = momio

        match['intentos'] = 0
        match['pregunta_actual'] += 1

        user_data[chat_id][match_selected] = match

        preguntar_momio(message)
    else:
        match['intentos'] += 1
        user_data[chat_id][match_selected] = match

        intentos_restantes = 3 - match['intentos']

        if intentos_restantes > 0:
            send_text(
                bot,
                chat_id,
                f'{nombre}\nEl momio es inválido, intenta de nuevo ({intentos_restantes} intentos).' # noqa
            )
            bot.register_next_step_handler(message, obtener_momio)
        else:
            send_text(
                bot,
                chat_id,
                '{nombre}\nVuelve a ingresar el id del partido para volver a empezar.' # noqa
            )


def start_bot(fecha):
    global bot
    logging.info(f'Mark IV BOT {fecha}')
    try:
        bot.infinity_polling(timeout=40, long_polling_timeout=60)
    except (ConnectionError, ReadTimeout):
        logging.warning('Telegram conection Timeout...')
    except (KeyboardInterrupt, SystemExit):
        logging.info('Fin...')
        bot.stop_polling()
    except Exception as e:
        logging.error('Telegram Exception')
        logging.error(str(e))
    else:
        bot.infinity_polling(timeout=50, long_polling_timeout=70)
    finally:
        try:
            bot.stop_polling()
        except Exception:
            pass


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) > 0:
        db_file = args[0]
        match_file = os.path.join(result_path, f'{db_file}.json')
        matches_result_file = os.path.join(result_path, f'matches_{db_file}.json') # noqa
        pais_match_file = os.path.join(result_path, f'{db_file}_pais.json')
        if os.path.exists(match_file) and os.path.exists(pais_match_file):
            execute = True
            try:
                db_matches = json.load(open(match_file))
            except Exception as e:
                execute = False
                logging.error(match_file)
                logging.error(str(e))
            try:
                db_pais_matches = json.load(open(pais_match_file))
            except Exception as e:
                execute = False
                logging.error(pais_match_file)
                logging.error(str(e))
            if execute:
                start_bot(db_file)
        else:
            logging.error('Archivo de base no existe, lo escribiste bien?')
    else:
        logging.error('Falta expecificar nombre de archivo')
