import sys
sys.path.append('../ft')
from utils.fight import start
import datetime

start({
    'log_file': '303698/logs/fight.' + datetime.date.today().strftime('%Y-%m-%d') + '.log',
    'PORT' : 11111,
    # 'AUTO_BUY': True,
    # 'if_check_line': False,
    # 'BULL_CODE': 'auto',
    # 'BEAR_CODE': 'auto',
    # 'DELTA_PRICE_MIN': 5,
    # 'DELTA_PRICE_MAX': 20,
    # 'BUY_VOLUME' : 400e3,
    # 'AUTO_ADJUST': True,
    # 'AUTO_ADJUST_BUY': True,
    # 'AUTO_ADJUST_SELL': True,
    # 'only_today_buy': False,
    # 'AUTO_PLACE_ORDER': False,
    # 'NEED_LOSS': False,
    # 'CUR_PRICE_MAX': 0.12,
    # 'sell_all_to_over': False,
    # 'AUTO_MOVE_POSITION': True,
})
