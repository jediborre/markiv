import os
import logging
import datetime
from web import Web
# https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json

# .venv/Scripts/Activate.ps1
# chrome --remote-debugging-port=9222 --user-data-dir="C:\Log"
# python db/flashcore.py

# https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&protocol=http&proxy_format=protocolipport&format=text&timeout=3017

script_path = os.path.dirname(os.path.abspath(__file__))
log_filepath = os.path.join(script_path, 'web_markiv.log')
source_path = os.path.join(script_path, 'flashcore')
if not os.path.exists(source_path):
    os.makedirs(source_path)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filepath),
        logging.StreamHandler()
    ]
)

# https://app.dataimpulse.com/plans/create-new
proxy_url = 'https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&country=mx,us,ca&protocol=http&proxy_format=ipport&format=text&timeout=4000' # noqa
# url = 'https://www.flashscore.com.mx/'
# web = Web(proxy_url=proxy_url, url=url)
# web.click_id('hamburger-menu')
# web.click_class('contextMenu__row')
# label        class="radioButton settings__label" Hora de Inicioi
# div cerrar   class="header__button header__button--active"

mobile_url = 'https://m.flashscore.com.mx/?d=1'
proxy_url = 'https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&country=mx,us,ca&protocol=http&proxy_format=ipport&format=text&timeout=4000' # noqa
web = Web(proxy_url=proxy_url, url=mobile_url)
source = web.source()
hoy = datetime.today().strftime('%Y-%m-%d')
open(f'{source_path}/flashscore_{hoy}.html', 'w').write(source)
partidos = web.ID('score-data')
ligas = web.TAG('h4')
for liga in ligas:
    print(liga.text)
