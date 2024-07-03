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
    'BUY_VOLUME' : 200e3,
    'MAX_VOLUME' : 300e3,
    'AUTO_ADJUST': True,
    'AUTO_PLACE_ORDER': True,
    'AUTO_MOVE_POSITION': True,
    'MOVE_POSITION_DICT': {
        'from_code': 'HK.',
        'to_code': 'auto',
        'volume': 400e3,
        'cur_price_min': 0.13,
        'cur_price_max': 0.18
    }
})
