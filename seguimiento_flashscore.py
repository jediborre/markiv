import re
import os
import sys
import time
import telebot
import logging
import argparse
from web import Web
from utils import gsheet
from utils import send_text
from utils import busca_id_bot
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from utils import get_json_list
from utils import path, pathexist
from utils import prepare_paths_ok

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID').split(',')

# https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json

url_matches_today = 'https://m.flashscore.com.mx/'

sys.stdout.reconfigure(encoding='utf-8')

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID').split(',')

path_result, path_ok = prepare_paths_ok()

parser = argparse.ArgumentParser(description="Solicita partidos de hoy o mañana de flashscore") # noqa
parser.add_argument('file', type=str, help='Archivo de Partidos Flashscore')
args = parser.parse_args()


def get_current_scores(web: Web):
    web.open(url_matches_today)
    web.wait_ID('main', 5)
    html = web.source()
    matches = {}
    filter_ligas = [
        'amistoso',
        'amistosos',
        'cup',
        'copa',
        'femenino',
        'femenina',
        'mundial',
        'playoffs',
        'internacional',
        'women',
    ]
    domain = 'https://www.flashscore.com.mx'
    soup = BeautifulSoup(html, 'html.parser')
    ligas = soup.find_all('h4')
    for liga in ligas:
        tmp_liga = ''.join([str(content) for content in liga.contents if not content.name]) # noqa
        pais, nombre_liga = tmp_liga.split(': ')
        nombre_liga = re.sub(r'\s+$', '', nombre_liga)
        partido_actual = liga.find_next_sibling()

        if any([x in nombre_liga.lower() for x in filter_ligas]):
            continue

        while partido_actual and partido_actual.name != 'h4':
            if partido_actual.name == 'span':
                hora = partido_actual.get_text(strip=True)
                aplazado = 'Aplazado' in hora
                hora = hora[:5]
                equipos = partido_actual.find_next_sibling(string=True).strip() # noqa
                try:
                    home, away = equipos.split(' - ')
                    score = partido_actual.find_next_sibling('a').get_text(strip=True) # noqa
                    link = partido_actual.find_next_sibling('a')['href']
                    link = f'{domain}{link}#/h2h/overall'
                    if not aplazado:
                        if nombre_liga not in matches:
                            matches[nombre_liga] = []
                        matches[nombre_liga].append({
                            'hora': hora,
                            'home': home,
                            'away': away,
                            'score': score,
                            'url': link,
                        })
                except ValueError:
                    pass
            partido_actual = partido_actual.find_next_sibling()
    return matches


