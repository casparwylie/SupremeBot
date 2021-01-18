"""
SupremeBot v1.0
"""
import dataclasses
import enum
import json
import os
import queue
import requests
import sys
import threading
import time
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.webdriver.chrome.options import Options, DesiredCapabilities
from selenium.webdriver.support.ui import Select

#################
#### GENERAL ####
#################
_V = 1.0
_MONITOR_INTERVAL = 1
_TESTING = True
_DEFAULT_PERCHASES_PER_PRODUCT = 1
_DEFAULT_DRIVER_POOL_SIZE = 1
_ATB_WAIT_TIME = 0.1
_SECONDS_ROUND = 3

################
### SELENIUM ###
################
_DRIVER_PATH = './chromedriver'

# TODO: consider proxies
"""
PROXY = '208.80.28.208:8080'
PROXY = '132.145.18.53:80'
PROXY = '197.220.109.222:80'
PROXY = '18.135.32.174:80'
DesiredCapabilities.CHROME['proxy'] = {
    "httpProxy": PROXY,
    "ftpProxy": PROXY,
    "sslProxy": PROXY,
    "proxyType": "MANUAL",
}
"""
driver_options = Options()

if not _TESTING:
  driver_options.add_argument('--headless')

##############
#### DATA ####
##############
_SAVED_DATA_FILENAME = '.saved.json'
_DEFAULT_TEMPLATE = {'users': []}

##############
#### MISC ####
##############
_NL = lambda count: count * '\n'

#################
#### SUPREME ####
#################

# URLS
_BASE_DOMAIN = 'www.supremenewyork.com'
_SCHEME = 'https'
_BASE_URL = f'{_SCHEME}://{_BASE_DOMAIN}' + '/{path}'
_LISTING_URL = f'{_SCHEME}://{_BASE_DOMAIN}' + '/shop/all/{category}'
_CHECKOUT_PART = 'checkout'
_CHECKOUT_URL = _BASE_URL.format(path=_CHECKOUT_PART)

# Web scraping
_LISTING_ITEM_CLASSNAME = 'inner-article'
_PRODUCT_NAME_CLASSNAME = 'protect'
_PRODUCT_SOLD_OUT_CLASSNAME = 'sold_out_tag'
_ATB_OPTION_XPATH = '//input[@name="commit"]'
_ATB_OPT_KEYWORD = 'add'
_CHECKOUT_OPTION_XPATH = '//a[@class="button checkout"]'
_TOTAL_BUY_XPATH = '//strong[@id="total"]'
_CO_SUBMIT_XPATH = '//input[@class="button checkout"]'

_CO_FIELD_ID_FULLNAME ='order_billing_name'
_CO_FIELD_ID_EMAIL ='order_email'
_CO_FIELD_ID_TEL = 'order_tel'
_CO_FIELD_ID_ADDR_1 = 'bo'
_CO_FIELD_ID_ADDR_2 = 'oba3'
_CO_FIELD_ID_CITY = 'order_billing_city'
_CO_FIELD_ID_POSTCODE = 'order_billing_zip'
_CO_FIELD_ID_COUNTRY = 'order_billing_country'
_CO_FIELD_ID_CARD_TYPE = 'credit_card_type'
_CO_FIELD_ID_CARD_NUM = 'cnb'
_CO_FIELD_ID_CARD_MONTH = 'credit_card_month'
_CO_FIELD_ID_CARD_YEAR = 'credit_card_year'
_CO_FIELD_ID_CARD_CVV = 'vval'
_CO_FIELD_CLASS_TERMS = 'has-checkbox'

# Values must match User attribute names
_USER_FIELD_INPUT_MAP = {
  _CO_FIELD_ID_FULLNAME: 'fullname',
  _CO_FIELD_ID_EMAIL: 'email',
  _CO_FIELD_ID_TEL: 'tel',
  _CO_FIELD_ID_ADDR_1: 'address_1',
  _CO_FIELD_ID_ADDR_2: 'address_2',
  _CO_FIELD_ID_CITY: 'city',
  _CO_FIELD_ID_POSTCODE: 'postcode',
  _CO_FIELD_ID_COUNTRY: 'country',
  _CO_FIELD_ID_CARD_TYPE: 'payment_method',
  _CO_FIELD_ID_CARD_NUM: 'card_number',
  _CO_FIELD_ID_CARD_MONTH: 'card_expire_month',
  _CO_FIELD_ID_CARD_YEAR: 'card_expire_year',
  _CO_FIELD_ID_CARD_CVV: 'cvv',
}

