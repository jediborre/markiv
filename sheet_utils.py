def get_last_row(worksheet, col="A"):
    cells = worksheet.get_col(1, include_tailing_empty=False)
    return len(cells) + 1


def write_sheet_match(wks, match):
    last_row = get_last_row(wks)
    url = match['url']
    fecha = match['fecha']
    hora = match['time']
    pais = match['pais']
    liga = match['liga']
    home = match['home']
    away = match['away']
    promedio_gol = match['promedio_gol']
    home_matches = match['home_matches']['matches']
    home_ft_1 = home_matches[0]['ft']
    home_ft_2 = home_matches[1]['ft']
    home_ft_3 = home_matches[2]['ft']
    home_ft_4 = home_matches[3]['ft']
    home_ft_5 = home_matches[4]['ft']
    home_hechos = match['home_matches']['hechos']
    home_concedidos = match['home_matches']['concedidos']
    home_p_hechos = match['home_matches']['p_hechos']
    home_p_concedidos = match['home_matches']['p_concedidos']
    away_matches = match['away_matches']['matches']
    away_ft_1 = away_matches[0]['ft']
    away_ft_2 = away_matches[1]['ft']
    away_ft_3 = away_matches[2]['ft']
    away_ft_4 = away_matches[3]['ft']
    away_ft_5 = away_matches[4]['ft']
    away_hechos = match['away_matches']['hechos']
    away_concedidos = match['away_matches']['concedidos']
    away_p_hechos = match['away_matches']['p_hechos']
    away_p_concedidos = match['away_matches']['p_concedidos']
    wks.update_row(last_row, [
        fecha,
        hora,
        home,
        away,
        '',
        '',
        pais,
        liga,
        home_ft_1,
        home_ft_2,
        home_ft_3,
        home_ft_4,
        home_ft_5,
        home_hechos,
        home_concedidos,
        '5',
        home_p_hechos,
        home_p_concedidos,
        away_ft_1,
        away_ft_2,
        away_ft_3,
        away_ft_4,
        away_ft_5,
        away_hechos,
        away_concedidos,
        '5',
        away_p_hechos,
        away_p_concedidos,
    ])
