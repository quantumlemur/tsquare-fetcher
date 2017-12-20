#!/usr/bin/python3

from fcntl import fcntl, F_SETFL
from math import floor
from os import O_NONBLOCK, makedirs, rename, stat, popen
from os.path import expanduser, exists
from queue import Queue
from re import compile
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from subprocess import Popen, PIPE
from threading import Thread
from time import time, sleep





debug = False




username = ''
password = ''


filename_pattern = compile('[^\w\-_\. /+\n)(,&]')
filepat = compile(r"""        (.+?) +([0-9]+) +[A-Za-z]{3} +[0-9]{1,2} +[0-9:]{3,5}""")
dirpat = compile(r"""Coll:   (.+?) +[0-9]+ +[A-Za-z]{3} +[0-9]{1,2} +[0-9]{4}""")

# read the login info from the .netrc file
with open(expanduser('~/.netrc'), 'r') as f:
    for line in f:
        if line[:5] == 'login':
            username = line.split()[1]
        if line[:8] == 'password':
            password = line.split()[1]



## Phase 1: Log in to tsquare and scrape the list of sites to download

# initialize the webdriver and start the tsquare login process
print('Trying to log in to tsquare... get out your phone and be ready to approve the two-factor auth!')
options = webdriver.ChromeOptions()
# options.add_argument('--headless')
driver = webdriver.Chrome(chrome_options=options)
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

site_links = []

# wait and find the worksite iframe
WebDriverWait(driver, 60).until(expected_conditions.presence_of_element_located((By.CSS_SELECTOR, 'iframe[title="Worksite Setup "]')))
iframe = driver.find_elements_by_css_selector('iframe[title="Worksite Setup "]')[0]
driver.switch_to_frame(iframe.get_attribute('id'))


# scrape the actual worksite links
WebDriverWait(driver, 10).until(expected_conditions.presence_of_element_located((By.NAME, 'eventSubmit_doList_next')))
next_button = driver.find_element_by_name('eventSubmit_doList_next')
titles = driver.find_elements_by_css_selector('td[headers="title"]')
for title in titles:
    link = title.find_element_by_tag_name('a')
    if link.text != 'My Workspace':
        site_links.append((filename_pattern.sub('_', link.text), link.get_attribute('href').split('/')[-1]))
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
            site_links.append((filename_pattern.sub('_', link.text), link.get_attribute('href').split('/')[-1]))
            print('Found site: ' + link.text)
    next_button = driver.find_element_by_name('eventSubmit_doList_next')

print('Site collection finished!  {} sites found.'.format(len(site_links)))

driver.close()



## Phase 2a:  downloading the files

def output_reader(proc, outq, output=''):
    global debug
    lastread = 0
    out = b''
    while proc.poll() is None:
        try:
            a = proc.stdout.read()
            if a:
                lastread = time()
                out += a
            if out != b'' and time() - lastread > 5:
                lines = out.decode('utf-8').split('\n')
                for line in lines:
                    print('     TIMEOUT: ' + line)
                    outq.put(line)
                out = b''
            elif out!=b'' and (out[-1]==b'\n' or out[-3:]==b'/> '):
                lines = out.decode('utf-8').split('\n')
                for line in lines:
                    if debug:
                        print('          ' + output + ' ' + line)
                    outq.put(line)
                out = b''
        except ValueError:
            break

def wait_for(q, s, output=False):
    out = []
    while len(out) == 0 or out[-1][:len(s)] != s:
        message = q.get()
        if output:
            print(message)
        out.append(message)
    return out


def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def time_fmt(seconds):
    seconds = int(seconds)
    s = seconds % 60
    m = (seconds - s) // 60 % 60
    h = (seconds - s - m*60) // 3600
    return '{0:0>2}:{1:0>2}:{2:0>2}'.format(h, m, s)


def progressBar(current, max, length):
    out = '['
    n = floor(current / max * length)
    return ('{0:#<%d}{1:.>%d}' % (n,length-n)).format('[', ']')


