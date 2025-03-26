import os
import json
import pprint # noqa
from utils import path
from utils import gsheet
from text_unidecode import unidecode


def get_filtro_ligas():
    result = {}
    script_dir = os.path.dirname(os.path.realpath(__file__))
    filename = path(script_dir, 'ligas.tsv')
    ligas = open(filename, 'r', encoding='utf-8').read()
    for n, liga in enumerate(ligas.split("\n")):
        if n > 0:
            if '\t\t\t\t' == liga or '' == liga:
                continue
            pais, liga, liga_robot, aun_no, quitar = liga.split("\t")
            pais = pais.strip().upper()
            liga = liga.strip().lower()
            liga_robot = liga_robot.strip().lower()
            quitar = quitar.strip().lower() == 'quitar'
            if pais not in result:
                result[pais] = {}
            if liga not in result[pais]:
                result[pais][liga] = [quitar]
            if liga_robot != '':
                if liga_robot != liga:
                    result[pais][liga].append(liga_robot)
            if len(result[pais][liga]) == 1 and not quitar:
                del result[pais][liga]
    return result


def get_ligas_google_sheet():
    result = {}
    wks = gsheet('Ligas')
    ligas = wks.get_all_values(returnas='matrix')
    for n, liga in enumerate(ligas):
        if n > 0:
            if all([x == '' for x in liga]):
                continue
            pais, origen, destino, quitar = liga
            pais = pais.strip().upper()
            liga_origen = unidecode(origen.strip())
            liga_origen = liga_origen.lower()
            liga_correccion = destino.strip()
            quitar = quitar.strip().lower() == 'no'
            if pais not in result:
                result[pais] = {}
            if liga_origen not in result[pais]:
                result[pais][liga_origen] = [quitar]
            if liga_correccion != '':
                if liga_correccion != liga_origen:
                    result[pais][liga_origen].append(liga_correccion)
            if len(result[pais][liga_origen]) == 1 and not quitar:
                del result[pais][liga_origen]
    return result


if __name__ == '__main__':
    ligas = get_ligas_google_sheet()
    file = r"C:\Users\Robot\Documents\markiv\result\20250325\ok\202503251245.json" # noqa
    matches = json.loads(open(file, 'r', encoding='utf-8').read())
    for match in matches:
        pais = match['pais']
        liga = match['liga']
        liga_m = match['liga_mod']
        liga_o = unidecode(liga.lower())
        liga_ = ''
        if pais in ligas:
            if liga_o in ligas[pais]:
                if len(ligas[pais][liga_o]) > 1:
                    liga_ = ligas[pais][liga_o][1]
        print(f"{pais} '{liga}' '{liga_m}' '{liga_}'") # noqa
