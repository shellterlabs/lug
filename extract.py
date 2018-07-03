#!/usr/bin/env python3
import os.path
import random
import re
import signal
import string
import time
from getpass import getpass
from bs4 import BeautifulSoup
from collections import OrderedDict
from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from sys import argv
from sys import exit
from sys import platform
from termcolor import colored
from unidecode import unidecode
from urllib.parse import quote

if 'linux' in platform:
    # start xvfb in case no X is running. Make sure xvfb
    # is installed, otherwise this won't work!
    _xvfb = None
    def start_xvfb():
        from xvfbwrapper import Xvfb
        global _xvfb
        _xvfb = Xvfb()
        _xvfb.start()
        atexit.register(_xvfb.stop)
    def stop_xvfb():
        global _xvfb
        _xvfb.stop()
    start_xvfb()

# To handle with keyboard interruption
def signal_handler(signal, frame):
    print('\nYou pressed Ctrl+C! Bye!')
    exit(0)
signal.signal(signal.SIGINT, signal_handler)

class Lug(object):
    def __init__(self, search=''):
        self.welcome()
        self.search = search
        self.client = ''
        self.filename = ''
        self.BASE_URL = 'https://www.linkedin.com'
        self.LOGIN_URI = '/uas/login'
        self.SEARCH_URI='/search/results/companies/?origin=SWITCH_SEARCH_VERTICAL&keywords={keywords}'
        self.PEOPLE_URI='/search/results/people/?facetCurrentCompany=["{cp}"]&page={pg}'
        self.LOGIN_URL  = self.BASE_URL + self.LOGIN_URI
        self.SEARCH_URL = self.BASE_URL + self.SEARCH_URI
        self.PEOPLE_URL = self.BASE_URL + self.PEOPLE_URI

    def welcome(self):
        print('''
LLLLLLLLLLL            UUUUUUUU     UUUUUUUU       GGGGGGGGGGGGG
L:::::::::L            U::::::U     U::::::U    GGG::::::::::::G
L:::::::::L            U::::::U     U::::::U  GG:::::::::::::::G
LL:::::::LL            UU:::::U     U:::::UU G:::::GGGGGGGG::::G
  L:::::L               U:::::U     U:::::U G:::::G       GGGGGG
  L:::::L               U:::::D     D:::::UG:::::G
  L:::::L               U:::::D     D:::::UG:::::G
  L:::::L               U:::::D     D:::::UG:::::G    GGGGGGGGGG
  L:::::L               U:::::D     D:::::UG:::::G    G::::::::G
  L:::::L               U:::::D     D:::::UG:::::G    GGGGG::::G
  L:::::L               U:::::D     D:::::UG:::::G        G::::G
  L:::::L         LLLLLLU::::::U   U::::::U G:::::G       G::::G
LL:::::::LLLLLLLLL:::::LU:::::::UUU:::::::U  G:::::GGGGGGGG::::G
L::::::::::::::::::::::L UU:::::::::::::UU    GG:::::::::::::::G
L::::::::::::::::::::::L   UU:::::::::UU        GGG::::::GGG:::G
LLLLLLLLLLLLLLLLLLLLLLLL     UUUUUUUUU             GGGGGG   GGGG

WELCOME TO LUG.
The LinkedIn Users Gather tool to extract all users from a LinkedIn Company.

    ''')

    def run(self):
        try:
            self.get()
        except Exception as e:
            print("[!] Error: {}".format(e))
            self.client.quit()

    def get(self):
        company = self.select()
        company_m = re.search(r'/([0-9]+)/',  company['link'])
        company_name = company['name'].lower()
        if not company_m:
            print("Something went wrong")
            exit(1)

        company_id = company_m.group(1)
        page = 0
        while True:
            page += 1
            driver = self.client
            print('Loading search page ({})...'.format(page))
            for c in range(10):
                driver.get(self.PEOPLE_URL.format(cp=company_id, pg=page))
                time.sleep(10 + c)
                self.client = driver
                body = driver.page_source
                if 'firstName' in body:
                    break
            if 'search-no-results' in body:
                break

            scrollDown = "function scrollWin(){\
                    var size = arguments[0];\
                    if( size <= 0 ){ return true; };\
                    window.scrollBy(0,500);\
                    scrolldelay = setTimeout(function(){scrollWin(size-1);},500);\
                    return true;};\
                    scrollWin(5);"
            driver.execute_script(scrollDown)
            time.sleep(3)
            r = driver.page_source
            self.parse(r, company_name)

    def select(self):
        search = self.search
        driver = self.login()
        print('Loading search page...')
        for c in range(10):
            driver.get(self.SEARCH_URL.format(keywords=quote(search)))
            self.client = driver
            if len(driver.find_elements_by_xpath('//ul[contains(@class,"results-list")]')) > 0:
                break
            time.sleep(3)

        soup = BeautifulSoup(driver.page_source, 'lxml')
        ul = soup.find('ul', {'class', 'results-list'})
        lis = ul.findAll('li')
        links = dict()
        loop = 5 if len(lis) > 5 else len(lis)
        for idx in range(loop):
            aux = lis[idx].find('div', {'class':'search-result__info'})
            link = aux.find('a', {'class':'search-result__result-link'})
            link = link.get('href') if link else '??'
            name = aux.find('h3', {'class':'search-result__title'})
            name = name.text.strip() if name else '??'
            desc = aux.find('p', {'class':'subline-level-1'})
            desc = desc.text.strip() if desc else '??'

            if str(idx) not in links.keys():
                links[str(idx)] = dict()
            links[str(idx)].update(dict(link=link, name=name, desc=desc))

        choice = self.printlinks(links)
        return choice

    def setup(self):
        self.display = Display(visible=0, size=(800, 600))
        self.display.start()
        cap = DesiredCapabilities().FIREFOX
        cap["marionette"] = False
        driver = webdriver.Firefox(capabilities=cap, executable_path="/usr/local/bin/geckodriver")
        driver.accept_untrusted_certs = True
        driver.set_window_size(1120, 550)
        return driver

    def login(self):
        driver = self.setup()
        driver.get(self.LOGIN_URL)

        session_email = input("Enter the username/email: ")
        session_pass = getpass("Enter the password: ")
        driver.find_element_by_id("session_key-login").send_keys("{}".format(session_email))
        driver.find_element_by_id("session_password-login").send_keys("{}".format(session_pass))
        driver.find_element_by_xpath("//input[@id='btn-primary']").click()
        wait_one = WebDriverWait(driver, 10)
        self.checkAlert(driver, "session_password-login-error")

        try:
            wait_one.until(EC.visibility_of_element_located((By.ID, "verification-code")))
        except Exception as e:
            try:
                wait_one.until(EC.visibility_of_element_located((By.ID, "feed-tab-icon")))
            except Exception as err:
                driver.quit()
                print("[!] Something went wrong with login")
                exit(1)
        
        self.checkAlert(driver, 'global-alert-queue')
        if len(driver.find_elements_by_id('verification-code')) > 0:
            soup = BeautifulSoup(driver.page_source, 'lxml')
            desc_text = soup.find('p', {'class':"descriptor-text"}).text
            while True:
                tsv = str(input('{}\n::: Enter the code or\n"SMS" To resend via SMS and \n"CALL" to resend via Phone Call.\n::: '.format(desc_text)))
                if tsv == "SMS":
                    driver.find_element_by_xpath("//a[@id='resendCodeTwoStepChallengeViaSms']").click()
                    print("::: The code was resent!")
                elif tsv == "CALL":
                    driver.find_element_by_xpath("//a[@id='resendCodeTwoStepChallengeViaCall']").click()
                    print("::: The code was resent!")
                elif tsv == "":
                    continue
                else:
                    break
            driver.find_element_by_id("verification-code").send_keys("{}".format(tsv))
            driver.find_element_by_id("recognize-device").click()
            driver.find_element_by_xpath("//input[@id='btn-primary']").click()

        try:
            wait_two = WebDriverWait(driver, 10)
            wait_two.until(EC.visibility_of_element_located((By.ID, "feed-tab-icon")))
        except:
            self.checkAlert(driver, 'global-alert-queue')

        self.client = driver
        return driver

    def checkAlert(self, driver, css_id):
        aux_elm = driver.find_elements_by_id(css_id)
        if len(aux_elm) > 0 and aux_elm[0].text != '':
            print('[!] {}'.format(aux_elm[0].text))
            driver.quit()
            exit(1)

    def printlinks(self, links):
        print("Which company you want to proceed?")
        links = OrderedDict(sorted(links.items(), key=lambda t: t[0]))
        for key,value in links.items():
            print("::: [{}] {} ({})".format(key, value['name'], value['desc']))
        print("::: Other char to quit")
        choice = str(input('::: '))
        if not choice or choice not in links.keys():
            print("Bye")
            exit(1)
        return links[choice]

    def initfilename(self):
        filename = ''.join([x for x in self.search if x in string.ascii_letters + string.digits])
        filename += '.txt'
        self.filename = filename

    def filewrite(self, text):
        if self.filename == '':
            self.initfilename()
        open('{}'.format(self.filename), 'a').write('{}'.format(text))

    def parse(self, text, company_name):
        soup = BeautifulSoup(text, 'lxml')
        lis = soup.findAll('li', {'class':'search-result'})

        for item in lis:
            name = item.find('span', {'class':'actor-name'})
            name = name.text.strip() if name else "??"
            occupation = item.find('p', {'class':'search-result__snippets'})
            occupation = occupation.text.replace('\n', ' ').strip() if occupation else "??"
            try:
                print('[+] :: {} :: {}'.format(unidecode(name), unidecode(occupation)))
                self.filewrite('[+] :: {} :: {}\n'.format(unidecode(name), unidecode(occupation)))
            except Exception as e:
                print('[+] :: {} :: {}\n'.format(unidecode(name.encode('utf-8', 'replace')),
                                                 unidecode(occupation.encode('utf-8', 'replace'))))
                self.filewrite('[+] :: {} :: {}\n'.format(unidecode(name.encode('utf-8', 'replace')),
                                                 unidecode(occupation.encode('utf-8', 'replace'))))

if __name__ == '__main__':
    if len(argv) != 2:
        print('Usage: python {} "<company name>"'.format(argv[0]))
        exit(1)
    lug = Lug(search=argv[1])
    lug.run()
