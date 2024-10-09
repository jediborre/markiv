import os
import logging
from web import Web

# .venv/Scripts/Activate.ps1
# chrome --remote-debugging-port=9222 --user-data-dir="C:\Log"
# python db/flashcore.py

# https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&protocol=http&proxy_format=protocolipport&format=text&timeout=3017

script_path = os.path.dirname(os.path.abspath(__file__))
log_filepath = os.path.join(script_path, 'web_markiv.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filepath),
        logging.StreamHandler()
    ]
)

cookies = [{
    'name': 'OptanonConsent',
    'value': 'isGpcEnabled=1&datestamp=Sat+Oct+05+2024+06%3A53%3A55+GMT-0600+(hora+est%C3%A1ndar+central)&version=202409.1.0&browserGpcFlag=0&isIABGlobal=false&consentId=153ea036-ef56-48a0-ab5e-24553c7cfdf9&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0004%3A1%2CV2STACK42%3A1&hosts=H594%3A1%2CH481%3A1%2CH289%3A1%2CH233%3A1%2CH283%3A1%2CH374%3A1%2CH286%3A1%2CH317%3A1%2CH517%3A1%2CH3%3A1%2CH8%3A1%2CH371%3A1%2CH192%3A1%2Cdrt%3A1%2CH463%3A1%2CH16%3A1%2CH190%3A1%2CH19%3A1%2CH21%3A1%2CH171%3A1%2CH25%3A1%2CH31%3A1%2CH195%3A1%2Cxhy%3A1%2Crkk%3A1%2CH35%3A1%2CH484%3A1%2CH598%3A1%2CH42%3A1%2Coiu%3A1%2Cifk%3A1%2CH499%3A1%2CH199%3A1%2CH485%3A1%2CH58%3A1%2CH64%3A1%2CH464%3A1%2CH68%3A1%2CH70%3A1%2CH500%3A1%2CH292%3A1%2CH79%3A1%2CH81%3A1%2CH85%3A1%2CH86%3A1%2CH87%3A1%2CH487%3A1%2CH89%3A1%2CH543%3A1%2CH596%3A1%2CH96%3A1%2CH99%3A1%2CH518%3A1%2CH106%3A1%2CH109%3A1%2Ctbv%3A1%2CH294%3A1%2CH112%3A1%2CH473%3A1%2CH115%3A1%2CH217%3A1%2Ccch%3A1%2CH119%3A1%2CH125%3A1%2CH127%3A1%2CH128%3A1%2CH129%3A1%2CH132%3A1%2CH465%3A1%2Csey%3A1%2CH503%3A1%2CH138%3A1%2Cygh%3A1%2CH145%3A1%2CH146%3A1%2CH150%3A1%2CH562%3A1%2CH152%3A1%2CH154%3A1%2Cueh%3A1%2CH477%3A1%2CH156%3A1%2Csef%3A1%2CH207%3A1%2CH162%3A1%2CH208%3A1%2CH209%3A1%2CH166%3A1%2Cfrw%3A1%2CH211%3A1%2Caeg%3A1&genVendors=V2%3A1%2C&intType=1&geolocation=MX%3BCMX&AwaitingReconsent=false', # noqa
    'domain': '.flashscore.com.mx',
    'path': '/',
}, {
    'name': 'OptanonAlertBoxClosed',
    'value': '2024-10-05T12:30:15.161Z',
    'domain': '.flashscore.com.mx',
    'path': '/',
}]

# https://app.dataimpulse.com/plans/create-new
proxy_url = 'https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&country=mx,us,ca&protocol=http&proxy_format=ipport&format=text&timeout=4000' # noqa
url = 'https://www.flashscore.com.mx/'
web = Web(proxy_url=proxy_url, url=url)
web.click_id('hamburger-menu')
web.click_class('contextMenu__row')
# label        class="radioButton settings__label" Hora de Inicioi
# div cerrar   class="header__button header__button--active"
