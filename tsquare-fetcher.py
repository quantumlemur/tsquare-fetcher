#!/usr/bin/python3

from fcntl import fcntl, F_SETFL
# from getpass import getpass
from os import O_NONBLOCK, makedirs, rename
from os.path import expanduser
from queue import Queue
from re import compile
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from subprocess import Popen, PIPE
from threading import Thread
from time import time



username = ''
password = ''

# read the login info from the .netrc file
with open(expanduser('~/.netrc'), 'r') as f:
    for line in f:
        if line[:5] == 'login':
            username = line.split()[1]
        if line[:8] == 'password':
            password = line.split()[1]


# initialize the webdriver and start the tsquare login process
print('trying to log in to tsquare... get out your phone and be ready to approve the two-factor auth!')
options = webdriver.ChromeOptions()
options.add_argument('headless')
driver = webdriver.Chrome()
driver.get("https://login.gatech.edu/cas/login?service=https%3A%2F%2Ft-square.gatech.edu%2Fsakai-login-tool%2Fcontainer")
assert "GT Login" in driver.title

# enter username
u = driver.find_element_by_name('username')
u.clear()
u.send_keys(username)

# enter password
p = driver.find_element_by_name('password')
p.clear()
p.send_keys(password)

# login
p.send_keys(Keys.RETURN)

# check if password is correct
assert 'Incorrect login or disabled account.' not in driver.page_source

# check for two-factor
if 'Two-factor login is needed' in driver.page_source:
    WebDriverWait(driver, 10).until(expected_conditions.presence_of_element_located((By.ID, 'duo_iframe')))
    driver.switch_to_frame('duo_iframe')
    WebDriverWait(driver, 10).until(expected_conditions.presence_of_element_located((By.XPATH, '//*[@id="login-form"]/fieldset[2]/div[1]/button')))
    btn = driver.find_element_by_xpath('//*[@id="login-form"]/fieldset[2]/div[1]/button')
    WebDriverWait(driver, 10).until(expected_conditions.visibility_of(btn))
    btn.click()
    driver.switch_to_default_content()

# we should be logged in and in tsquare now
WebDriverWait(driver, 60).until(expected_conditions.presence_of_element_located((By.XPATH, '//*[@id="siteLinkList"]/li[1]/a/span')))
print('Login successful.  Collecting sites...')
# go to the worksite list
assert 'Worksite Setup' in driver.page_source
worksite_link = driver.find_element_by_link_text('Worksite Setup')
worksite_link.click()

site_links = {}

# wait and find the worksite iframe
WebDriverWait(driver, 60).until(expected_conditions.presence_of_element_located((By.CSS_SELECTOR, 'iframe[title="Worksite Setup "]')))
iframe = driver.find_elements_by_css_selector('iframe[title="Worksite Setup "]')[0]
driver.switch_to_frame(iframe.get_attribute('id'))

print('switched to inner iframe')


# scrape the actual worksite links
filename_pattern = compile('[^\w\-_\. ]')
WebDriverWait(driver, 10).until(expected_conditions.presence_of_element_located((By.NAME, 'eventSubmit_doList_next')))
next_button = driver.find_element_by_name('eventSubmit_doList_next')
titles = driver.find_elements_by_css_selector('td[headers="title"]')
for title in titles:
    link = title.find_element_by_tag_name('a')
    site_links[filename_pattern.sub('_', link.text)] = link.get_attribute('href').split('/')[-1]
    print('Found site: ' + link.text)

while not next_button.get_attribute('disabled'):
    next_button.click()
    WebDriverWait(driver, 10).until(expected_conditions.staleness_of(titles[-1]))
    WebDriverWait(driver, 10).until(expected_conditions.presence_of_element_located((By.CSS_SELECTOR, 'td[headers="title"]')))
    # driver.switch_to_frame(iframe.get_attribute('id'))
    titles = driver.find_elements_by_css_selector('td[headers="title"]')
    for title in titles:
        link = title.find_element_by_tag_name('a')
        if link.text != 'My Workspace':
            site_links[filename_pattern.sub('_', link.text)] = link.get_attribute('href').split('/')[-1]
            print('Found site: ' + link.text)
    next_button = driver.find_element_by_name('eventSubmit_doList_next')

print('Site collection finished!  {} sites found.'.format(len(site_links.keys())))

driver.close()








def output_reader(proc, outq):
    lastread = 0
    out = b''
    while proc.poll() is None:
        try:
            a = proc.stdout.read()
            if a:
                lastread = time()
                out += a
            if out!=b'' and (out[-1]==b'\n' or out[-3:]==b'/> ' or time()-lastread>3):
                lines = out.decode('utf-8').split('\n')
                for line in lines:
                    # print('.....' + line)
                    outq.put(line)
                out = b''
        except ValueError:
            break

def wait_for(q, s):
    out = []
    while len(out) == 0 or out[-1][:len(s)] != s:
        out.append(q.get())
    return out

filepat = compile(r"""        (.+?) +[0-9]+ +[A-Za-z]{3} +[0-9]{1,2} +[0-9:]{3,5}""")
dirpat = compile(r"""Coll:   (.+?) +[0-9]+ +[A-Za-z]{3} +[0-9]{1,2} +[0-9]{4}""")

def process_directory(root, path):
    makedirs(path)
    proc.stdin.write('lcd "{}/{}"\n'.format(root, path).encode())
    proc.stdin.flush()
    wait_for(q, 'dav:/dav/')
    proc.stdin.write('ls "/dav/{}"\n'.format(path).encode())
    proc.stdin.flush()
    for line in wait_for(q, 'dav:/dav/'):
        if 'collection is empty' in line:
            return
        print(line)
        filematch = filepat.match(line)
        if filematch:
            print('file matched')
            proc.stdin.write('get "/dav/{}/{}"\n'.format(path, filematch.group(1)).encode())
            proc.stdin.flush()
            wait_for(q, 'dav:/dav/')
        else:
            dirmatch = dirpat.match(line)
            if dirmatch:
                print('directory matched')
                process_directory(root, path+'/'+dirmatch.group(1))
            else:
                print('*** not matched ***')


print('Starting to fetch files...')
numsites = len(site_links.keys())
currentnum = 0
with Popen([], executable='/usr/bin/cadaver', stdin=PIPE, stdout=PIPE, stderr=PIPE) as proc:
    fcntl(proc.stdout.fileno(), F_SETFL, O_NONBLOCK)
    # fcntl(proc.stderr.fileno(), F_SETFL, O_NONBLOCK)
    # fcntl(proc.stdin.fileno(), F_SETFL, O_NONBLOCK)

    q = Queue()
    t = Thread(target=output_reader, args=(proc, q))
    t.start()

    for external_name, internal_name in site_links.items():
        proc.stdin.write('open https://t-square.gatech.edu/dav/{}\n'.format(internal_name).encode())
        proc.stdin.flush()
        wait_for(q, 'dav:/dav/')

        root_dir = ''
        proc.stdin.write(b'lpwd\n')
        proc.stdin.flush()
        for line in wait_for(q, 'dav:/dav/'):
            if line[:17] == 'Local directory: ':
                root_dir = line[17:]

        process_directory(root_dir, internal_name)
        proc.stdin.write('lcd "{}"\n'.format(root_dir).encode())
        proc.stdin.flush()
        wait_for(q, 'dav:/dav/')
        rename(internal_name, external_name)
        currentnum += 1
        print('\n\n\n\n\nFinished {} sites of {}\n\n\n\n\n'.format(currentnum, numsites))
    proc.stdin.write('quit\n'.encode())
    proc.stdin.flush()



print('Finished!  Everything should be downloaded now.')