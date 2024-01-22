import sys
sys.path.append('../ft')
from utils.fight import start
import datetime

start({
    'log_file': '303698/logs/fight.' + datetime.date.today().strftime('%Y-%m-%d') + '.log',
    'PORT' : 11111,
    'AUTO_BUY': True,
    'BULL_CODE': 'auto',
    'BEAR_CODE': 'auto',
    'BUY_VOLUME' : 600e3,
    'MAX_VOLUME' : 800e3,
    'AUTO_ADJUST': True,
    'AUTO_PLACE_ORDER': True,
    'AUTO_FORCE_REPLACING': False,
})