# Other
_CURRENCY = '£'

###########################
### META HELPER CLASSES ###
###########################

class Enum(enum.Enum):

  @classmethod
  @property
  def show_values(cls):
    joined = '\', \''.join(cls.values)
    return f'\'{joined}\''

  @classmethod
  @property
  def values(cls):
    return [category.value for category in cls]

  @classmethod
  def ask(cls):
    val = None
    while val not in cls.values:
      val = input(f'Enter a {cls.__display__} (one of {cls.show_values}): ')
    return cls(val)

class LoadableDataclassMixin:

  @classmethod
  def load(cls, data):
    obj = cls(**data)
    fields = obj.__annotations__
    for field, f_type in fields.items():
      if type(f_type) is enum.EnumMeta:
        setattr(obj, field, f_type(getattr(obj, field)))
    return obj


class CustomJsonEncoder(json.JSONEncoder):
  def default(self, obj):
    if isinstance(obj, Enum):
      return obj.value
    else:
      return super().default(self, obj)


def intput(message):
  val = ''
  while not val.isdigit():
    val = input(message)
  return int(val)


def tprint(message):
  if _TESTING:
    print(f'{_NL(1)}[INFO] {message}')


def secs(value):
  return f'{round(value, _SECONDS_ROUND)}s'


#############
### ENUMS ###
#############

class ProductCategory(Enum):
  __display__ = 'product category'

  JACKETS = 'jackets'
  ACCESSORIES = 'accessories'
  SALES = 'sale'


class PaymentMethod(Enum):
  __display__ = 'payment method'

  CREDIT_CARD = 'Credit Card'
  PAYPAL = 'Paypal' # Unsupported

class Country(Enum):

  __display__ = 'country'

  UK = 'UK'
  NORTHENIRELAND = 'UK (N. IRELAND)'
  AUSTRIA = 'AUSTRIA'
  BELARUS = 'BELARUS'
  BELGIUM = 'BELGIUM'
  BULGARIA = 'BULGARIA'
  CROATIA = 'CROATIA'
  CYPRUS = 'CYPRUS'
  CZECHREPUBLIC = 'CZECH REPUBLIC'
  DENMARK = 'DENMARK'
  ESTONIA = 'ESTONIA'
  FINLAND = 'FINLAND'
  FRANCE = 'FRANCE'
  GERMANY = 'GERMANY'
  GREECE = 'GREECE'
  HUNGARY = 'HUNGARY'
  ICELAND = 'ICELAND'
  IRELAND = 'IRELAND'
  ITALY = 'ITALY'
  LATVIA = 'LATVIA'
  LITHUANIA = 'LITHUANIA'
  LUXEMBOURGi = 'LUXEMBOURG'
  MALTA = 'MALTA'
  MONACO = 'MONACO'
  NETHERLANDS = 'NETHERLANDS'
  NORWAY = 'NORWAY'
  POLAND = 'POLAND'
  PORTUGAL = 'PORTUGAL'
  ROMANIA = 'ROMANIA'
  RUSSIA = 'RUSSIA'
  SLOVAKIA = 'SLOVAKIA'
  SLOVENIA = 'SLOVENIA'
  SPAIN = 'SPAIN'
  SWEDEN = 'SWEDEN'
  SWITZERLAND = 'SWITZERLAND'
  TURKEY = 'TURKEY'


class PurchaseTaskStatus(Enum):
  NOTSET = 0
  READY = 1
  RUNNING = 2
  COMPLETE = 3
  FAILED = 4
  CANCELLED = 5


####################
### DATA CLASSES ###
####################

@dataclasses.dataclass
class Product:
  name: str
  pid: str
  url: str
  colour: str
  in_stock: bool

  @property
  def full_name(self):
    return f'{self.name} {self.colour}'

  def __str__(self):
    return f'{self.pid}<{self.name}>({self.colour})'

  def __eq__(self, other):
    return self.name == self.name

