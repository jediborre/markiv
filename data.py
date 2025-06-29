from utils import cls
from utils import gsheet


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


def main():
    cls()
    n = 0
    ganados = 0
    perdidos = 0
    data = get_data()

    for row in data:
        id = row[0]
        fecha = row[1]
        hora = row[2]
        local = row[3]
        visitante = row[4]
        apuesta = row[6]
        pais = row[7]
        liga = row[8]
        total = row[42]
        if not apuesta or apuesta in ['NO apostar', '']:
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
        print(
            n,
            id,
            f"{fecha} {hora}",
            f"{pais} {liga}",
            f"{local} vs {visitante}",
            f"FT: {total} →",
            apuesta_corta, "←",
            gana
        )
    print(f"\nTotal: {n} | Ganados: {ganados} | Perdidos: {perdidos} | Efectividad: {ganados / n:.2f}%") # noqa


if __name__ == "__main__":
    main()
