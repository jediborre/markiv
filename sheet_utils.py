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


def update_formula(formula, source_row, target_row):
    pattern = r'([A-Z]+)(\d+)'
    updated_formula = re.sub(pattern, lambda match: f"{match.group(1)}{int(match.group(2)) - source_row + target_row}", formula)  # noqa
    return updated_formula


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
    home_35 = f'{match["home_matches"]["p35"] * 100}%'
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
    away_35 = f'{match["away_matches"]["p45"] * 100}%'
    face_matches = match['face_matches']['matches']
    face_ft_1, face_ft_2, face_ft_3, face_ft_4, face_ft_5 = (
        (face_matches[n]['ft'] if n < len(face_matches) else '') for n in range(5) # noqa
    )
    face_35 = f'{match["face_matches"]["p35"] * 100}%'
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
    revision = match['revision'] if 'revision' in match else ''
    # f1 = get_f1(dif_momio_sino)
    last_row = get_last_row(wks)
    x1 = update_formula(wks.cell('F3').formula, 3, last_row)
    x2 = update_formula(wks.cell('G3').formula, 3, last_row)
    x3 = update_formula(wks.cell('T3').formula, 3, last_row)
    dif = update_formula(wks.cell('AN3').formula, 3, last_row)
    f1 = update_formula(wks.cell('BI3').formula, 3, last_row)
    f2 = update_formula(wks.cell('BJ3').formula, 3, last_row)
    f3 = update_formula(wks.cell('BK3').formula, 3, last_row)
    f4 = update_formula(wks.cell('BL3').formula, 3, last_row)
    f5 = update_formula(wks.cell('BM3').formula, 3, last_row)
    f6 = update_formula(wks.cell('BN3').formula, 3, last_row)
    ap = update_formula(wks.cell('BO3').formula, 3, last_row)
    reg = [
        fecha[:10],
        hora,
        home,
        away,
        '-3.5',  # AP
        x1,  # X1 F
        x2,  # X2 G
        pais,
        liga,
        home_ft_1,
        home_ft_2,
        home_ft_3,
        home_ft_4,
        home_ft_5,
        home_hechos,
        home_concedidos[0],
        '5',  # no juegos Local
        home_p_hechos,
        home_p_concedidos,
        x3,  # X3 T
        away_ft_1,  # U
        away_ft_2,
        away_ft_3,
        away_ft_4,
        away_ft_5,
        away_hechos,
        away_concedidos[0],
        '5',  # no juegos Visitante
        away_p_hechos,
        away_p_concedidos,
        face_ft_1,  # AE
        face_ft_2,
        face_ft_3,
        face_ft_4,
        face_ft_5,
        momio_home,  # AJ
        momio_away,
        momio_si,  # AL
        momio_no,
        '',  # DIF AN
        momio_ht_05,  # AO
        momio_ht_15,
        momio_ht_25,
        momio_ft_05,  # AR
        momio_ft_15,
        momio_ft_25,
        momio_ft_35,
        momio_ft_45,
        '',  # -5.5  AW
        '',  # linea de gol 1  AX
        '',  # linea de gol 2  AY
        '',  # linea de gol 3  AZ
        '',  # linea de gol 4  BA
        '',  # ROJA l BB
        '',  # ROJA V BC
        home_35,  # BD
        away_35,
        face_35,
        '',  # Total BG
        '',  # Observacion BH
        '',  # f1 BI
        '',  # f2 BJ
        '',  # f3 BK
        '',  # f4 BL
        '',  # f5 BM
        '',  # f6 BN
        '',  # AP BO
        revision,  # Revision
        usuario,  # Usuario
        url  # link totalcorner
    ]
    # pprint.pprint(reg)
    wks.update_row(last_row, reg)
    wks.update_value(f'F{last_row}', x1)
    wks.update_value(f'G{last_row}', x2)
    wks.update_value(f'T{last_row}', x3)
    wks.update_value(f'AN{last_row}', dif)
    wks.update_value(f'BI{last_row}', f1)
    wks.update_value(f'BJ{last_row}', f2)
    wks.update_value(f'BK{last_row}', f3)
    wks.update_value(f'BL{last_row}', f4)
    wks.update_value(f'BM{last_row}', f5)
    wks.update_value(f'BN{last_row}', f6)
    wks.update_value(f'BO{last_row}', ap)
