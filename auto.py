from selenium import webdriver
from time import sleep
import json
import requests
import datetime

# constants
DROP_WORTH_BUYING = -.05
AMOUNT_TO_INVEST_PER_PURCHASE = 7500
RAISE_WORTH_SELLING = 200.0 / AMOUNT_TO_INVEST_PER_PURCHASE # first value is raise in $ when to sell
MINIMUM_CASH = 20000
UPDATE_MIN_DELAY = 30

destructive = True # if True, will actually perform buy & sell operations

# helper functions
def read_file(path):
    file = open(path)
    text = file.read()
    file.close()
    return text

home = read_file('gamehomepage.txt')
loginpage = read_file('loginpage.txt')

def login():
    print('logging in')
    driver.get(loginpage)

    by_name('username').send_keys(read_file('username.txt'))
    by_name('password').send_keys(read_file('password.txt'))
    by_class('basic-login-submit').click()
    sleep(3)

def buy_stock(name, amount):
    print('buying ' + str(amount) + '$ worth of '+ name)
    driver.get(home)
    sleep(5)
    
    # search interfeace
    by_class('j-miniTrade').send_keys(name)
    sleep(5)
    price = float(by_class('t-price').text)
    print('the price of ' + name + ' is:' + str(price))
    by_class('t-trade').click()
    sleep(5)

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


def get_stock_info(name):
    print('getting stock info for ' + name)
    return json.loads(requests.get('https://api.iextrading.com/1.0/stock/' + name + '/quote').content)

def get_overview_stats():
    print('getting overview stats about my profile')
    driver.get(home)
    sleep(5)
    
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

    i = 1
    f = open('stock_list.txt')
    for line in f:
#        if i > 30:
#            break

        if i % 10 == 0:
            print(str(i/500.0*100) + '% complete getting stock info')
        i += 1
        
        name = line[:len(line) - 2]
        stock_info.append((name, get_stock_info(name)))

    print('finished getting all stock info for s&p 500')
    return stock_info

def auto_buy():
    print('auto purchasing all stocks that have gone down by ' + str(DROP_WORTH_BUYING) + '%')
    
    current = get_portfolio_stocks()
    
    sp = get_sp_stock_data()
    sp.sort(key=lambda x: x[1]['changePercent'])
    
    for stock in sp:
        name, change = stock[0], stock[1]['changePercent']
        
        cash_remaining = get_overview_stats()['cash remaining']
        
        if change <= DROP_WORTH_BUYING and cash_remaining - AMOUNT_TO_INVEST_PER_PURCHASE >= MINIMUM_CASH:
            print('buying', name, 'that dropped', change)
            buy_stock(name, AMOUNT_TO_INVEST_PER_PURCHASE)
        else:
            print('reached point of stopping auto buy')
            break

def get_transaction_history():
    print('obtaining transaction history for previously purchased stocks')
    driver.get(home + 'portfolio')
    
    table = by_class('ranking')
    trs = table.find_elements_by_class_name('table__row')[1:] # first table row is headers
    
    history = []
    
    headers = ['name', 'order time', 'transaction time', 'type', 'amount', 'purchase price']
    is_num = [False, False, False, False, True, True]
    
    for row in trs:
        tds = row.find_elements_by_class_name('table__cell')
        info = {}
        for i, td in enumerate(tds):
            info[headers[i]] = clean(td.text, is_num[i])

        history.append(info)
    
    return history

def get_portfolio_stocks():
    print('checking pries of current stocks in portfolio')
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
        for hist in history:
            if hist['name'] == key:
                old_price = hist['purchase price']
                new_price = current[key]['price']
                
                change = (new_price - old_price) / old_price
                
                if change > RAISE_WORTH_SELLING and key != 'VGSH': # have to keep bond
                    shares = current[key]['shares']
                    print('price of ' + key + ' rose by ' + str(change * 100) + '% from ' + str(old_price) + ' to ' + str(new_price) + ' so selling ' + str(shares) + ' shares')
                    sell(key, shares)

def sell(name, shares):
    print('selling ' + str(shares) + ' of ' + name)
    driver.get(home + 'portfolio')
    sleep(3)
    
    # search interfeace
    by_class('j-miniTrade').send_keys(name)
    sleep(3)
    price = float(by_class('t-price').text)
    by_class('t-trade').click()
    sleep(2)
    
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

while True:
    try:
        hour = datetime.datetime.now().hour
        
        if hour >= 10 and hour <= 15: # if stock market open
            print('market is open, running algorithm')
            
            # open driver
            driver = webdriver.Chrome('./chromedriver')
            
            # shortcut bindings
            by_name = driver.find_element_by_name
            by_class = driver.find_element_by_class_name
            multiple_by_class = driver.find_elements_by_class_name
            
            # MAIN OPERATIONS
            login()
            auto_buy()
            auto_sell()

            driver.close()
        else:
            print('market is closed, algorithm will NOT run')

        print('sleeping for ' + str(UPDATE_MIN_DELAY) + ' minutes')
        sleep(UPDATE_MIN_DELAY * 60) # sleep 30 minutes

    except:
        pass
