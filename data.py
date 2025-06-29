import re
import os
import json
from utils import cls
from utils import gsheet


def parse_apuesta(texto):
    """
    Parsea una cadena de resultado de apuesta en un diccionario.
    Ejemplos de entrada:
    "38 - 3 - 92.68% = -3.5 goles (Escenario: Escenario Moderado)"
    "0 - 6 - 100.00% = 1.5 goles (Escenario: Escenario Conservador)"

    Returns:
        dict: Diccionario con los datos parseados
    """
    patron = (r'(\d+)\s*-\s*(\d+)\s*-\s*([\d.]+)%\s*=\s*'
              r'([-+]?[\d.]+)\s*goles\s*\(Escenario:\s*(.+?)\)')

    match = re.match(patron, texto.strip())

    if not match:
        raise ValueError(f"No se pudo parsear el texto: {texto}")

    wins, losses, efectividad, apuesta, escenario = match.groups()

    # Extraer el tipo de escenario (después de "Escenario ")
    escenario_limpio = escenario.strip()
    if escenario_limpio.startswith("Escenario "):
        escenario_tipo = escenario_limpio[10:].strip()  # Remover "Escenario "
    else:
        escenario_tipo = escenario_limpio

    return {
        'wins': int(wins),
        'losses': int(losses),
        'efectividad': float(efectividad),
        'apuesta': float(apuesta),
        'escenario': escenario_tipo
    }


def get_data():
    print("Fetching Viernes from Google Sheets...")
    wks = gsheet('Bot')
    if not wks:
        raise ValueError("Worksheet 'Bot' not found.")
    data = wks.get_all_values(returnas='matrix')
    result = []
    for row in data[3:]:
        if all([x == '' for x in row]):
            continue
        result.append(row)

    return result


def ganador(apuesta, total):
    total = int(total)
    if apuesta == '-3.5':
        return 'GANA' if total < 4 else 'PIERDE'
    elif apuesta == '1.5':
        return 'GANA' if total > 1 else 'PIERDE'
    return 'Ni idea'


def procesar(data):
    n = 0
    result = []
    ganados = 0
    perdidos = 0
    print("Procesando datos...")
    if data:
        for row in data:
            id = row[0]
            pais = row[7]
            hora = row[2]
            liga = row[8]
            local = row[3]
            fecha = row[1]
            total = row[42]
            visitante = row[4]
            apuesta = row[5]
            if apuesta in ['NO apostar', '']:
                continue
            n += 1
            apuesta_corta = '-3.5' if '-3.5' in apuesta else '1.5' if '1.5' in apuesta else apuesta # noqa
            gana = ganador(apuesta_corta, total)
            if gana == 'GANA':
                ganados += 1
            elif gana == 'PIERDE':
                perdidos += 1
            else:
                print(f"Unknown result for {apuesta_corta} with total {total}")
            apuesta_ = parse_apuesta(apuesta)
            rec = {
                'id': id,
                'fecha': fecha,
                'hora': hora,
                'local': local,
                'visitante': visitante,
                'prediccion': apuesta,
                'apuesta': apuesta_corta,
                'pais': pais,
                'liga': liga,
                'total': total,
                'gana': gana,
                'escenario': apuesta_['escenario'] if 'escenario' in apuesta_ else '', # noqa
                'efectividad': apuesta_['efectividad'] if 'efectividad' in apuesta_ else 0.0 # noqa,
            }
            result.append(rec)
    else:
        print("No hay datos de Sheet para procesar.")
    return result


def muestra(data):
    if not data:
        print("No hay datos para mostrar.")
        return
    juegos = len(data)
    ganados = 0
    jugables = 0
    perdidos = 0
    descartados = 0
    escenarios = {}
    for n, row in enumerate(data):
        if row['efectividad'] > 90:
            print(
                f"{row['id']} | {row['fecha']} {row['hora']} | "
                f"{row['pais']} {row['liga']} | "
                f"{row['local']} vs {row['visitante']} | "
                f"FT: {row['total']} → {row['apuesta']} → {row['gana']} | "
                f"Escenario: {row['escenario']} | "
                f"Efectividad: {row['efectividad']:.2f}%"
            )
            if row['escenario'] not in escenarios:
                escenarios[row['escenario']] = {
                    '-3.5': {
                        'ganados': 0,
                        'perdidos': 0
                    },
                    '1.5': {
                        'ganados': 0,
                        'perdidos': 0
                    }
                }
            jugables += 1
            if row['gana'] == 'GANA':
                ganados += 1
                escenarios[row['escenario']][row['apuesta']]['ganados'] += 1
            elif row['gana'] == 'PIERDE':
                perdidos += 1
                escenarios[row['escenario']][row['apuesta']]['perdidos'] += 1
        else:
            descartados += 1
    print(f"Jugables: {jugables} - {juegos} ({jugables / juegos * 100:.2f}%)")
    print(f"Descartados: {descartados} - {juegos} ({descartados / juegos * 100:.2f}%)")
    print(f"Ganados: {ganados} - {jugables} ({ganados / jugables * 100:.2f}%)")
    print(f"Perdidos: {perdidos} - {jugables} ({perdidos / jugables * 100:.2f}%)")
    for escenario, stats in escenarios.items():
        print(f"Escenario: {escenario}")
        for apuesta, resultados in stats.items():
            print(f"  Apuesta {apuesta}: Ganados: {resultados['ganados']}, "
                  f"Perdidos: {resultados['perdidos']}, "
                  f"Total: {resultados['ganados'] + resultados['perdidos']}")


def main():
    filename = 'tmp/resultados.json'
    cls()
    if not os.path.exists(filename):
        data = get_data()
        print(f"Datos obtenidos: {len(data)} filas.")
        ndata = procesar(data)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(ndata, f, ensure_ascii=False, indent=4)
    else:
        with open(filename, 'r', encoding='utf-8') as f:
            ndata = json.load(f)
    muestra(ndata)


if __name__ == "__main__":
    main()
