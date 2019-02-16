from time import sleep
import json
import requests
import datetime
import traceback
from preferences import *
import os
import csv

if use_virtual_display:
    from pyvirtualdisplay import Display
    display = Display(visible=0, size=(1000, 800))
    display.start()

# helper functions
def read_file(path):
    file = open(path)
    text = file.read()
    file.close()
    return text

def login():
    print('logging in')
    driver.get(loginpage)

    by_name('username').send_keys(username)
    by_name('password').send_keys(password)
    by_class('basic-login-submit').click()
    sleep(10) # need to wait to make sure login properly works, 10 might be excessive

def buy_stock(name, amount):
    print('buying ' + str(amount) + '$ worth of '+ name)
    driver.get(home)
    
    # search interfeace
    by_class('j-miniTrade').send_keys(name)
    price = float(by_class('t-price').text)
    print('the price of ' + name + ' is:' + str(price))
    by_class('t-trade').click()

    # buy interface
    shares = int(amount / price)
    print('this equates to ' + str(shares) + ' shares')
    num_shares_elem = by_class('j-number-shares')
    num_shares_elem.clear()
    num_shares_elem.send_keys(shares)

    if destructive:
        by_class('j-submit').click()

def clean(text, num=False):
    result = str(text).replace('$', '').replace(',', '').replace('%', '')
    if num:
        return float(result)
    else:
        return result

def get_stocks_info(names): # batch request
    link = 'https://api.iextrading.com/1.0/stock/market/batch?symbols=' + ','.join(names) + '&types=quote'
    
    return json.loads(requests.get(link).content)

def get_stock_info(name):
    print('getting stock info for ' + name)
    return json.loads(requests.get('https://api.iextrading.com/1.0/stock/' + name + '/quote').content)

def get_overview_stats():
    print('getting overview stats about my profile')
    driver.get(home)

    info = {}
    
    info['rank'] = int(by_class('rank__number ').text)
    
    elems = multiple_by_class('kv__primary')
    order = ['net worth', 'todays gains', 'overall gains', 'overall returns', 'cash remaining', 'buying power', 'short reserve', 'cash borrowed']

    for i, item in enumerate(order):
        info[item] = clean(elems[i].text, True)
    
    return info

def get_sp_stock_data():
    print('getting current stock information for s&p 500 stocks')
    # get s&p stock list
    stock_info = []

    
    f = open('stock_list.txt')
    
    names = []
    for line in f:
        names.append(line[:len(line) - 2]) # remove excess on ending
    f.close()

    for i in range(5): # need to repeat 5 times because batch size is 100 and there are 500 s&p stocks
        cur_names = names[100*i:100*(i + 1)]
        data = get_stocks_info(cur_names)

        for name in cur_names:
            stock_info.append((name, data[name]['quote']))

    print('finished getting all stock info for s&p 500')

    return stock_info

def auto_buy():
    print('auto purchasing all stocks that have gone down by ' + str(DROP_WORTH_BUYING) + '%')
    
    current = get_portfolio_stocks() # don't want to buy stocks we currently already have
    
    sp = get_sp_stock_data()
    sp.sort(key=lambda x: x[1]['changePercent'])
    
    for stock in sp:
        name, change = stock[0], stock[1]['changePercent']
        
        cash_remaining = get_overview_stats()['cash remaining']
        
        if change <= DROP_WORTH_BUYING and cash_remaining - AMOUNT_TO_INVEST_PER_PURCHASE >= MINIMUM_CASH and name not in current:
            print('buying '+ name + ' that dropped ' + str(change*100) + '%')
            buy_stock(name, AMOUNT_TO_INVEST_PER_PURCHASE)
        else:
            print('reached point of stopping auto buy')
            break

def get_transaction_history():
    print('obtaining transaction history for previously purchased stocks')
    driver.get(home + 'portfolio')
    
    history = {}
    
    headers = ['Symbol', 'order time', 'transaction time', 'type', 'amount', 'price']
    is_num = [False, False, False, False, True, True]
    
    def get_page():
        table = by_class('ranking')
        trs = table.find_elements_by_class_name('table__row')[1:] # first table row is headers
        
        for row in trs:
            tds = row.find_elements_by_class_name('table__cell')
            info = {}
            for i, td in enumerate(tds):
                info[headers[i]] = clean(td.text, is_num[i])

            name = info['Symbol']
            
            if name not in history and info['type'] == 'Buy':
                history[name] = info

    transactions_title = multiple_by_class('title')[5]
    driver.execute_script("arguments[0].scrollIntoView();", transactions_title)
    sleep(10)
    
    while True: # go through every page (table only shows 10 at a time)
        get_page()
        next = multiple_by_class('j-next')[1] #.find_element_by_tag_name('i')
        if next.get_attribute('data-is-disabled') == 'false': # more to go
            next.click()
            sleep(3)
        else:
            break

    return history

#def get_transaction_history_new(): # gets transaction history including only most recent buy for each stock if multiple entries appear
#    print('getting transaction history')
#    sleep(5)
#    driver.get(home + 'download?view=transactions&count=100000')
#    sleep(5)
#
#    address = downloads_folder + 'Portfolio Transactions - ' + market_watch_name + '.csv'
#
#    result = {}
#
#    with open(address) as csvfile:
#        reader = csv.DictReader(csvfile)
#        for row in reader:
#            name = row['Symbol']
#
#            if name not in result and row['Type'] == 'Buy':
#                row['Price'] = float(row['Price'].replace('$', ''))
#                result[name] = row
#
#    csvfile.close()
#
#    # delete the file
#    os.remove(address)
#
#    return result