def seguimiento(path_file: str, filename: str, web, bot, botregs, resultados=None): # noqa
    if resultados is None:
        resultados = {}

    matches = get_json_list(path_file)
    _matches = get_current_scores(web)

    try:
        algun_partido_activo = False

    # 1. Actualizar estado de los partidos existentes en 'resultados'
    ids_actualizados_o_nuevos = set()
    for id_partido, datos_partido in list(resultados.items()): # Iterar sobre copia para poder borrar
        # Si el partido ya terminó en una iteración anterior, no hacer nada
        if datos_partido.get('termino', False):
            print(f"Info: Partido {datos_partido['home']} vs {datos_partido['away']} ({id_partido}) ya terminó.")
            ids_actualizados_o_nuevos.add(id_partido)
            continue

        # Buscar datos actuales para este partido
        liga = datos_partido['liga']
        home = datos_partido['home']
        away = datos_partido['away']
        record_actual = None
        if liga in _matches:
            record_actual = next((match for match in _matches[liga] if match['home'] == home and match['away'] == away), None)

        if record_actual:
            ids_actualizados_o_nuevos.add(id_partido)
            minuto_actual_str = record_actual['hora']
            score_actual_str = record_actual['score']

            # --- Lógica de Detección de Goles ---
            goles_local_actual = -1 # Valor inválido inicial
            goles_visitante_actual = -1

            try:
                if ':' in score_actual_str:
                    parts = score_actual_str.split(':')
                    goles_local_actual = int(parts[0])
                    goles_visitante_actual = int(parts[1])
            except (ValueError, TypeError, IndexError):
                print(f"Alerta: Formato de marcador inesperado '{score_actual_str}' para {home} vs {away}. No se detectarán goles en este ciclo.")
                # Mantener los goles anteriores o resetear? Mejor mantener para evitar falsos positivos
                goles_local_actual = datos_partido.get('goles_local_anterior', 0)
                goles_visitante_actual = datos_partido.get('goles_visitante_anterior', 0)


            # Obtener goles anteriores del último registro guardado
            goles_local_anterior = datos_partido.get('goles_local_anterior', 0)
            goles_visitante_anterior = datos_partido.get('goles_visitante_anterior', 0)

            # Detectar GOL LOCAL
            if goles_local_actual > goles_local_anterior:
                print(f"¡GOL! Minuto {minuto_actual_str} - {datos_partido['pais']} {datos_partido['hora']} - {home} ({goles_local_actual}) vs {away} ({goles_visitante_actual}) - LOCAL")

            # Detectar GOL VISITANTE
            if goles_visitante_actual > goles_visitante_anterior:
                 print(f"¡GOL! Minuto {minuto_actual_str} - {datos_partido['pais']} {datos_partido['hora']} - {home} ({goles_local_actual}) vs {away} ({goles_visitante_actual}) - VISITANTE")

            # --- Fin Lógica de Detección de Goles ---

            # Actualizar estado en resultados
            datos_partido['minuto'] = minuto_actual_str
            # Guardar los goles actuales para la próxima comparación
            datos_partido['goles_local_anterior'] = goles_local_actual
            datos_partido['goles_visitante_anterior'] = goles_visitante_actual

            # Añadir al historial (seguimiento)
            # Evitar duplicados si el minuto y marcador no cambian
            ultimo_seguimiento = datos_partido['seguimiento'][-1] if datos_partido['seguimiento'] else None
            if not ultimo_seguimiento or ultimo_seguimiento[0] != minuto_actual_str or ultimo_seguimiento[1] != score_actual_str:
                 datos_partido['seguimiento'].append([minuto_actual_str, score_actual_str])
                 print(f"Update: {datos_partido['pais']} {datos_partido['hora']} {home} vs {away} -> Min: {minuto_actual_str}, Score: {score_actual_str}")

            if not minuto_actual_str or any(t in minuto_actual_str for t in ['FT', 'Fin', 'Terminado', 'Aplazado', ':']):
                 datos_partido['termino'] = True
                 print(f"Info: Partido {home} vs {away} ({id_partido}) marcado como terminado/finalizado.")
            else:
                 datos_partido['termino'] = False
                 algun_partido_activo = True # Si no ha terminado, marcamos que algo sigue activo

        else:
            print(f"Alerta: No se encontraron datos actuales para {home} vs {away} ({id_partido}). Estado no actualizado.")
            if not datos_partido.get('termino', False):
                 algun_partido_activo = True

        for m in matches:
            id_partido = m["id"]
            if id_partido in ids_actualizados_o_nuevos: # Ya procesado o añadido
                continue

            row = busca_id_bot(bot_regs, id_partido)
            if row:
                bot_reg = bot_regs[row - 1]
                if not bot_reg: continue # Registro vacío o inválido

                apuesta = bot_reg[6]
                if 'OK' in apuesta:
                    # Es un partido nuevo a seguir
                    print(f"Info: Iniciando seguimiento para {m['home']} vs {m['away']} ({id_partido})")
                    ids_actualizados_o_nuevos.add(id_partido)
                    resultados[id_partido] = {
                        'liga': m["liga"],
                        'home': m["home"],
                        'away': m["away"],
                        'hora': m["hora"],
                        'pais': m["pais"],
                        'apuesta': apuesta,
                        'termino': False, # Inicia como no terminado
                        'minuto': None,   # Minuto inicial desconocido
                        'seguimiento': [], # Historial de [minuto, score]
                        'goles_local_anterior': 0, # Goles iniciales para comparación
                        'goles_visitante_anterior': 0
                    }
                    algun_partido_activo = True # Un nuevo partido siempre está activo inicialmente

                    # Intentar obtener datos iniciales si están disponibles ya
                    liga = m["liga"]
                    home = m["home"]
                    away = m["away"]
                    record_inicial = None
                    if liga in _matches:
                        record_inicial = next((match for match in _matches[liga] if match['home'] == home and match['away'] == away), None)

                    if record_inicial:
                        minuto_inicial_str = record_inicial['hora']
                        score_inicial_str = record_inicial['score']
                        resultados[id_partido]['minuto'] = minuto_inicial_str
                        resultados[id_partido]['seguimiento'].append([minuto_inicial_str, score_inicial_str])
                        print(f"Update inicial: {m['pais']} {m['hora']} {home} vs {away} -> Min: {minuto_inicial_str}, Score: {score_inicial_str}")
                        try:
                            if ':' in score_inicial_str:
                                parts = score_inicial_str.split(':')
                                resultados[id_partido]['goles_local_anterior'] = int(parts[0])
                                resultados[id_partido]['goles_visitante_anterior'] = int(parts[1])
                        except (ValueError, TypeError, IndexError):
                            print(f"Alerta: Formato de marcador inicial inesperado '{score_inicial_str}' para {home} vs {away}.")
                            # Se quedan en 0 si falla la conversión inicial

        # 3. Decidir si continuar el seguimiento
        if algun_partido_activo:
            print(f"\n--- Ciclo completado. Esperando {40} segundos para la próxima actualización... ---")
            time.sleep(40)
            # Llamada recursiva pasando el diccionario 'resultados' actualizado
            seguimiento(path_file, filename, web, bot, bot_regs, resultados)
        else:
            print("\n--- Todos los partidos seguidos han terminado. ---")
            # Opcional: Guardar los resultados finales si es necesario
            # with open('resultados_finales.json', 'w', encoding='utf-8') as f:
            #     json.dump(resultados, f, ensure_ascii=False, indent=4)
            return resultados

    except KeyboardInterrupt:
        print('\nFin...')
    # web.close()


if __name__ == '__main__':
    args = parser.parse_args()
    filename = args.file
    path_file = path(path_result, filename.split('.')[0][:8], filename)

    if pathexist(path_file):
        logging.info(f'Seguimiento MarkIV {filename}')
        web = Web(multiples=True)
        wks = gsheet('Bot')
        bot_regs = wks.get_all_values(returnas='matrix')
        bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
        seguimiento(path_file, filename, web, bot, bot_regs)
