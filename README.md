# tsquare-fetcher

This is a utility to traverse the entirety of your t-square site and download all of the resources for each site that you're a member of.  Note that this will take a while, since it downloads files one at a time (intentionally, so that you don't cause too much of a load on the servers).  I don't know how much IT will mind you doing mass downloads, and there is a possibility you'll get flagged or throttled.  Use at your own risk.

Can be stopped and restarted at any time, and it'll resume from where it left off and re-download any missing or incomplete files.

Linux only, because of the cadaver dependency (used to actually fetch the files).

## Dependencies:

- python3
- selenium
- cadaver
- chromedriver

Install linux dependencies with:

> sudo apt-get install python3 selenium cadaver chromium-chromedriver

I set this up on WSL in win10, so I followed the instructions at http://ngauthier.com/2017/09/rails-system-tests-with-headless-chrome-on-windows-bash-wsl.html to set up chromedriver in Windows to be able to interact with the scripts.  Basically just download it and add it to your path, is all.

Also, you need to have a phone that allows push notifications enabled for DUO two-factor authentication.

## Usage

- Download tsquare-fetcher.py and put it in a folder where you want the files to end up.
- Create a ~/.netrc file with the contents:
```
Machine: t-square.gatech.edu
Login: <username>
Password: <password>
```
- Run tsquare-fetcher.py and get ready to wait.