def get_portfolio_stocks():
    print('checking prices of current stocks in portfolio')
    driver.get(home + 'portfolio')
    table = by_class('holdings')
    trs = table.find_elements_by_class_name('table__row')[1:] # first table row is headers
    
    portfolio = {}
    
    headers = ['name', 'shares', 'price', 'change', 'change %', 'value', 'value change', 'value change %']
    
    for row in trs:
        tds = row.find_elements_by_class_name('table__cell')
        info = {}
        
        name = clean(tds[1].find_element_by_class_name('symbol').text)
        info['shares'] = int(clean(tds[1].find_element_by_class_name('text').text.replace(' SHARES', ''), True))
        info['price'] = clean(tds[3].find_element_by_class_name('primary').text, True)
        info['price change'] = clean(tds[3].find_element_by_class_name('point').text, True)
        info['price change %'] = clean(tds[3].find_element_by_class_name('percent').text, True)
        info['value'] = clean(tds[4].find_element_by_class_name('primary').text, True)
        info['value change'] = clean(tds[4].find_element_by_class_name('point').text, True)
        info['value change %'] = clean(tds[4].find_element_by_class_name('percent').text, True)
        
        portfolio[name] = info
    
    return portfolio

def auto_sell():
    print('auto selling stocks that have risen by ' + str(RAISE_WORTH_SELLING * 100.0) + '% since purchase time')
    history = get_transaction_history()
    current = get_portfolio_stocks()
    
    for key in current:
        old_price = history[key]['price']
        new_price = current[key]['price']
        
        change = (new_price - old_price) / old_price
        
        if change > RAISE_WORTH_SELLING and key != 'VGSH': # have to keep bond
            shares = current[key]['shares']
            print('price of ' + key + ' rose by ' + str(change * 100) + '% from ' + str(old_price) + ' to ' + str(new_price) + ' so selling ' + str(shares) + ' shares')
            sell(key, shares)

def sell(name, shares):
    print('selling ' + str(shares) + ' of ' + name)
    driver.get(home + 'portfolio')

    # search interfeace
    by_class('j-miniTrade').send_keys(name)
    price = float(by_class('t-price').text)
    by_class('t-trade').click()

    # click sell
    header = by_class('lightbox__header')
    li = header.find_elements_by_class_name('radio__item')[2]
    label = li.find_element_by_class_name('label')
    label.click()
    
    # sell interface
    num_shares_elem = by_class('j-number-shares')
    num_shares_elem.clear()
    num_shares_elem.send_keys(shares)
    
    if destructive:
        by_class('j-submit').click()

def safe_exit():
    try:
        driver.close()
        driver.quit()
        print('sucessfully closed driver')
    except Exception:
        print('error when closing driver')
        pass
        
    try:
        display.stop()
        print('stopped display')
    except Exception:
        print('error stopping display')
        pass

def is_market_open():
    now = datetime.datetime.now()
    hour, minute = now.hour, now.minute

    return 6.5 <= hour + (minute / 60.0) and hour <= 12.5

def download_file_test():
    print('downloading sample file')
    driver.get('https://www.marketwatch.com/game/ap-macro-4th-/download?view=transactions&count=100000')
#    driver.get(home + 'portfolio')

#    items = multiple_by_class('download__data')[2].click()
    sleep(30)
#    print(len(items))

while True:
    f = open("runhistory.txt", "w")
    f.write(str(datetime.datetime.now()) + '\n')
    f.close()

    try:
        if is_market_open() or ignore_if_market_open: # if stock market open
            print('market is open or state ignored by preference, running algorithm')
            
#            chromeOptions = webdriver.ChromeOptions()
#            print(downloads_folder)
#            prefs = {"download.default_directory" : downloads_folder}
#            chromeOptions.add_experimental_option("prefs",prefs)

            # setup driver
            if driver_path != '':
                driver = driver_type(driver_path)
            else:
                driver = driver_type()
        
#            fp.set_preference("browser.download.folderList",2)
#            fp.set_preference("browser.download.manager.showWhenStarting",False)
#            fp.set_preference("browser.download.dir", os.getcwd())
#            fp.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/octet-stream")

            driver.implicitly_wait(100)
            
            by_name = driver.find_element_by_name
            by_class = driver.find_element_by_class_name
            multiple_by_class = driver.find_elements_by_class_name
            
            # MAIN OPERATIONS
            login()
#            buy_stock(' AAPL', 10000)
#            print(get_transaction_history())
#            print(get_transaction_history_old())
#            download_file_test()
            auto_buy()
            auto_sell()

            safe_exit()
        else:
            print('market is closed, algorithm will NOT run')

        print('sleeping for ' + str(UPDATE_MIN_DELAY) + ' minutes')
        sleep(UPDATE_MIN_DELAY * 60) # sleep 30 minutes

    except Exception:
        print("EXCEPTION!!!")
        traceback.print_exc()
        
        f = open("errors.txt", "a")
        f.write(str(datetime.datetime.now()) + '\n' + traceback.format_exc() + '\n')
        f.close()
        
        safe_exit()
        print('waiting after error occurred')
        sleep(60)

        pass

    if reboot_after_run:
        os.system('sudo reboot now')