@dataclasses.dataclass
class User(LoadableDataclassMixin):
  ident: str = ''
  fullname: str = ''
  email: str = ''
  tel: str = ''
  address_1: str = ''
  address_2: str = ''
  city: str = ''
  postcode: str = ''
  country: Country = ''
  payment_method: PaymentMethod = ''
  card_expire_month: str = ''
  card_expire_year: str = ''
  cvv: str = ''
  card_number: str = ''

  def __str__(self):
    return f'{self.ident}<{self.fullname}>'

  def populate(self):
    self.ident = input('Enter username: ')
    self.fullname = input('Enter fullname: ')
    self.email = input('Enter email: ')
    self.tel = input('Enter telephone: ')
    self.address_1 = input('Enter address 1: ')
    self.address_2 = input('Enter address 2: ')
    self.city = input('Enter city: ')
    self.postcode = input('Enter postcode: ')
    self.country = Country.ask()
    self.payment_method = PaymentMethod.ask()
    self.card_expire_month = input('Enter card expiry month (00-12): ')
    if len(self.card_expire_month) == 1:
      self.card_expire_month = f'0{self.card_expire_month}'
    self.card_expire_year = input('Enter card expiry year (2020): ')
    self.cvv = input('Enter card CVV (123): ')
    self.card_number = input('Enter card number (1234123412341234): ')
    return self

  def save(self):
    data = get_saved_data()
    data['users'].append(dataclasses.asdict(self))
    save_data(data)
    return self

  @classmethod
  def new(cls):
    print('Making new user...')
    return cls().populate().save()


@dataclasses.dataclass
class Options(LoadableDataclassMixin):
  keywords: list[str]
  category: ProductCategory
  budget: int
  user: User

  def __str__(self):
    return (f'Keywords: {", ".join(self.keywords)}{_NL(1)}'
            f'Category: {self.category.value.capitalize()}{_NL(1)}'
            f'My budget: {_CURRENCY}{self.budget}{_NL(1)}'
            f'User: {self.user.ident}')


####################
### TEST RELATED ###
####################

_TEST_USER = User(
  ident='test',
  fullname='Test User',
  email='test@user.com',
  tel='1234567890',
  address_1='1, Test location',
  city='Test',
  postcode='ABC 123',
  country=Country.GREECE,
  payment_method=PaymentMethod.CREDIT_CARD,
  card_expire_month='01',
  card_expire_year='2023',
  cvv='123',
  card_number='5355123412341234')

_TEST_OPTIONS = Options(
  keywords=['tagless', 'tees'],
  category=ProductCategory.ACCESSORIES,
  budget=1000,
  user=_TEST_USER)

class MockDriver:
  def quit(self, *args, **kwargs):
    pass

  def get(self, *args, **kwargs):
    time.sleep(5)


##################
### EXCEPTIONS ###
##################

# Errors
class ATBNotFoundError(Exception):
  ...


class CannotFillCheckoutError(Exception):
  ...


class UserFieldInputMappingError(AttributeError):
  ...


# General
class BugdetMetException(Exception):
  ...


##############
#### MAIN ####
##############

def save_data(data):
  with open(_SAVED_DATA_FILENAME, 'w') as out:
    json.dump(data, out, cls=CustomJsonEncoder)


def get_saved_data():
  if not os.path.exists(_SAVED_DATA_FILENAME):
    with open(_SAVED_DATA_FILENAME, 'w') as out:
      json.dump(_DEFAULT_TEMPLATE, out)
  with open(_SAVED_DATA_FILENAME) as data:
    return json.load(data)


def get_user():
  users = [User.load(user) for user in get_saved_data()['users']]
  if not users:
    return User.new()
  else:
    print(f'Choose a user...{_NL(1)}')
    for index, user in enumerate(users):
      print(f'{index + 1}: {user}')
    print()
    num = input('[Enter the number] >>> ')
    if not num:
      print(f'(Not from above, making new user...){_NL(2)}')
      return User.new()
    return users[int(num) - 1]

def collection_options():
  if _TESTING:
    print('[TEST MODE] Skipping questions...')
    return _TEST_OPTIONS
  return Options(
    keywords=input('Enter product keywords: ').split(','),
    category=ProductCategory.ask(),
    budget=intput(f'Enter your budget / spending limit in {_CURRENCY}: '),
    user=get_user())


