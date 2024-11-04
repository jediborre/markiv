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
from catalogos import paises, user_data, preguntas_momios
from requests.exceptions import ConnectionError, ReadTimeout
from sheet_utils import write_sheet_match, update_formulas_bot_row
from utils import get_momios_image
from utils import get_match_details, get_match_paises, get_paises_count

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID').split(',')

gc = pygsheets.authorize(service_file='feroslebosgc .json')
spreadsheet = gc.open('Mark 4')
wks = spreadsheet.worksheet_by_title('Bot')

matches_result_file = ''
filename = 'partidos_totalcorner'
script_path = os.path.dirname(os.path.abspath(__file__))
gemini_path = os.path.join(script_path, 'gemini_path')
if not os.path.exists(gemini_path):
    os.makedirs(gemini_path)
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
    global db_matches, preguntas_momios
    user_id = call.message.chat.id
    user = user_data[user_id]
    # nombre = user['nombre']
    match_selected = user['match_selected']
    match = db_matches[match_selected]
    match['intentos'] = 0
    match['pregunta_actual'] = 0
    for p in preguntas_momios:
        campo, _ = p
        match[campo] = ''
    if call.data == 'si':
        match['correcto'] = 'SI'
    elif call.data == 'no':
        match['correcto'] = 'NO'
    user_data[user_id][match_selected] = match
    logging.info('Esperando Momios')
    preguntar_momio(call.message)


def preguntar_momio(message):
    global matches_result_file, wks
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
            f'''{nombre}
Ingresa la imagen de los momios o captura

¿{texto_pregunta}? (- Si no hay)'''
        )
        bot.register_next_step_handler(message, obtener_momios)
    else:
        match['usuario'] = nombre
        send_text(
            bot,
            user_id,
            'Calculando...'
        )
        res = write_sheet_match(wks, match)
        ap = res['ap']
        row = res['row']
        match['ap'] = ap
        save_match(matches_result_file, match)
        markup = types.InlineKeyboardMarkup()
        if match_url:
            link_boton = types.InlineKeyboardButton('Partido', url=match_url) # noqa
            markup.add(link_boton)
        msj = get_match_details(match, True)
        bot_msj = f'{msj}\n\nApuesta: {ap}'
        logging.info(bot_msj)
        if match['correcto'] == 'SI':
            if 'OK' in ap:
                for cid in TELEGRAM_CHAT_ID:
                    send_text(
                        bot,
                        cid,
                        bot_msj,
                        markup
                    )
            else:
                send_text(
                    bot,
                    user_id,
                    bot_msj,
                    markup
                )
        else:
            send_text(
                bot,
                user_id,
                bot_msj,
                markup
            )
        update_formulas_bot_row(wks, row)


def obtener_momios(message):
    global matches_result_file
    chat_id = message.chat.id
    user = user_data[chat_id]
    nombre = user['nombre']
    match_selected = user['match_selected']
    match = db_matches[match_selected]
    match_url = match['url']
    pregunta_actual = match['pregunta_actual']
    if message.photo:
        send_text(
            bot,
            chat_id,
            'Reenvia captura sin comprimir...'
        )
    if message.document:
        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        img_filename = f'{match_selected}_{chat_id}.jpg'
        with open(f"img/{img_filename}", 'wb') as f:
            f.write(downloaded_file)
        send_text(
            bot,
            chat_id,
            'Obteniendo momios...'
        )
        momios = get_momios_image(img_filename)
        logging.info(momios)
        match = {key: momios.get(key, match.get(key)) if match.get(key) == '' else match.get(key) # noqa
                 for key in set(match) | set(momios)}
        match['usuario'] = nombre
        user_data[chat_id][match_selected] = match
        send_text(
            bot,
            chat_id,
            'Calculando Apuesta...'
        )
        res = write_sheet_match(wks, match)
        ap = res['ap']
        row = res['row']
        match['ap'] = ap
        save_match(matches_result_file, match)
        markup = types.InlineKeyboardMarkup()
        if match_url:
            link_boton = types.InlineKeyboardButton('Partido', url=match_url) # noqa
            markup.add(link_boton)
        msj = get_match_details(match, True)
        bot_msj = f'{msj}\n\nApuesta: {ap}'
        if match['correcto'] == 'SI':
            if 'OK' in ap:
                for cid in TELEGRAM_CHAT_ID:
                    send_text(
                        bot,
                        cid,
                        bot_msj,
                        markup
                    )
            else:
                send_text(
                    bot,
                    chat_id,
                    bot_msj,
                    markup
                )
        else:
            send_text(
                bot,
                chat_id,
                bot_msj,
                markup
            )
        update_formulas_bot_row(wks, row)
    else:
        momio = message.text
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
                bot.register_next_step_handler(message, obtener_momios)
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
        bot.infinity_polling(
            timeout=60,
            long_polling_timeout=100,
            logger_level=None
        )
    except (ConnectionError, ReadTimeout):
        logging.warning('Telegram conection Timeout...')
    except (KeyboardInterrupt, SystemExit):
        logging.info('Fin...')
        bot.stop_polling()
    except Exception as e:
        logging.error('Telegram Exception')
        logging.error(str(e))
    else:
        bot.infinity_polling(
            timeout=80,
            long_polling_timeout=150,
            logger_level=None
        )
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
