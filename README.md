# tsquare-fetcher

This is a utility to traverse the entirety of your t-square site and download all of the resources for each site that you're a member of.  It'll create directories for each site and download into them.  Note that this will take quite a while, since it downloads files one at a time (intentionally, so that you don't cause too much of a load on the servers).  Note that there's a very real possibility that someone will realize that you're doing this and may get upset that you're clogging things up!  Use at your own risk.

Right now, it only works on linux because of the cadaver dependency (used to actually fetch the files).  
## Dependencies:

- python3
- selenium
- chromium-chromedriver
- cadaver

Install with:

> sudo apt-get install python3 selenium chromium-chromedriver cadaver

## Usage

- Download the scripts and put them in a folder where you want the files to end up.
- Create a ~/.netrc file with the contents:
> Machine: t-square.gatech.edu
> Login: <username>
> Password: <password>
- Run tsquare-fetcher.py and get ready to wait.