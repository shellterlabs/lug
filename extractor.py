from bs4 import BeautifulSoup as BS
from collections import OrderedDict
from colored import fg
from colored import stylize
from datetime import datetime
from getpass import getpass
from splinter import Browser
from sys import argv
from sys import exit
from time import sleep
from unidecode import unidecode
from urllib.parse import quote
from urllib.parse import urljoin
import string
import signal
import ipdb
import os

isDebug = True
outputfile = f"{datetime.now().strftime('%Y%m%d%H%M%S-%s')}_employees.log"

def debug():
  ipdb.set_trace()

gBrowser = None

# To handle with keyboard interruption
def signal_handler(signal, frame):
  print('\nYou pressed Ctrl+C! Bye!')
  try:
    # Try to avoid defunct proccesses
    gBrowser.quit()
  except:
    pass
  exit(0)
signal.signal(signal.SIGINT, signal_handler)

def shift(msg, width=70, spaces=4):
  aux = list()
  while True:
    line = msg[:width].rsplit(" ",1)[0].strip()
    aux.append(" " * spaces + line.strip())
    lenl = len(line)
    msg = msg[lenl:].strip()
    if len(msg) <= width:
        aux.append(" " * spaces + msg.strip())
        break
  return '\n'.join(aux)

def _print(symbol, msg, **kwargs):
  aux = str()
  if symbol == "warning":
    aux = stylize('[!]', fg("orange_3"))
  elif symbol == "success":
    aux = stylize('[+]', fg("green"))
  elif symbol == "error":
    aux = stylize('[-]', fg("red"))
  elif symbol == "info":
    aux = stylize('[>]', fg("white"))
  elif symbol == "choice":
    line = msg.split(" ", 1)
    aux = stylize(line[0], fg("blue"))
    msg = stylize(line[-1], fg("grey_54"))
  elif symbol == "employee":
    aux = stylize('[+]', fg("green"))
    line = msg.split(":: ", 3)
    msg = ":: ".join([stylize(line[1], fg("magenta")), stylize(line[2], fg("blue"))])

  if kwargs.get("color", None):
    msg = stylize(msg, fg(kwargs.get("color")))

  print("{} {}".format(aux, msg))


