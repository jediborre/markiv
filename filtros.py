
def get_filtro_ligas():
    result = {}
    ligas = open('ligas.tsv', 'r', encoding='utf-8').read()
    for n, liga in enumerate(ligas.split("\n")):
        if n > 0:
            if '\t\t\t\t' == liga or '' == liga:
                continue
            pais, liga, liga_robot, aun_no, quitar = liga.split("\t")
            pais = pais.strip().lower()
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


if __name__ == '__main__':
    ligas = get_filtro_ligas()
    print(ligas)
