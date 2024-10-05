import sys
import random
import logging
import psutil
from dotenv import load_dotenv
from selenium import webdriver
from utils.utils import kill_processes_by_name
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import SessionNotCreatedException

load_dotenv()


class Web:
    driver: webdriver.Chrome = None

    def __init__(self) -> None:
        self.user_agents = [
            # Desktop browsers
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36", # noqa
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36 Edg/94.0.992.31", # noqa
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36", # noqa
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15", # noqa
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0", # noqa
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:93.0) Gecko/20100101 Firefox/93.0", # noqa
            "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko", # noqa
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15", # noqa

            # Mobile browsers
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1", # noqa
            "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Mobile Safari/537.36", # noqa
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/94.0.4606.51 Mobile/15E148 Safari/604.1", # noqa
            "Mozilla/5.0 (Linux; Android 11; SM-G991U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Mobile Safari/537.36", # noqa
            "Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1", # noqa
            "Mozilla/5.0 (Linux; Android 11; SM-G991U) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/16.0 Chrome/94.0.4606.61 Mobile Safari/537.36", # noqa

            # Others
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)", # noqa
            "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)", # noqa
        ]

        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('log-level=3')
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument(f"user-agent={self.random_user_agent()}")
        # chrome_options.debugger_address = "localhost:9222"
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.maximize_window()
        except SessionNotCreatedException as e:
            print(e.msg)
            sys.exit(0)

    def log(self, message):
        logging.info(f'WEB: {message}')

    def random_user_agent(self):
        return random.choice(self.user_agents)

    def close(self):
        try:
            self.driver.close()
        except Exception:
            pass

    def quit(self):
        self.driver.close()
        self.driver.quit()
        kill_processes_by_name("chrome")
        kill_processes_by_name("chromedriver")

    def get_cookies(self):
        return self.driver.get_cookies()

    def set_coockies(self, cookies):
        for cookie in cookies:
            self.driver.add_cookie(cookie)
        self.driver.refresh()

    def open(self, url, debug=False):
        if debug:
            self.log('opening: ' + url)
        try:
            web = self.driver
            web.get(url)
        except WebDriverException as e:
            self.log('WebDriverException')
            print(e.msg)

    def source(self):
        return self.driver.page_source

    def save_screenshot(self, filename):
        self.driver.save_screenshot(filename)

    def kill_processes_by_name(self, name):
        for process in psutil.process_iter(['pid', 'name']):
            if process.info['name'] == name:
                process.kill()
