import pprint # noqa
from utils import gsheet


def excel_col(col_label):
    col_num = 0
    for char in col_label:
        col_num = col_num * 26 + (ord(char) - ord('A') + 1)
    return col_num - 1


def get_rango2(rango):
    numero = float(rango)
    if -1.00 >= numero <= -0.80:
        return '-1.00 -0.80:'
    if -0.70 >= numero <= -0.50:
        return '-0.70 -0.50'
    if -0.40 >= numero <= -0.20:
        return '-0.40 -0.20'
    if -0.10 >= numero <= 0.10:
        return '-0.10 0.10'
    if 0.20 >= numero <= 0.40:
        return '0.20 0.40'
    if 0.50 >= numero <= 0.70:
        return '0.50 0.70'
    if 0.80 >= numero <= 1.00:
        return '0.80 1.00'


def gen_pais_liga():
    result = {}
    wks = gsheet('Ligas')
    ligas = wks.get_all_values(returnas='matrix')
    for n, liga in enumerate(ligas):
        if n > 0:
            if all([x == '' for x in liga]):
                continue
            pais, origen, destino, quitar = liga
            pais = pais.strip().upper()
            liga_correccion = destino.strip()
            if pais not in result:
                result[pais] = {}
            if liga_correccion not in result[pais]:
                result[pais][liga_correccion] = {}
    return result


def get_bot():
    result = []
    wks = gsheet('Bot')
    data = wks.get_all_values(returnas='matrix')
    for n, row in enumerate(data):
        if n > 1:
            if all([x == '' for x in row]):
                continue
            id = row[excel_col('A')]
            fecha = row[excel_col('B')]
            hora = row[excel_col('C')]
            home = row[excel_col('D')]
            away = row[excel_col('E')]
            pais = row[excel_col('H')]
            liga = row[excel_col('I')]
            ocho_x2 = row[excel_col('BI')]
            nueve_asiatico = row[excel_col('BJ')]
            gol_1 = row[excel_col('AK')]
            gol_2 = row[excel_col('AL')]
            gol_3 = row[excel_col('AM')]
            gol_4 = row[excel_col('AN')]
            roja_home = row[excel_col('AO')]
            roja_away = row[excel_col('AP')]
            ft = row[excel_col('AQ')]
            link = row[excel_col('CC')]
            equipo_fuerte = row[excel_col('BV')]
            rango = row[excel_col('BW')]
            result.append({
                'id': id,
                'fecha': fecha,
                'hora': hora,
                'home': home,
                'away': away,
                'pais': pais,
                'liga': liga,
                'x2': ocho_x2,
                'asiatico': nueve_asiatico,
                'gol_1': gol_1,
                'gol_2': gol_2,
                'gol_3': gol_3,
                'gol_4': gol_4,
                'roja_home': roja_home,
                'roja_away': roja_away,
                'equipo_fuerte': equipo_fuerte,
                'rango': rango,
                'ft': ft,
                'link': link
            })
    return result


def main():
    matches = get_bot()
    matriz_ligas = gen_pais_liga()
    matriz_35home, lista_35home = {}, []
    matriz_35away, lista_35away = {}, []
    for match in matches:
        x2 = match['x2']
        pais = match['pais']
        liga = match['liga']
        rango = match['rango']
        equipo = match['equipo_fuerte']
        pais_liga = f'{pais} {liga}'
        x2_rango = get_rango2(x2)
        if pais in matriz_ligas:
            if liga in matriz_ligas[pais]:
                if equipo == 'L':
                    if pais_liga not in matriz_35home:
                        matriz_35home[pais_liga] = {}
                    if rango not in matriz_35home[pais_liga]:
                        matriz_35home[pais_liga][rango] = {}
                    if x2_rango not in matriz_35home[pais_liga][rango]:
                        matriz_35home[pais_liga][rango][x2_rango] = []
                    matriz_35home[pais_liga][rango][x2_rango].append(match)
                elif equipo == 'V':
                    if pais_liga not in matriz_35away:
                        matriz_35away[pais_liga] = {}
                    if rango not in matriz_35away[pais_liga]:
                        matriz_35away[pais_liga][rango] = {}
                    if x2_rango not in matriz_35away[pais_liga][rango]:
                        matriz_35away[pais_liga][rango][x2_rango] = []
                    matriz_35away[pais_liga][rango][x2_rango].append(match)

    for pais_liga in matriz_35home:
        for rango in matriz_35home[pais_liga]:
            for x2_rango in matriz_35home[pais_liga][rango]:
                n_matches = len(matriz_35home[pais_liga][rango][x2_rango])
                lista_35home.append([pais_liga, rango, x2_rango, n_matches])

    for pais_liga in matriz_35away:
        for rango in matriz_35away[pais_liga]:
            for x2_rango in matriz_35away[pais_liga][rango]:
                n_matches = len(matriz_35away[pais_liga][rango][x2_rango])
                lista_35away.append([pais_liga, rango, x2_rango, n_matches])

    print('-3.5 Home')
    lista_35home = sorted(lista_35home, key=lambda x: x[3], reverse=True)
    for n, (pais_liga, rango, x2_rango, n_matches) in enumerate(lista_35home):
        if n < 50:
            print(pais_liga, rango, x2_rango, n_matches)

    print('-3.5 Away')
    lista_35away = sorted(lista_35away, key=lambda x: x[3], reverse=True)
    for n, (pais_liga, rango, x2_rango, n_matches) in enumerate(lista_35away):
        if n < 50:
            print(pais_liga, rango, x2_rango, n_matches)


if __name__ == '__main__':
    main()
