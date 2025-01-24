def goles_esperados(home_pgplus, away_pgminus, away_pgplus, home_pgminus):
    if "-" in (home_pgplus, away_pgminus, away_pgplus, home_pgminus):
        return "Sin Datos"
    return (home_pgplus * away_pgminus) + (away_pgplus * home_pgminus)


def ocho_x2(home_pgplus, away_pgminus, away_pgplus, home_pgminus):
    if "-" in (home_pgplus, away_pgplus, home_pgminus, away_pgminus):
        return "Sin Datos"
    return ((home_pgplus - away_pgplus) + (away_pgminus - home_pgminus)) / 2


# AC -> HandiCap Asiatico 0/-0.5 LM
# AD -> HandiCap Asiatico 0/-0.5 VM
# AE -> HandiCap Asiatico -1 LM
# AF -> HandiCap Asiatico -1 VM
# AG -> HandiCap Asiatico -2 LM
# AH -> HandiCap Asiatico -2 VM

def handicap_nueve(ac, ad, ae, af, ag, ah):
    if "" in (ac, ad):
        return "-"

    def tipo_handicap(value):
        if value == '':
            return 50
        return ((value - 1.01) / 1.49) * 100 if value <= 2.5 else 50

    # Weighted calculation
    weights = {"AC": 0.7, "AE": 0.3, "AG": 0.2}
    components = {
        "AC": tipo_handicap(ac) * weights["AC"],
        "AE": tipo_handicap(ae) * weights["AE"],
        "AG": tipo_handicap(ag) * weights["AG"],
    }

    weighted_average = sum(components.values()) / sum(weights.values())

    penalties = (
        (50 if ae is None or af is None else 0) +
        (25 if ag is None or ah is None else 0)
    )

    return weighted_average + penalties


if __name__ == '__main__':
    # print(goles_esperados(1.2, 1.2, 0.6, 0.8))
    # print(goles_esperados(0.4, 1, 1.4, 0.8))
    # print(goles_esperados(1.2, 1.2, 1, 1.6))
    print(handicap_nueve(3.17, 1.27, 7.8, 1.02, '', ''))  # 55.37
