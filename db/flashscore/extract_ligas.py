import os
import json
import glob

path = "./db/flashscore/"
files = [os.path.basename(file) for file in glob.glob(f"{path}/*.json") if not '_pais' in os.path.basename(file)] # noqa
ligas = []
for filename in files:
    f = open(f'{path}{filename}', 'r')
    file = json.loads(f.read())
    f.close()
    for id in file:
        reg = file[id]
        liga = reg['liga']
        if liga not in ligas:
            ligas.append(liga)
for liga in ligas:
    print(liga)