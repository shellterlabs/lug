#!/usr/bin/python
#-*- coding: utf-8 -*-
from collections import OrderedDict
from urllib.parse import quote
from bs4 import BeautifulSoup
from getpass import getpass
from html import unescape
from sys import platform
from sys import argv
from sys import exit
from time import sleep
from re import findall
import requests
import re
import json
import string
import dryscrape
import signal

# To handle with keyboard interruption
def signal_handler(signal, frame):
    print('\nYou pressed Ctrl+C! Bye!')
    exit(0)
signal.signal(signal.SIGINT, signal_handler)

if 'linux' in platform:
    # start xvfb in case no X is running. Make sure xvfb
    # is installed, otherwise this won't work!
    dryscrape.start_xvfb()

class Lug(object):
    def __init__(self, search=''):
        self.welcome()
        self.search = search
        self.client = ''
        self.filename = ''
        self.BASE_URL = 'https://www.linkedin.com'
        self.LOGIN_URI = '/uas/login-submit'
        self.SEARCH_URI = '/search/results/companies/?origin=SWITCH_SEARCH_VERTICAL&keywords={keywords}'
        self.PEOPLE_URI = '/search/results/people/?facetCurrentCompany=["{cp}"]&page={pg}'
        self.LOGIN_URL = self.BASE_URL + self.LOGIN_URI
        self.SEARCH_URL = self.BASE_URL + self.SEARCH_URI


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

    def initfilename(self):
        filename = ''.join([x for x in self.search if x in string.ascii_letters + string.digits])
        filename += '.txt'
        self.filename = filename


    def login(self):
        sess = dryscrape.Session(base_url=self.LOGIN_URL)
        print('Loading search page...')
        sess.visit('/')
        session_email = str(input("Enter the username/email: "))
        session_pass = getpass("Enter the password: ")
        sess.at_xpath('//*[@id="login-email"]').set(session_email)
        sess.at_xpath('//*[@id="login-password"]').set(session_pass)
        sess.at_xpath('//*[@id="login-submit"]').click()

        soup = BeautifulSoup(sess.body(), 'lxml')

        if 'Two Step Verification' in soup.find('title').text:
            desc_text = soup.find('p', {'class':"descriptor-text"}).text
            tsv = str(input('{}\n::: Enter the code ::: '.format(desc_text)))
            sess.at_xpath('//*[@id="verification-code"]').set(tsv)
            sess.exec_script('document.getElementById("recognize-device").removeAttribute("checked");')
            sess.at_xpath('//*[@id="btn-primary"]').click()
        self.client = sess
        return sess


    def select(self):
        search = self.search
        sess = self.login()
        print('Loading search page...')
        for c in range(10):
            sess.visit(self.SEARCH_URI.format(keywords=quote(search)))
            sleep(20 + c)
            sess.interact
            self.client = sess
            if 'results-list' in sess.body():
                break

        soup = BeautifulSoup(sess.body(), 'lxml')
        ul = soup.find('ul', {'class', 'results-list'})
        lis = ul.findAll('li')
        links = dict()
        loop = 5 if len(lis) > 5 else len(lis)
        for idx in range(loop):
            aux = lis[idx].find('div', {'class':'search-result__info'})
            link = aux.find('a', {'class':'search-result__result-link'}).get('href')
            name = aux.find('h3', {'class':'search-result__title'}).text
            desc = aux.find('p', {'class':'subline-level-1'}).text

            if link not in links.keys():
                links[str(idx)] = dict()
            links[str(idx)].update(dict(link=link, name=name, desc=desc))

        choice = self.printlinks(links)
        return choice


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


    def filewrite(self, text):
        if self.filename == '':
            self.initfilename()
        open('{}'.format(self.filename), 'a').write('{}'.format(text))


    def run(self):
        self.get()


    def parse(self, text, company_name):
        soup = BeautifulSoup(text, 'lxml')
        lis = soup.findAll('li', {'class':'search-result'})

        for item in lis:
            name = item.find('span', {'class':'actor-name'})
            if name:
                name = name.text
            occupation = item.find('p', {'class':'search-result__snippets'})
            if occupation:
                occupation = occupation.text.replace('\n', ' ')

            if '{}'.format(company_name).lower() in '{}'.format(occupation).lower():
                try:
                    print(         '[+] :: {} :: {}\n'.format(name, occupation))
                    self.filewrite('[+] :: {} :: {}\n'.format(name, occupation))
                except Exception as e:
                    print(         '[+] :: {} :: {}\n'.format(name.encode('utf-8', 'replace'),
                        occupation.encode('utf-8', 'replace')))
                    self.filewrite('[+] :: {} :: {}\n'.format(name.encode('utf-8', 'replace'),
                        occupation.encode('utf-8', 'replace')))


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
            sess = self.client
            print('Loading search page ({})...'.format(page))
            for c in range(10):
                sess.visit(self.PEOPLE_URI.format(cp=company_id, pg=page))
                sleep(20 + c)
                sess.interact
                self.client = sess
                if 'firstName' in sess.body():
                    break
            if 'search-no-results' in sess.body():
                break

            r = sess.body()
            self.parse(r, company_name)

if __name__ == '__main__':
    if len(argv) != 2:
        # TODO Usage
        print("Usage: python {} <company name>".format(argv[0]))
        exit(1)
    lug = Lug(search=argv[1])
    lug.run()
