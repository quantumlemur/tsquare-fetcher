# tsquare-fetcher

This is a utility to traverse the entirety of your t-square site and download all of the resources for each site that you're a member of.  It'll create directories for each site and download into them.  Note that this will take quite a while, since it downloads files one at a time (intentionally, so that you don't cause too much of a load on the servers).  Note that there's a very real possibility that someone will realize that you're doing this and may get upset that you're clogging things up!  Use at your own risk.

Right now, it only works on linux because of the cadaver dependency (used to actually fetch the files).

Occasionally, it will get hung up on a file.  I'm not sure why, but if it seems to be stuck (check and make sure it's not just busy downloading a large file), then you can cancel it with ctrl-c, and restart it to let it continue.

## Dependencies:

- python3
- selenium
- cadaver
- chromedriver

Install linux dependencies with:

> sudo apt-get install python3 selenium cadaver chromium-chromedriver

I set this up on WSL in win10, so I followed the instructions at http://ngauthier.com/2017/09/rails-system-tests-with-headless-chrome-on-windows-bash-wsl.html to set up chromedriver in Windows to be able to interact with my scripts.  This is probably easier if you stick to a native linux instead of doing this, but it does work.  Basically just download it and add it to your path, is all.

Also, you need to have a phone that allows push notifications enabled for DUO two-factor authentication.

## Usage

- Download the scripts and put them in a folder where you want the files to end up.
- Create a ~/.netrc file with the contents:
```
Machine: t-square.gatech.edu
Login: <username>
Password: <password>
```
- Run tsquare-fetcher.py and get ready to wait.