def get_page_content(url):
  response = requests.get(url)
  return bs(response.content, 'html.parser')


def get_products(listing_page_url, options):

  listing_content = get_page_content(listing_page_url)
  elements = listing_content.find_all(
    'div', {'class': _LISTING_ITEM_CLASSNAME})
  for element in elements:
    url = _BASE_URL.format(path=element.find('a').get('href'))
    name = ''.join(element.find('h1').find('a').strings)
    colour = ''.join(element.find('p').find('a').strings)
    pid = element.find('img').get('src', '').split('/')[-3]
    in_stock = not element.find('div',
      {'class': _PRODUCT_SOLD_OUT_CLASSNAME})
    if in_stock:
      yield Product(
        pid=pid,
        name=name,
        colour=colour,
        url=url,
        in_stock=in_stock)


def search_products(products, keywords):
  results = []
  for keyword in keywords:
    for product in products:
      if keyword.lower() in product.full_name.lower() and product not in results:
        results.append(product)
  return results


def check_already_released(products, options):
  wanted_products = search_products(list(products), options.keywords)
  if wanted_products:
    print('The following products are already available on the site:')
    print(f'{_NL(1)}'.join(str(product) for product in wanted_products))
    print(f'{_NL(1)}Would you like to continue / buy these or start over?')
    if input('>>> continue/quit: ') != 'continue':
      exit()


class PurchaseManager:

  tasks = []
  complete_tasks = []
  spent = 0

  def __init__(self, options, purchase_per_product=_DEFAULT_PERCHASES_PER_PRODUCT,
                     driver_pool_size=_DEFAULT_DRIVER_POOL_SIZE):
    self.budget = options.budget
    self.user = options.user
    self.purchase_per_product = purchase_per_product
    self.driver_pool_size = driver_pool_size
    self.initialize_drivers()

  def initialize_drivers(self):
    self.drivers = queue.Queue()
    for _ in range(self.driver_pool_size):
      tprint('Initializing driver...')
      start_time = time.time()
      self.drivers.put(
        webdriver.Chrome(_DRIVER_PATH, options=driver_options))
      tprint(f'Done. Took {secs(time.time() - start_time)}.')

  def add_task(self, task):
    self.tasks.append(task)
    return task

  def start(self, products):
    tprint('Starting purchase manager.')
    for p_group_id, product in enumerate(products):
      tprint('Starting new purchase group.')
      for p_member_id in range(self.purchase_per_product):
        p_task = PurchaseTask(self.drivers.get(), self.remaining_budget, product, self.user,
          p_group_id, p_member_id)
        self.add_task(p_task).start()
      while True:
        next_group = False
        for task in self.tasks:
          if task.status == PurchaseTaskStatus.FAILED:
            self.quit_all_tasks()
            next_group = True
            break
          if task.status == PurchaseTaskStatus.COMPLETE:
            self.spent += task.spent
            self.finish_task(task)
          if not self.tasks:
            next_group = True
            break
        if next_group:
          break

  @property
  def remaining_budget(self):
    return self.budget - self.spent

  def quit_all_tasks(self):
    for task in self.tasks:
      task.quit(PurchaseTaskStatus.CANCELLED)
      self.tasks.remove(task)

  def finish_task(self, task):
    self.complete_tasks.append(task)
    self.tasks.remove(task)


