import re
import pprint # noqa
# from utils import get_f1


def get_hum_fecha(fecha):
    mes = {
        '01': 'Ene',
        '02': 'Feb',
        '03': 'Mar',
        '04': 'Abr',
        '05': 'May',
        '06': 'Jun',
        '07': 'Jul',
        '08': 'Ago',
        '09': 'Sep',
        '10': 'Oct',
        '11': 'Nov',
        '12': 'Dic',
    }
    if fecha:
        y, m, d = fecha.split('-')
        return f'{mes[m]} {d} {y}'
    else:
        return fecha


def get_last_row(worksheet, col="A"):
    cells = worksheet.get_col(1, include_tailing_empty=False)
    return len(cells) + 1


def update_formula(wks, cell, target_row, source_row=3):
    source_cell = f'{cell}{source_row}'
    target_cell = f'{cell}{target_row}'
    formula = wks.cell(source_cell).formula
    pattern = r'([A-Z]+)(\d+)'
    updated_formula = re.sub(pattern, lambda match: f"{match.group(1)}{int(match.group(2)) - source_row + target_row}", formula)  # noqa
    wks.update_value(target_cell, updated_formula)
    return wks.cell(target_cell).value


def write_sheet_flashcore(wks, match):
    pass


def write_sheet_match(wks, match):
    url = match['url']
    fecha = get_hum_fecha(match['fecha'][:10]) if 'fecha' in match else ''
    hora = match['time']
    pais = match['pais']
    liga = match['liga']
    home = match['home']
    away = match['away']
    # promedio_gol = match['promedio_gol']
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
    face_matches = match['face_matches']['matches']
    face_ft_1, face_ft_2, face_ft_3, face_ft_4, face_ft_5 = (
        (face_matches[n]['ft'] if n < len(face_matches) else '') for n in range(5) # noqa
    )
    momio_home = match['momio_home'] if 'momio_home' in match else ''
    momio_away = match['momio_away'] if 'momio_away' in match else ''
    # dif_momio_win = ''
    # if momio_home != '-' and momio_away != '':
    #     dif_momio_win = int(momio_home) - int(momio_away)
    momio_si = match['momio_si'] if 'momio_si' in match else ''
    momio_no = match['momio_no'] if 'momio_no' in match else ''
    # dif_momio_sino = ''
    # if momio_si != '-' and momio_no != '':
    #     dif_momio_sino = int(momio_si) - int(momio_no)
    momio_ht_05 = match['momio_ht_05'] if 'momio_ht_05' in match else ''
    momio_ht_15 = match['momio_ht_15'] if 'momio_ht_15' in match else ''
    momio_ht_25 = match['momio_ht_25'] if 'momio_ht_25' in match else ''
    momio_ft_05 = match['momio_ft_05'] if 'momio_ft_05' in match else ''
    momio_ft_15 = match['momio_ft_15'] if 'momio_ft_15' in match else ''
    momio_ft_25 = match['momio_ft_25'] if 'momio_ft_25' in match else ''
    momio_ft_35 = match['momio_ft_35'] if 'momio_ft_35' in match else ''
    momio_ft_45 = match['momio_ft_45'] if 'momio_ft_45' in match else ''
    usuario = match['usuario'] if 'usuario' in match else ''
    correcto = match['correcto'] if 'correcto' in match else ''
    reg = [
        fecha[:10],
        hora,
        home,
        away,
        '-3.5',
        '',  # AP F
        pais,
        liga,
        home_ft_1,
        home_ft_2,
        home_ft_3,
        home_ft_4,
        home_ft_5,
        home_hechos,
        home_concedidos[0],
        home_p_hechos,
        home_p_concedidos,
        away_ft_1,
        away_ft_2,
        away_ft_3,
        away_ft_4,
        away_ft_5,
        away_hechos,
        away_concedidos[0],
        away_p_hechos,
        away_p_concedidos,
        face_ft_1,
        face_ft_2,
        face_ft_3,
        face_ft_4,
        face_ft_5,
        momio_home,
        momio_away,
        momio_si,
        momio_no,
        '',  # DIF AJ
        momio_ht_05,
        momio_ht_15,
        momio_ht_25,
        momio_ft_05,
        momio_ft_15,
        momio_ft_25,
        momio_ft_35,
        momio_ft_45,
        '',  # linea de gol 1  AS
        '',  # linea de gol 2  AT
        '',  # linea de gol 3  AU
        '',  # linea de gol 4  BV
        '',  # ROJA l AW
        '',  # ROJA V AX
        '',  # PROB LOCAL AY
        '',  # PROB VISITANTE AZ
        '',  # PROB EQUIPOS BA
        '',  # FT BB
        '',  # Observaciones BC
        '',  # F1 BD
        '',  # F2 BE
        '',  # F3 BF
        '',  # F4 BG
        '',  # F5 BH
        '',  # F6 BI
        '',  # 1 BJ
        '',  # L1 /  V0  BK
        '',  # 2  BL
        '',  # L1 /  V0  BM
        '',  # 3  BN
        '',  # L1 /  V0  BO
        '',  # 4  BP
        '',  # L1 /  V0  BQ
        '',  # Total  BR
        # '',  # PG  BS
        # '',  # UG  BT
        # '',  # Mensajes  BU
        # '',  # Analisis gol BV
        correcto,
        usuario,
        url
    ]
    # pprint.pprint(reg)
    row = get_last_row(wks)
    wks.update_row(row, reg)
    update_formula(wks, 'AJ', row)  # dif
    update_formula(wks, 'AY', row)  # home_35
    update_formula(wks, 'AZ', row)  # away_35
    update_formula(wks, 'BA', row)  # face_35
    update_formula(wks, 'BD', row)  # F1
    update_formula(wks, 'BE', row)  # F2
    update_formula(wks, 'BF', row)  # F3
    update_formula(wks, 'BG', row)  # F4
    update_formula(wks, 'BH', row)  # F5
    update_formula(wks, 'BI', row)  # F6
    ap = update_formula(wks, 'F', row)  # ap
    return {
        'ap': ap,
        'row': row
    }


def update_formulas_bot_row(wks, row):
    update_formula(wks, 'BJ', row)  # 1
    update_formula(wks, 'BK', row)  # L1 /  V0
    update_formula(wks, 'BL', row)  # 2
    update_formula(wks, 'BM', row)  # L1 /  V0
    update_formula(wks, 'BN', row)  # 3
    update_formula(wks, 'BO', row)  # L1 /  V0
    update_formula(wks, 'BP', row)  # 4
    update_formula(wks, 'BQ', row)  # L1 /  V0
    update_formula(wks, 'BR', row)  # Total
    update_formula(wks, 'BC', row)  # Observaciones
