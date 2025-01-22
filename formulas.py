def goles_esperados(home_pgplus, away_pgminus, away_pgplus, home_pgminus):
    if "-" in (home_pgplus, away_pgminus, away_pgplus, home_pgminus):
        return "Sin Datos"
    return (home_pgplus * away_pgminus) + (away_pgplus * home_pgminus)


if __name__ == '__main__':
    print(goles_esperados(1.2, 1.2, 0.6, 0.8))
    print(goles_esperados(0.4, 1, 1.4, 0.8))
    print(goles_esperados(1.2, 1.2, 1, 1.6))
