from web import Web
from utils import gsheet
from parse import get_marcador_ft
from parse import status_partido


def main():
    wks = gsheet('Bot')
    web = Web(multiples=True)
    bot_regs = wks.get_all_values(returnas='matrix')
    for row, value in enumerate(bot_regs):
        r = row + 1
        id = value[0]
        home = value[3]
        away = value[4]
        hora = value[2]
        pais = value[7]
        liga = value[8]
        ft = value[42]
        link = f'https://www.flashscore.com.mx/partido/{id}/#/resumen-del-partido' # noqa
        if id != '' and ft == '':
            web.open(link)
            web.wait(1)
            status = status_partido(web)
            finalizado = False
            if status == 'finalizado':
                finalizado = True
            elif status == 'aplazado':
                print(r, id, pais, liga, hora, home, away, 'Aplazado', '-', '-') # noqa
                wks.update_value(f'AK{r}', '-')
                wks.update_value(f'AL{r}', '-')
                wks.update_value(f'AM{r}', '-')
                wks.update_value(f'AN{r}', '-')
                wks.update_value(f'AQ{r}', '-')
            else:
                print(r, id, pais, liga, hora, home, away, 'En Juego', '-', '-') # noqa
            if finalizado:
                marcador = get_marcador_ft(web)
                total_goles = marcador['ft']
                sheet = marcador['sheet']
                gol1, gol2, gol3, gol4, rojahome, rojas_away = sheet
                wks.update_value(f'AK{r}', gol1)
                wks.update_value(f'AL{r}', gol2)
                wks.update_value(f'AM{r}', gol3)
                wks.update_value(f'AN{r}', gol4)
                wks.update_value(f'AO{r}', rojahome)
                wks.update_value(f'AP{r}', rojas_away)
                wks.update_value(f'AQ{r}', total_goles)
                print(r, id, pais, liga, hora, home, away, 'Finalizado', gol1, gol2, gol3, gol4, total_goles) # noqa


if __name__ == '__main__':
    main()
