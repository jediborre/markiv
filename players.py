import csv

players = [
    'Petruchio',
    'Bomb1to',
    'Kodak',
    'palkan',
    'Jekunam',
    'lion',
    'dm1trena',
    'Arcos',
    'Kray',
    'Inquisitor',
    'Koftovsky',
    'Boulevard',
    'Calvin',
    'Flamingo',
    'jAke',
    'Senior',
    'Sava',
    'Shone',
    'lowheels',
    'Bolec',
    'd1pseN',
    'Kravatskhelia',
    'nikkitta',
    'WBoy',
    'hotShot',
    'Izzy',
    'cl1vlind',
    'Glumac',
    'Galikooo',
    'Fratello',
    'Hotshot',
    'Wboy',
    'Menez',
    'SuperMario',
    'BlackStar98',
    'MeLToSik',
    'FEARGGWP'
]


def get_player_stats():
    player_stats = {}

    with open('stats.csv', mode='r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file, delimiter=',')
        for row in csv_reader:
            player = row['Player']

            player_stats[player] = {
                'No': int(row['No']),
                'Jugados': int(row['Jugados']),
                'Ganados': int(row['Ganados']),
                'Empate': int(row['Empate']),
                'Perdidos': int(row['Perdidos']),
                'GH': int(row['GH']),
                'GC': int(row['GC']),
                'AvgGH': float(row['AvgGH']),
                'AvgGC': float(row['AvgGC'])
            }
    return player_stats
