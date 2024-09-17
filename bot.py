import os
import re
import sys
import json
import telebot
import logging
from telebot import types
# from model.db import Base
# from model import Match
from catalogos import paises
from dotenv import load_dotenv
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, scoped_session
from requests.exceptions import ConnectionError, ReadTimeout

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID').split(',')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
filename = 'partidos_totalcorner'
script_path = os.path.dirname(os.path.abspath(__file__))
result_path = os.path.join(script_path, 'result')
if not os.path.exists(result_path):
    os.makedirs(result_path)
db_matches = {}
db_pais_matches = {}

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


@bot.message_handler(func=lambda message: True)
def handle_(message):
    global db_matches, db_pais_matches
    pattern = r"^#\d{1,}$"
    msj = message.text
    if msj:
        msj_l = msj.lower()
        if msj_l == 'paises':
            str_msj = []
            num_juegos = 0
            pais_cuenta = []
            # print(db_pais_matches)
            for pais in db_pais_matches:
                n_juegos_pais = len(db_pais_matches[pais])
                pais_cuenta.append([pais, n_juegos_pais])
                num_juegos += n_juegos_pais
            str_msj.append(f'Juegos de hoy: {num_juegos}')
            pais_cuenta_sorted = sorted(
                pais_cuenta,
                key=lambda x: x[1],
                reverse=True
            )
            if len(pais_cuenta_sorted) > 0:
                for pais, n in pais_cuenta_sorted:
                    str_msj.append(f'{pais} [{n}]')
                bot.reply_to(message, '\n'.join(str_msj))
            else:
                bot.reply_to(message, 'No hay partidos')

        if msj_l in paises:
            pais = msj_l
            if pais in db_pais_matches:
                str_msj = []
                matches = db_pais_matches[pais]
                for match in matches:
                    str_msj.append(f'#{match["id"]} {match["time"]} {match["liga"]} {match["home"]} - {match["away"]}') # noqa
                bot.reply_to(message, '\n'.join(str_msj))
            else:
                bot.reply_to(message, f'No hay partidos en {pais}')

        if re.fullmatch(pattern, msj):
            id = str(re.sub(r'\#', '', msj))
            if id in db_matches:
                match = db_matches[id]
                match_url = match['url']
                home = match['home']
                away = match['away']
                liga = match['liga']
                pais = match['pais']
                pGol = match['promedio_gol']
                home_matches = match['home_matches']
                away_matches = match['away_matches']
                face_matches = match['face_matches']
                home_gP = home_matches['hechos']
                home_gM = home_matches['concedidos']
                home_pgP = home_matches['p_hechos']
                home_pgM = home_matches['p_concedidos']
                home_n_games = len(home_matches)
                home_games = '\n'.join(f'{m["ft"]}    {m["home_ft"]} - {m["away_ft"]}    {m["home"][:5]} - {m["away"][:5]}' for m in home_matches['matches']) # noqa
                away_gP = away_matches['hechos']
                away_gM = away_matches['concedidos']
                away_pgP = away_matches['p_hechos']
                away_pgM = away_matches['p_concedidos']
                away_n_games = len(away_matches)
                away_games = '\n'.join(f'{m["ft"]}    {m["home_ft"]} - {m["away_ft"]}    {m["home"][:5]} - {m["away"][:5]}' for m in away_matches['matches']) # noqa
                face_games = '\n'.join(f'{m["ft"]}    {m["home_ft"]} - {m["away_ft"]}    {m["home"][:5]} - {m["away"][:5]}' for m in face_matches) # noqa
                # print(f'{home} {home_gP} {home_gM}')
                # for m in home_matches['matches']:
                #     print(f'{m["ft"]}    {m["home_ft"]} - {m["away_ft"]}    {m["home"]} - {m["away"]}') # noqa
                # print('')
                # print(f'{away} {away_gP} {away_gM}')
                # for m in away_matches['matches']:
                #     print(f'{m["ft"]}    {m["home_ft"]} - {m["away_ft"]}    {m["home"]} - {m["away"]}') # noqa
                str_msj = f'''{match["fecha"]}
{pais}
{liga}
{home} v {away}

G PARTIDO: {pGol}
{home}
J: {home_n_games} +: {home_gP} -: {home_gM} P+: {home_pgP} P-: {home_pgM}
{home_games}

{away}
J: {away_n_games} +: {away_gP} -: {away_gM} P+: {away_pgP} P-: {away_pgM}
{away_games}

vs
{face_games}

¿Deseas continuar?''' # noqa

                markup = types.InlineKeyboardMarkup()
                si_boton = types.InlineKeyboardButton("Sí", callback_data='si')
                no_boton = types.InlineKeyboardButton("No", callback_data='no')
                if match_url:
                    link_boton = types.InlineKeyboardButton("Partido", url=match_url) # noqa

                markup.add(si_boton, no_boton)
                if match_url:
                    markup.add(link_boton)

                bot.reply_to(message, str_msj, reply_markup=markup)
                # bot.register_next_step_handler(message, obtener_momio1, 0)
            else:
                bot.reply_to(message, f'Partido #{id} no encontrado.')
    else:
        bot.reply_to(message, 'Instruccion vacia')


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == 'si':
        bot.send_message(call.message.chat.id, "¿Cuál es el momio?")
    elif call.data == 'no':
        bot.answer_callback_query(call.id, "Ingresa otro ID o pais")


def start_bot():
    global bot
    logging.info('Mark IV BOT')
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=10)
    except (ConnectionError, ReadTimeout):
        sys.stdout.flush()
        os.execv(sys.argv[0], sys.argv)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Fin...")
        bot.stop_polling()
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
                print(e)
                print(match_file)
            try:
                db_pais_matches = json.load(open(pais_match_file))
            except Exception as e:
                execute = False
                print(e)
                print(pais_match_file)
            if execute:
                start_bot()
        else:
            print('Archivo de base no existe, lo escribiste bien?')
    else:
        print('Falta expecificar nombre de archivo')
