DROP_WORTH_BUYING = -.05
AMOUNT_TO_INVEST_PER_PURCHASE = 7500
RAISE_WORTH_SELLING = 200.0 / AMOUNT_TO_INVEST_PER_PURCHASE # first value is raise in $ when to sell
MINIMUM_CASH = 20000
UPDATE_MIN_DELAY = 30

use_virtual_display = True
ignore_if_market_open = True
destructive = False # if True, will actually perform buy & sell operations

username = ''
password = ''

loginpage = 'https://accounts.marketwatch.com/login?target=http%3A%2F%2Fwww.marketwatch.com%2Fgame%2Fap-macro-4th-'
home = 'https://www.marketwatch.com/game/ap-macro-4th-/'

from selenium import webdriver
# set driver_path to '' if driver in system PATH
driver_path = ''
driver_type = webdriver.Firefox

reboot_after_run = False
