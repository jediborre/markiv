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
    face_matches = match['face_matches']
    face_ft_1, face_ft_2, face_ft_3, face_ft_4, face_ft_5 = (
        (face_matches[n]['ft'] if n < len(face_matches) else '') for n in range(5) # noqa
    )
    momio_home = int(match['momio_home']) if 'momio_home' in match else ''
    momio_away = int(match['momio_away']) if 'momio_away' in match else ''
    dif_momio_win = momio_home - momio_away
    momio_si = int(match['momio_si']) if 'momio_si' in match else ''
    momio_no = int(match['momio_no']) if 'momio_no' in match else ''
    dif_momio_sino = momio_si - momio_no
    momio_ht_05 = int(match['momio_ht_05']) if 'momio_ht_05' in match else ''
    momio_ht_15 = int(match['momio_ht_15']) if 'momio_ht_15' in match else ''
    momio_ht_25 = int(match['momio_ht_25']) if 'momio_ht_25' in match else ''
    momio_ft_05 = int(match['momio_ft_05']) if 'momio_ft_05' in match else ''
    momio_ft_15 = int(match['momio_ft_15']) if 'momio_ft_15' in match else ''
    momio_ft_25 = int(match['momio_ft_25']) if 'momio_ft_25' in match else ''
    momio_ft_35 = int(match['momio_ft_35']) if 'momio_ft_35' in match else ''
    momio_ft_45 = int(match['momio_ft_45']) if 'momio_ft_45' in match else ''
    reg = [
        fecha[:10],
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
        face_ft_1,
        face_ft_2,
        face_ft_3,
        face_ft_4,
        face_ft_5,
        momio_home,
        momio_away,
        dif_momio_win,
        momio_si,
        momio_no,
        dif_momio_sino,
        momio_ht_05,
        momio_ht_15,
        momio_ht_25,
        momio_ft_05,
        momio_ft_15,
        momio_ft_25,
        momio_ft_35,
        momio_ft_45,
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        promedio_gol
    ]
    wks.update_row(last_row, reg)