class Lug(object):
  def __init__(self, search=''):
    self.welcome()
    self.search = search
    self.client = ''
    self.session_user = str()
    self.session_pass = str()
    self.filename = self.initFilename(search)
    self.BASE_URL = 'https://www.linkedin.com'
    self.LOGIN_URI = '/login'
    self.SEARCH_URI='/search/results/companies/?origin=SWITCH_SEARCH_VERTICAL&keywords={keywords}'
    self.PEOPLE_URI='/search/results/people/?facetCurrentCompany=["{cp}"]&page={pg}'
    self.LOGIN_URL  = urljoin(self.BASE_URL, self.LOGIN_URI)
    self.SEARCH_URL = urljoin(self.BASE_URL, self.SEARCH_URI)
    self.PEOPLE_URL = urljoin(self.BASE_URL, self.PEOPLE_URI)
    ##
    self.browser = self.initBrowser(headless=False if isDebug else True)
    global gBrowser
    gBrowser = self.browser

  def initBrowser(self, headless=True):
    return Browser('firefox', headless=headless, capabilities={'acceptSslCerts': True})

  def initFilename(self, search):
    filename = ''.join([x for x in search if x in string.ascii_letters + string.digits])
    filename += '.txt'
    return filename.replace(" ", "")

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

  def hideBrowser(self, browser=None):
    if not browser:
      browser = self.browser

  def login(self, username='', password='', browser=None, reRun=False):
    if not browser:
      browser = self.browser

    def fillAndClick(browser, username, password):
      browser.find_by_id('username').first.value = username
      browser.find_by_id('password').first.value = password
      if isDebug: browser.screenshot("/tmp/splinter", full=True)
      browser.find_by_xpath("//button[@type='submit']").first.click()
      if isDebug: browser.screenshot("/tmp/splinter", full=True)

      if not browser.find_by_id("error-for-username").is_empty():
        _print("error", "{}".format(browser.find_by_id("error-for-username").first.text))
        exit(1)
      if not browser.find_by_id("error-for-password").is_empty():
        _print("error", "{}".format(browser.find_by_id("error-for-password").first.text))
        exit(1)
    # Login
    url = self.LOGIN_URL
    ## Visit URL
    browser.visit(url)
    fillAndClick(browser, username, password)

    ### TODO: Captcha Internal
    # id: captcha-internal
    captcha_elm = browser.find_by_id('captcha-internal')
    if not captcha_elm.is_empty():
      if not reRun:
        # Re-run login in windowed mode to solve captch
        browser.quit()
        browser = self.initBrowser(headless=False)
        browser = self.login(self.session_user, self.session_pass, browser=browser, reRun=True)
        self.browser = browser
        return browser
      _print("warning", "Captcha detected re-running login in windowed mode to solve captcha")
      _print("warning", "Press enter when captcha was solved successfully: ")
      input()
      fillAndClick(browser, username, password)
      #exit(1)
    else:
      _print("info", "No captcha detected!")

    ### TODO: Confirm Account Info
    # class: cp-card-new
    confirm_elm = browser.find_by_xpath("//div[@class='cp-card-new']")
    if not confirm_elm.is_empty():
      if isDebug: debug()
      if isDebug: browser.screenshot("/tmp/splinter", full=True)
      if 'Confirm your account information' in confirm_elm.first.text:
        skip = browser.find_by_xpath("//button[@class='secondary-action-new']")
        if not skip.is_empty() and 'Skip' in skip.first.text:
          skip.first.click()
    else:
      _print("info", "No account info confirmation detected!")

    ### TODO: Wrong Password
    username_elm = browser.find_by_id('username')
    if not username_elm.is_empty():
      usr_elm = browser.find_by_id('error-for-username')
      pwd_elm = browser.find_by_id('error-for-password')
      err_usr = usr_elm.first.text if not usr_elm.is_empty() else ''
      err_pwd = pwd_elm.first.text if not pwd_elm.is_empty() else ''
      _print("error", "{}".format(err_usr if err_usr else err_pwd))
      exit(1)

    ### TODO: Verify if 2FA was trigged
    #browser.find_by_id("input__phone_verification_pin").first.value = '634522'
    #if isDebug: browser.screenshot("/tmp/splinter", full=True, random=False)
    #browser.find_by_xpath('//button[@id="two-step-submit-button"]').first.click()
    #if isDebug: browser.screenshot("/tmp/splinter", full=True, random=False)
    ## Logged Page:
    if browser.find_by_xpath('//div[@class="search-global-typeahead__search-icon-container"]').is_empty():
      _print("error", "Something went wrong!")
      exit(1)
    self.browser = browser
    return browser

    ### TODO: Verify if 2FA was trigged
    #cookies_elm = browser.find_by_id('')

  def chooseCompany(self, cia_dict):
    _print("info", "Which company you want to proceed?")
    _print("info", "If not find it try to be more specific.")
    for ciaK,ciaV in cia_dict.items():
      _print("choice", "[{}] {}".format(ciaK, ciaV.get('name','')))
      _print("info", shift("{}".format(ciaV.get('description',''))).strip())
      # print(ciaV.get('description', {}))
    _print("choice", "[q] To quit")
    choice = str(input("Enter the choice: "))
    if choice == "q" or choice not in cia_dict.keys():
      print("Bye")
      exit(1)
    choice = cia_dict.get(choice)
    _print("", "---")
    _print("info", "::: Company information:")
    _print("info", "\t{}".format(choice.get("name")), color="grey_54")
    _print("info", "::: Description:")
    _print("info", shift("{}".format(choice.get("description"))), color="grey_54")
    return choice

  def search_company(self, company, browser=None):
    if not browser:
      browser = self.browser
    ## SEARCH COMPANY
    url = self.SEARCH_URL.format(keywords=quote(company))
    browser.visit(url)
    if isDebug: browser.screenshot("/tmp/splinter", full=True)

    company_list_elm = browser.find_by_xpath('//ul[contains(@class,"result-list")]')
    if company_list_elm.is_empty():
      # TODO Nice Exit
      exit(1)
    soup = BS(company_list_elm.first.html, 'lxml')
    company_list = soup.findAll('div', {'class': 'entity-result__content'})
    company_dict = OrderedDict()
    for idx,cia in enumerate(company_list):
      idx = str(idx)
      # Get link
      a_elm = cia.find("a", {"class": "app-aware-link"})
      if not a_elm:
        # TODO Nice Exit
        exit(1)
      link = a_elm.get("href", "")

      # Get Name
      span_elm = cia.find('span', {'class': 'entity-result__title-text'})
      if not span_elm:
        # TODO Nice Exit
        exit(1)
      name = unidecode(span_elm.getText().strip())

      # Get Description
      p_elm = cia.find('p', {'class': 'entity-result__summary'})
      if not p_elm:
        # TODO Nice Exit
        exit(1)
      desc = unidecode(p_elm.getText().strip())

      if idx not in company_dict.keys():
        company_dict[idx] = dict()
      company_dict[idx] = {
          "name": name,
          "url": link,
          "description": desc,
      }

    choice = self.chooseCompany(company_dict)
    browser.visit(choice.get("url"))
    if isDebug: browser.screenshot("/tmp/splinter", full=True)
    e_link = browser.find_by_xpath('//span[contains(@class,"link-without-visited-state")]')
    if e_link.is_empty():
      # TODO Nice exit
      exit(1)
    e_link.click()
    self.browser = browser
    return choice


  def getEmployeers(self, browser=None):
    if not browser:
      browser = self.browser

    # Click on employeers link
    employeers = dict()
    browser_html = BS(browser.html, 'lxml')
    while True:
      if isDebug: browser.screenshot("/tmp/splinter", full=True)
      if not browser.is_element_present_by_xpath('//ul[contains(@class,"result-list")]', wait_time=10):
        continue
      soup = BS(browser.find_by_xpath('//ul[contains(@class,"result-list")]').first.html, 'lxml')
      for item in soup.findAll("div", {"class": "entity-result__content"}):
        if 'LinkedIn Member'.lower() in item.text.lower():
          continue
        name = item.find("span", {"dir": "ltr"}).find("span")
        name = unidecode(name.text.strip() if name else '')
        occu = item.find("div", {"class": "entity-result__primary-subtitle"})
        occu = unidecode(occu.text.strip() if occu else '')
        if not name and not occu:
          continue
        _print("employee", ":: {} :: {}".format(name, occu))
        with open(outputfile, "a") as fp:
          fp.write("[+] :: {} :: {}\n".format(name, occu))

      # Next page
      if browser.is_element_present_by_xpath('//button[contains(@class,"--disabled")]'):
        elm = browser.find_by_xpath('//button[contains(@class,"--disabled")]')
        if not elm.is_empty() and elm.first.text == 'Next':
          break
      count = 0
      browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
      while not browser.is_element_present_by_text("Next"):
        if isDebug: browser.screenshot("/tmp/splinter", full=True)
        count += 1
        if count > 5:
          _print("error", "Something went wrong")
          exit(1)
        sleep(1)
        continue
      if isDebug: browser.screenshot("/tmp/splinter", full=True)
      browser.find_by_text("Next").first.click()
      sleep(1)
    return

  def run(self):
    # Start browser object
    print(self.session_user, self.session_pass)
    self.session_user = os.environ.get('LINKEDIN_USR', "")
    self.session_pass = os.environ.get('LINKEDIN_PWD', "")
    if not self.session_user or not self.session_pass:
      self.session_user = input("Enter the username/email: ")
      self.session_pass = getpass("Enter the password: ")
    _print("", "---")
    self.browser = self.login(self.session_user,self.session_pass)
    choice = self.search_company(self.search)
    # Handler Employeers Page
    self.getEmployeers(self.browser)
    _print("info","The End")
    _print("info","With any luck the result is in the {} file.".format(outputfile))

    self.browser.quit()

if __name__ == '__main__':
  if len(argv) < 2:
    print("Usage: python {} <company_name>".format(argv[0]))
    exit(1)
  term = ' '.join(argv[1:])
  lug = Lug(search=term)
  lug.run()
