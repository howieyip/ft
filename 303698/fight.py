import sys
sys.path.append('../ft')
from utils.fight import start
import datetime

start({
    'log_file': '303698/logs/fight.' + datetime.date.today().strftime('%Y-%m-%d') + '.log',
    'PORT' : 11111,
    'AUTO_BUY': True,
    'if_check_line': False,
    'BULL_CODE': 'HK.51539',
    'BEAR_CODE': '',
    'DELTA_PRICE_MIN': 0,
    'DELTA_PRICE_MAX': 500,
    'BUY_VOLUME' : 20e3,
    'MAX_VOLUME' : 1000e3,
    'AUTO_ADJUST': False,
    'AUTO_ADJUST_BUY': False,
    'AUTO_ADJUST_SELL': False,
    'only_today_buy': False,
    'ADD_PRICE_DIFF': 0.004,
    'AUTO_PLACE_ORDER': True,
    'NEED_LOSS': False,
    'AUTO_MOVE_POSITION': False,
    'MOVE_POSITION_DICT': {
        'from_code': 'HK.',
        'to_code': 'auto',
        'volume': 400e3,
        'cur_price_min': 0.13,
        'cur_price_max': 0.18
    }
})
