def es_momio_americano(texto):
    try:
        if texto == '-':
            return True
        momio = int(texto) # noqa
        return True
    except ValueError:
        return False


def get_paises_count(paises):
    result = []
    num_juegos = 0
    pais_cuenta = []
    for pais in paises:
        n_juegos_pais = len(paises[pais])
        pais_cuenta.append([pais, n_juegos_pais])
        num_juegos += n_juegos_pais
    result.append(f'Juegos de hoy: {num_juegos}')
    pais_cuenta_sorted = sorted(
        pais_cuenta,
        key=lambda x: x[1],
        reverse=True
    )
    if len(pais_cuenta_sorted) > 0:
        for pais, n in pais_cuenta_sorted:
            result.append(f'{pais} [{n}]')
    return '\n'.join(result)


def get_match_paises(matches) -> str:
    result = []
    for match in matches:
        id = match["id"]
        time = match["time"]
        liga = match["liga"]
        home = match["home"]
        away = match["away"]
        result.append(f'#{id} {time} {liga} {home} - {away}')

    return '\n'.join(result)


def get_match_details(match, with_momios=False) -> str:
    id = match['id']
    fecha = match['fecha']
    home = match['home']
    away = match['away']
    liga = match['liga']
    pais = match['pais'] + ' ' if match['pais'] != 'sinpais' else ''
    pGol = match['promedio_gol']
    home_matches = match['home_matches']
    away_matches = match['away_matches']
    face_matches = match['face_matches']
    home_gP = home_matches['hechos']
    home_gM = home_matches['concedidos']
    home_pgP = home_matches['p_hechos']
    home_pgM = home_matches['p_concedidos']
    # home_n_games = len(home_matches)
    home_games = '\n'.join(f'{m["ft"]}    {m["home_ft"]} - {m["away_ft"]}    {m["home"][:5]} - {m["away"][:5]}' for m in home_matches['matches']) # noqa
    away_gP = away_matches['hechos']
    away_gM = away_matches['concedidos']
    away_pgP = away_matches['p_hechos']
    away_pgM = away_matches['p_concedidos']
    # away_n_games = len(away_matches)
    away_games = '\n'.join(f'{m["ft"]}    {m["home_ft"]} - {m["away_ft"]}    {m["home"][:5]} - {m["away"][:5]}' for m in away_matches['matches']) # noqa
    face_games = '\n'.join(f'{m["ft"]}    {m["home_ft"]} - {m["away_ft"]}    {m["home"][:5]} - {m["away"][:5]}' for m in face_matches) # noqa
    result = f'''
#{id} {fecha}
{pais}{liga}
{home} v {away}

G PARTIDO: {pGol}
{home}
+: {home_gP} -: {home_gM} P+: {home_pgP} P-: {home_pgM}
{home_games}

{away}
+: {away_gP} -: {away_gM} P+: {away_pgP} P-: {away_pgM}
{away_games}

vs
{face_games}''' # noqa
    if with_momios:
        momio_home = match['momio_home'] if 'momio_home' in match else ''
        momio_away = match['momio_away'] if 'momio_away' in match else ''
        momio_si = match['momio_si'] if 'momio_si' in match else ''
        momio_no = match['momio_no'] if 'momio_no' in match else ''
        momio_ht_05 = match['momio_ht_05'] if 'momio_ht_05' in match else ''
        momio_ht_15 = match['momio_ht_15'] if 'momio_ht_15' in match else ''
        momio_ht_25 = match['momio_ht_25'] if 'momio_ht_25' in match else ''
        momio_ft_05 = match['momio_ft_05'] if 'momio_ft_05' in match else ''
        momio_ft_15 = match['momio_ft_15'] if 'momio_ft_15' in match else ''
        momio_ft_25 = match['momio_ft_25'] if 'momio_ft_25' in match else ''
        momio_ft_35 = match['momio_ft_35'] if 'momio_ft_35' in match else ''
        momio_ft_45 = match['momio_ft_45'] if 'momio_ft_45' in match else ''
        result += f'''

Ganador: {momio_home} {momio_away}
Ambos Anotan: {momio_si} {momio_no}
Gol HT: {momio_ht_05} {momio_ht_15} {momio_ht_25}
Gol FT: {momio_ft_05} {momio_ft_15} {momio_ft_25} {momio_ft_35} {momio_ft_45}''' # noqa
    return result
