import os
import pytz
import telebot
import logging
import argparse
import traceback
from utils import path
from utils import gsheet
from telebot import types
from utils import wakeup
from utils import send_text
from utils import save_matches
from utils import get_match_ok
from utils import busca_id_bot
from dotenv import load_dotenv
from utils import get_json_list
from utils import prepare_paths
from pulpo import predict_pulpo
from datetime import datetime, timedelta

load_dotenv()

path_result, path_cron, path_csv, path_json, path_html = prepare_paths('envio_telegram.log') # noqa

parser = argparse.ArgumentParser(description="Envia Partidos Telegram, Sheets")
parser.add_argument('file', type=str, help='Archivo de Partidos Flashscore')
parser.add_argument('--cron', action='store_true', help="Programar")

cron = True
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID').split(',')


def process_match(bot_regs, bot, match):
    id = match['id']
    link = match['url']
    row = busca_id_bot(bot_regs, id)
    if row:
        bot_reg = bot_regs[row - 1]
        if not bot_reg:
            return
        resultado_pulpo_ = ""
        prediccion_pulpo = predict_pulpo(bot_reg)
        if prediccion_pulpo != "ERROR":
            resultado_pulpo, history_pred, odds_pred, prob_de_ganar = prediccion_pulpo
            match['apostar'] = True
            match['pulpo'] = prob_de_ganar
            match['pulpo_odds'] = odds_pred
            match['pulpo_history'] = history_pred
            resultado_pulpo_ = f"{resultado_pulpo} H:{history_pred:.5f} O:{odds_pred:.5f} P:{prob_de_ganar:.4f}" # noqa
        home = bot_reg[3]
        away = bot_reg[4]
        apuesta = bot_reg[6]
        # resultado = bot_reg[5]
        apostar = 'APOSTAR' == resultado_pulpo
        msj = get_match_ok(match, apuesta, resultado_pulpo_)
        logging.info(f'{id} -> {msj}')
        markup = types.InlineKeyboardMarkup()
        if link:
            link_boton = types.InlineKeyboardButton('Partido', url=link) # noqa
            markup.add(link_boton)
        for chat_id in TELEGRAM_CHAT_ID:
            send_text(
                bot,
                chat_id,
                msj,
                markup
            )
        if apostar:
            match['apostar'] = True
            match['viernes'] = apuesta
            pass
        else:
            logging.info(f'{id} -> {home} - {away}, NO {apuesta}') # noqa
        return match
    else:
        logging.info(f'{id} No encontrado')
        return


def telegram_ok_matches(matches):
    try:
        print(f'Telegram Matches [{len(matches)}]')

        wks = gsheet('Bot')
        bot_regs = wks.get_all_values(returnas='matrix')
        bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

        hora = ''
        fecha = ''
        _matches = []
        for match in matches:
            hora = match['hora'] if 'hora' in match else hora
            fecha = match['fecha'] if 'fecha' in match else fecha
            _match = process_match(bot_regs, bot, match)
            if _match['apostar']:
                _matches.append(_match)

        if len(_matches) > 0:
            cinco_minutos = timedelta(minutes=5)
            zona_horaria = pytz.timezone('America/Mexico_City')
            dt_partido = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
            dt_partido = zona_horaria.localize(dt_partido)
            dt_partido_m5m = dt_partido - cinco_minutos
            filename_date = dt_partido.strftime('%Y%m%d')
            filename_datetime = dt_partido.strftime('%Y%m%d%H%M')
            filename_cron = f'{filename_datetime}.json'
            fecha_seguimiento = dt_partido_m5m.strftime('%Y-%m-%d %H:%M:%S') # noqa

            path_result_date_seguimiento = path(path_result, filename_date, 'seguimiento') # noqa
            if not os.path.exists(path_result_date_seguimiento):
                os.makedirs(path_result_date_seguimiento)
            path_seguimiento_matches = path(path_result_date_seguimiento, filename_cron) # noqa

            save_matches(path_seguimiento_matches, _matches, True)

            print(f'Seguimiento {fecha_seguimiento} [{len(_matches)}]') # noqa
            wakeup(
                'SEG',
                'seguimiento_flashscore.py',
                dt_partido_m5m,
                filename_cron,
                len(_matches)
            )

    except Exception as e:
        logging.error(f'Error: {e}')
        traceback.print_exc()
    except KeyboardInterrupt:
        print('\nFin...')


if __name__ == '__main__':
    args = parser.parse_args()
    filename = args.file
    date = filename.split('.')[0][:8]

    # result\20250325\ok\202503251245.json
    path_file = path(path_result, date, 'ok', filename)

    if not os.path.exists(path_file):
        logging.info(f'Archivo {path_file} no existe')
        exit(1)

    matches = get_json_list(path_file)
    telegram_ok_matches(matches, filename)
