#!/usr/bin/python3

from fcntl import fcntl, F_SETFL
# from getpass import getpass
from os import O_NONBLOCK, makedirs
from queue import Queue
from re import compile
from subprocess import Popen, PIPE
from threading import Thread
from time import time

# raw_table = input('pasted table of sites: ')

sites = []

pattern = compile(r"""\t*<a href="https://t-square.gatech.edu/portal/site/(.*)" target="_top">""")
with open('notes.txt', 'r') as f:
    for line in f:
        match = pattern.search(line)
        if match:
            sites.append(match.group(1))


def output_reader(proc, outq):
    lastread = 0
    out = b''
    while proc.poll() is None:
        a = proc.stdout.read()
        if a:
            lastread = time()
            out += a
        if out!=b'' and (out[-1]==b'\n' or out[-3:]==b'/> ' or time()-lastread>3):
            lines = out.decode('utf-8').split('\n')
            for line in lines:
                print('=====' + line)
                outq.put(line)
            out = b''

def wait_for(q, s):
    out = []
    while len(out) == 0 or out[-1][:len(s)] != s:
        out.append(q.get())
    return out

filepat = compile(r"""        (.+?) +[0-9]+  [A-Za-z]{3} [0-9]{1,2} [0-9:]{3,5}""")
dirpat = compile(r"""Coll:   (.+?) +[0-9]+  [A-Za-z]{3} [0-9]{1,2}  [0-9]{4}""")

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
        filematch = filepat.match(line)
        if filematch:
            proc.stdin.write('get "/dav/{}/{}"\n'.format(path, filematch.group(1)).encode())
            proc.stdin.flush()
            wait_for(q, 'dav:/dav/')
        else:
            dirmatch = dirpat.match(line)
            if dirmatch:
                process_directory(root, path+'/'+dirmatch.group(1))



s = 'ef9c11c4-3a66-484d-a2cd-746cf130c774'


with Popen([], executable='/usr/bin/cadaver', stdin=PIPE, stdout=PIPE, stderr=PIPE) as proc:
    fcntl(proc.stdout.fileno(), F_SETFL, O_NONBLOCK)
    # fcntl(proc.stderr.fileno(), F_SETFL, O_NONBLOCK)
    # fcntl(proc.stdin.fileno(), F_SETFL, O_NONBLOCK)

    q = Queue()
    t = Thread(target=output_reader, args=(proc, q))
    t.start()


    proc.stdin.write('open https://t-square.gatech.edu/dav/{}\n'.format(s).encode())
    proc.stdin.flush()
    wait_for(q, 'dav:/dav/')

    root_dir = ''
    proc.stdin.write(b'lpwd\n')
    proc.stdin.flush()
    for line in wait_for(q, 'dav:/dav/'):
        if line[:17] == 'Local directory: ':
            root_dir = line[17:]

    process_directory(root_dir, s)




# print('test')






# from fcntl import fcntl, F_SETFL
# from getpass import getpass
# from os import O_NONBLOCK
# from re import compile
# from subprocess import Popen, PIPE
# proc = Popen([], executable='/mnt/c/Users/mr234/Dropbox (Personal)/Documents/Projects/tsquare-fetcher/echo.sh', stdin=PIPE, stdout=PIPE, stderr=PIPE)
# fcntl(proc.stdout.fileno(), F_SETFL, O_NONBLOCK)
# fcntl(proc.stderr.fileno(), F_SETFL, O_NONBLOCK)
# fcntl(proc.stdin.fileno(), F_SETFL, O_NONBLOCK)