class PurchaseTask:

  status = PurchaseTaskStatus.NOTSET
  start_time = None

  def __init__(self, driver, budget, product, user, group_id, member_id):
    self.driver = driver
    self.budget = budget
    self.product = product
    self.user = user
    self.group_id = group_id
    self.member_id = member_id
    self.set_status(PurchaseTaskStatus.READY)

  def start(self):
    self.thread = threading.Thread(target=self.buy)
    self.thread.start()
    self.set_status(PurchaseTaskStatus.RUNNING)
    self.start_time = time.time()
    tprint(f'    Started new purchase task {self.id!r}')

  @property
  def id(self):
    return int(f'{self.group_id}{self.member_id}')

  def buy(self):
    self.driver.get(self.product.url)
    try:
      atb_option = self.driver.find_element_by_xpath(_ATB_OPTION_XPATH)
      if _ATB_OPT_KEYWORD not in atb_option.get_attribute('value'):
        raise ATBNotFoundError('ATB not found.')
      atb_option.click()
      time.sleep(_ATB_WAIT_TIME)
      self.driver.get(_CHECKOUT_URL)
      spent_text = self.driver.find_element_by_xpath(_TOTAL_BUY_XPATH).text
      price = float(spent_text.replace(_CURRENCY, ''))
      if price > self.budget:
        raise BugdetMetException(f'Product {self.product.name!r} is too expensive.')
      print(f'{_NL(1)}Trying to buy {str(self.product)!r} (£{price})!')
      self.fill_checkout()
      success = True
      if success:
        self.spent = price
        self.quit(PurchaseTaskStatus.COMPLETE)
        return
    except Exception as error:
      print(error)
      self.quit(PurchaseTaskStatus.FAILED)

  def fill_checkout(self):
    if _CHECKOUT_PART not in self.driver.current_url:
      raise CannotFillCheckoutError('Not on checkout page.')
    for field_id, user_attr in _USER_FIELD_INPUT_MAP.items():
      try:
        value = getattr(self.user, user_attr)
      except AttributeError:
        raise UserFieldInputMappingError(f'Bad user field mapping {user_attr!r}.')
      if isinstance(value, Enum):
        value = value.value
      field = self.driver.find_element_by_id(field_id)
      tprint(f'Filling field {field_id}/{user_attr} with {value!r}')
      if field.tag_name == 'input':
        field.send_keys(value)
      elif field.tag_name == 'select':
        self.driver.find_element_by_xpath(
          f"//select[@id='{field_id}']/option[text()='{value}']").click()
    self.driver.find_element_by_class_name(_CO_FIELD_CLASS_TERMS).click()
    self.driver.find_element_by_xpath(_CO_SUBMIT_XPATH).click()
    time.sleep(30)

  def quit(self, status):
    self.driver.quit()
    self.set_status(status)
    self.duration = time.time() - self.start_time
    tprint(f'{self.id} finished in {secs(self.duration)}')

  def set_status(self, status):
    tprint(f'Status change <task:{self.id}>: {self.status} -> {status}')
    self.status = status


def run_monitor(options):
  listing_page_url = _LISTING_URL.format(category=options.category.value)
  last_products = list(get_products(listing_page_url, options))
  check_already_released(last_products, options)
  last_found_products = []
  p_manager = PurchaseManager(options)
  print(f'{_NL(2)}***Starting monitor***{_NL(2)}')
  while True:
    products = list(get_products(listing_page_url, options))
    print(f'Scanning for products on {listing_page_url}...')
    if products != last_products:
      print('***New products detected!***')
    found_products = search_products(products, options.keywords)
    if found_products and found_products != last_found_products:
      print(f'Found {len(found_products)} products!')
      p_manager.start(found_products)
      last_found_products = found_products
    last_products = products
    time.sleep(_MONITOR_INTERVAL)


def print_welcome():
  print('############################################################')
  print('################### Welcome to SupremeBot #####################')
  print(f'########################## v{_V} ############################')


def print_introduction():
  print('This bot automates the checkout process on the Supreme website.')
  print('A few important notes to get started:')
  print(
    ' - Order your keywords by priority, so the bot knows what you '
    'want the most.')
  print(
    ' - The bot will try and buy ANY products that have ANY of your keywords,'
    'so think carefully how you use them.')
  print(' - If the bot tells you that products are already available given'
        ' your keywords, ONLY CONTINUE IF YOU WANT TO BUY THEM.')
  print(
    ' - Your budget is a saftey net, so the bot doesn\'t ever spend more '
    'then you\'d like.')

  if not _TESTING:
    input(f'{_NL(2)}READY? Hit enter!')


def main():
  print(_NL(2))
  print_welcome()
  print(_NL(2))
  print_introduction()
  print(_NL(2))
  options = collection_options()
  print(_NL(2))
  print(f'Cool. Using options: {_NL(2)}{options}')
  print(_NL(2))
  run_monitor(options)


if __name__ == "__main__":
    main()
