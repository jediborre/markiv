import os
import re
import sys
import json
import telebot
import logging
from telebot import types
from dotenv import load_dotenv
from catalogos import paises, user_data
from requests.exceptions import ConnectionError, ReadTimeout
from utils import es_momio_americano
from utils import get_match_details, get_match_paises, get_paises_count

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID').split(',')

filename = 'partidos_totalcorner'
script_path = os.path.dirname(os.path.abspath(__file__))
result_path = os.path.join(script_path, 'result')
if not os.path.exists(result_path):
    os.makedirs(result_path)
log_file_path = os.path.join(script_path, "log_markiv.log")
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

preguntas_momios = [
    ['momio_home', 'Momio Resultado Local'],
    ['momio_away', 'Momio Resultado Visitante'],
    ['momio_si', 'Momio Ambos Anotaran Si'],
    ['momio_no', 'Momio Ambos Anotaran No'],
    ['momio_ht_05', 'Momio HT -0.5'],
    ['momio_ht_15', 'Momio HT -1.5'],
    ['momio_ht_25', 'Momio HT -2.5'],
    ['momio_ft_05', 'Momio HT -0.5'],
    ['momio_ft_15', 'Momio HT -1.5'],
    ['momio_ft_25', 'Momio HT -2.5'],
    ['momio_ft_35', 'Momio HT -3.5'],
    ['momio_ft_45', 'Momio HT -4.5'],
]


@bot.message_handler(func=lambda message: True)
def handle_(message):
    global db_matches, db_pais_matches, preguntas_momios
    user_id = message.chat.id
    user = user_data[user_id]
    nombre = user['nombre']
    pattern = r"^#\d{1,}$"
    msj = message.text
    if msj:
        msj_l = msj.lower()
        if msj_l == 'paises':
            if db_pais_matches:
                paises_count = get_paises_count(db_pais_matches)
                bot.reply_to(message, paises_count)
            else:
                bot.reply_to(message, f'{nombre}\nNo hay partidos, falla la Base?') # noqa

        if msj_l in paises:
            pais = msj_l
            if pais in db_pais_matches:
                matches = db_pais_matches[pais]
                str_paises = get_match_paises(matches)
                bot.reply_to(message, str_paises)
            else:
                bot.reply_to(message, f'{nombre}\nNo hay partidos en {pais}')

        if re.fullmatch(pattern, msj):
            id = str(re.sub(r'\#', '', msj))
            if id in db_matches:
                match = db_matches[id]
                user_data[user_id]['match_selected'] = id
                match_url = match['url']

                markup = types.InlineKeyboardMarkup()
                si_boton = types.InlineKeyboardButton("Sí", callback_data='si')
                no_boton = types.InlineKeyboardButton("No", callback_data='no')
                if match_url:
                    link_boton = types.InlineKeyboardButton("Partido", url=match_url) # noqa

                markup.add(si_boton, no_boton)
                if match_url:
                    markup.add(link_boton)
                str_match_detail = get_match_details(match)
                logging.info(str_match_detail + '\n\n ¿{nombre}, deseas continuar?') # noqa
                bot.reply_to(message, str_match_detail, reply_markup=markup)
                # bot.register_next_step_handler(message, obtener_momio1, 0)
            else:
                bot.reply_to(message, f'{nombre}\nPartido #{id} no encontrado.') # noqa
    else:
        bot.reply_to(message, 'Instruccion vacia')


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    global db_matches, preguntas_momios
    chat_id = call.message.chat.id
    user = user_data[chat_id]
    nombre = user['nombre']
    if call.data == 'si':
        match_selected = user['match_selected']
        match = db_matches[match_selected]
        match['intentos'] = 0
        match['pregunta_actual'] = 0
        for p in preguntas_momios:
            campo, _ = p
            match[campo] = ''
        user_data[chat_id][match_selected] = match
        preguntar_momio(call.message)
    elif call.data == 'no':
        bot.send_message(chat_id, f"{nombre}\nIngresa otro ID o pais")


def preguntar_momio(message):
    chat_id = message.chat.id
    user = user_data[chat_id]
    nombre = user['nombre']
    match_selected = user['match_selected']
    match = db_matches[match_selected]
    pregunta_actual = match['pregunta_actual']

    if pregunta_actual < len(preguntas_momios):
        campo, texto_pregunta = preguntas_momios[pregunta_actual]
        bot.send_message(chat_id, f"{nombre}\n¿{texto_pregunta}? (- Si no hay)") # noqa
        bot.register_next_step_handler(message, obtener_momio)
    else:
        bot.send_message(chat_id, f"{nombre}\n¡Has completado todas las preguntas!") # noqa
        logging.info(f'#{match_selected}')
        for m in match:
            logging.info(f'{m}: {match[m]}')


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
            bot.send_message(chat_id, f"{nombre}\nEl momio es inválido, intenta de nuevo ({intentos_restantes} intentos).") # noqa
            bot.register_next_step_handler(message, obtener_momio)
        else:
            bot.send_message(chat_id, "{nombre}\nVuelve a ingresar el id del partido para volver a empezar.") # noqa


def start_bot():
    global bot
    logging.info('Mark IV BOT')
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=10)
    except (ConnectionError, ReadTimeout):
        logging.warning("Telegram conection Timeout...")
        # sys.stdout.flush()
        # os.execv(sys.argv[0], sys.argv)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Fin...")
        bot.stop_polling()
    except Exception as e:
        logging.error("Telegram Exception")
        logging.error(str(e))
    else:
        bot.infinity_polling(timeout=20, long_polling_timeout=10)
    finally:
        try:
            bot.stop_polling()
        except Exception:
            pass


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) > 0:
        db_file = args[0]
        match_file = os.path.join(result_path, f'{db_file}.json')
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
                start_bot()
        else:
            logging.error('Archivo de base no existe, lo escribiste bien?')
    else:
        logging.error('Falta expecificar nombre de archivo')
