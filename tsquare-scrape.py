#!/usr/bin/python3

import time

from os.path import expanduser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait


username = ''
password = ''

# read the login info from the .netrc file
with open(expanduser('~/.netrc'), 'r') as f:
    for line in f:
        if line[:5] == 'login':
            username = line.split()[1]
        if line[:8] == 'password':
            password = line.split()[1]



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

# login?
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
assert 'Worksite Setup' in driver.page_source















# driver.close()

