import sys
import random
import psutil
import logging
import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import SessionNotCreatedException

load_dotenv()


class Web:
    driver: webdriver.Chrome = None

    def __init__(self, proxy_url=None) -> None:
        self.user_agents = [
            # Desktop
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36", # noqa
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36 Edg/94.0.992.31", # noqa
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36", # noqa
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15", # noqa
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0", # noqa
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:93.0) Gecko/20100101 Firefox/93.0", # noqa
            "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko", # noqa
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15", # noqa

            # Mobile
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1", # noqa
            "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Mobile Safari/537.36", # noqa
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/94.0.4606.51 Mobile/15E148 Safari/604.1", # noqa
            "Mozilla/5.0 (Linux; Android 11; SM-G991U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Mobile Safari/537.36", # noqa
            "Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1", # noqa
            "Mozilla/5.0 (Linux; Android 11; SM-G991U) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/16.0 Chrome/94.0.4606.61 Mobile Safari/537.36", # noqa

            # Otros
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)", # noqa
            "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)", # noqa
        ]
        self.proxies = self.get_proxies_from_url(proxy_url) if proxy_url else [] # noqa

        if not self.proxies:
            raise Exception("No proxies available")

        self.start_browser()

    def get_proxies_from_url(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            proxies = response.text.splitlines()
            return [proxy.strip() for proxy in proxies if proxy.strip()]
        except requests.RequestException as e:
            print(f"Error fetching proxies from {url}: {e}")
            return []

    def start_browser(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('log-level=3')
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument(f"user-agent={self.random_user_agent()}")
        chrome_options.add_argument(f"--proxy-server={self.random_proxy()}")

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
        self.kill_processes_by_name("chrome")
        self.kill_processes_by_name("chromedriver")

    def get_cookies(self):
        return self.driver.get_cookies()

    def set_coockies(self, cookies):
        for cookie in cookies:
            self.driver.add_cookie(cookie)
        self.driver.refresh()

    def open(self, url, debug=False):
        if self.driver:
            self.quit()

        self.start_browser()

        if debug:
            self.log('Opening: ' + url)

        try:
            self.driver.get(url)
        except WebDriverException as e:
            self.log(f"Error opening URL: {e.msg}")

    def ID(self, id):
        return self.driver.find_element(By.ID, id)

    def CLASS(self, class_name):
        return self.driver.find_element(By.CLASS_NAME, class_name)

    def source(self):
        return self.driver.page_source

    def save_screenshot(self, filename):
        self.driver.save_screenshot(filename)

    def kill_processes_by_name(self, name):
        for process in psutil.process_iter(['pid', 'name']):
            if process.info['name'] == name:
                process.kill()

    def click_id(self, id):
        try:
            element = self.ID(id)
            element.click()
        except WebDriverException as e:
            self.log(f"Failed to click element by ID: {id}. Error: {str(e)}")

    def click_class(self, class_name):
        try:
            element = self.CLASS(class_name)
            element.click()
        except WebDriverException as e:
            self.log(f"Failed to click element by class: {class_name}. Error: {str(e)}") # noqa