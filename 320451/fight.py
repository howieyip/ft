import sys
sys.path.append('../ft')
from utils.fight import start
import datetime

start({
    'log_file': '320451/logs/fight.' + datetime.date.today().strftime('%Y-%m-%d') + '.log',
    'PORT' : 11112,
    'AUTO_BUY': True,
    'BULL_CODE': '',
    'BEAR_CODE': 'auto',
    'BUY_VOLUME' : 200e3,
    'MAX_VOLUME' : 300e3,
    'AUTO_ADJUST': True,
    'AUTO_PLACE_ORDER': True,
    'AUTO_MOVE_POSITION': False,
})