class CadaverDownloader:
    def __init__(self, filequeue):
        self.filequeue = filequeue
        self.messagequeue = Queue()
        self.currentsite = ''
        self.processedFiles = 0
        self.processedSize = 0
        self.startTime = time()
        self.proc = Popen([], executable='/usr/bin/cadaver', stdin=PIPE, stdout=PIPE, stderr=PIPE)
        fcntl(self.proc.stdout.fileno(), F_SETFL, O_NONBLOCK)
        self.t = Thread(target=output_reader, args=(self.proc, self.messagequeue, 'download'))
        self.t.start()
        self.d = Thread(target=self.downloader, args=(self.proc, self.messagequeue, self.filequeue))
        self.d.start()

    def downloader(self, proc, messagequeue, filequeue):
        while True:
            f = filequeue.get()
            if not f:
                proc.stdin.write('quit\n'.encode())
                proc.stdin.flush()
                sleep(1)
                proc.terminate()
                print('Done downloading files!')
                break
            else:
                self.downloadFile(proc, messagequeue, f)

    def downloadFile(self, proc, messagequeue, fileTuple):
        global totalsize
        global totalfiles
        root, internal_name, human_name, subdir, filename, filesize = fileTuple

        if internal_name != self.currentsite:
            proc.stdin.write('open https://t-square.gatech.edu/dav/{}\n'.format(internal_name).encode())
            proc.stdin.flush()
            wait_for(messagequeue, 'dav:/dav/')
        dirpath = "{}{}{}".format(root, human_name, subdir)
        if not exists(dirpath):
            makedirs(dirpath)
        filepath = "{}{}{}{}".format(root, human_name, subdir, filename)
        if not exists(filepath) or stat(filepath).st_size != filesize:
            proc.stdin.write('get "/dav/{}{}{}" "{}{}{}{}"\n'.format(internal_name, subdir, filename, root, human_name, subdir, filename).encode())
            proc.stdin.flush()
            # print('get "/dav/{}{}{}" "{}{}{}{}"\n'.format(internal_name, subdir, filematch.group(1), root, human_name, subdir, filematch.group(1)).encode())
            wait_for(messagequeue, 'dav:/dav/')
        self.processedFiles += 1
        self.processedSize += filesize
        elapsed = time() - self.startTime
        perFile = elapsed / self.processedFiles
        remaining = (totalfiles - self.processedFiles) * perFile
        # print(human_name + subdir + filename)
        print('Files: {} of {} | Size: {} of {} | Time: {} of {}  {}   '.format(self.processedFiles, totalfiles, sizeof_fmt(self.processedSize), sizeof_fmt(totalsize), time_fmt(elapsed), time_fmt(remaining), progressBar(self.processedFiles, totalfiles, 50)), end='\r')





## Phase 2b: collecting the list of files

filequeue = Queue()
totalsize = 0
totalfiles = 0
totalsites = 0

downloader = CadaverDownloader(filequeue)

def process_directory(root, internal_name, human_name, subdir=''):
    global totalsize
    global totalfiles
    fullpath = root + human_name + subdir
    # if not exists(fullpath):
    #     makedirs(fullpath)
    # print(human_name + subdir)
    # proc.stdin.write('lcd "{}/{}"'.format(root, path)).encode()
    # proc.stdin.flush()
    # wait_for(q, 'dav:/dav/')
    proc.stdin.write('ls "/dav/{}{}"\n'.format(internal_name, subdir).encode())
    proc.stdin.flush()
    for line in wait_for(q, 'dav:/dav/'):
        if 'collection is empty' in line:
            return
        # print(line)
        filematch = filepat.match(line)
        if filematch:
            # print('file matched:     ' + filematch.group(1))
            size = int(filematch.group(2))
            totalsize += size
            totalfiles += 1
            filequeue.put((root, internal_name, human_name, subdir, filematch.group(1), size))
        else:
            dirmatch = dirpat.match(line)
            if dirmatch:
                process_directory(root, internal_name, human_name, subdir+dirmatch.group(1)+'/')
            else:
                pass
                # print('*** not matched ***     ' + line)


print('Starting to fetch files...')
currentnum = 0
with Popen([], executable='/usr/bin/cadaver', stdin=PIPE, stdout=PIPE, stderr=PIPE) as proc:
    fcntl(proc.stdout.fileno(), F_SETFL, O_NONBLOCK)
    # fcntl(proc.stderr.fileno(), F_SETFL, O_NONBLOCK)
    # fcntl(proc.stdin.fileno(), F_SETFL, O_NONBLOCK)

    q = Queue()
    t = Thread(target=output_reader, args=(proc, q, 'file'))
    t.start()
    root_dir = ''
    proc.stdin.write(b'lpwd\n')
    proc.stdin.flush()
    for line in wait_for(q, 'Local'):
        if line[:17] == 'Local directory: ':
            root_dir = line[17:] + '/files/'
    print(root_dir)
    wait_for(q, 'dav:')

    for (external_name, internal_name) in site_links:
        # print('Starting download of ' + external_name)
        proc.stdin.write('open https://t-square.gatech.edu/dav/{}\n'.format(internal_name).encode())
        proc.stdin.flush()
        wait_for(q, 'dav:/dav/')

        process_directory(root_dir, internal_name+'/', filename_pattern.sub('_', external_name+'/'))
        proc.stdin.write('lcd "{}"\n'.format(root_dir).encode())
        proc.stdin.flush()
        wait_for(q, 'dav:/dav/')
        currentnum += 1
    proc.stdin.write('quit\n'.encode())
    proc.stdin.flush()




print('Done enumerating files!  Still downloading, though.')