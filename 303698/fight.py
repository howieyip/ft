import sys
sys.path.append('../ft')
from utils.fight import start
import datetime

start({
    'log_file': '303698/logs/fight.' + datetime.date.today().strftime('%Y-%m-%d') + '.log',
    'PORT' : 11111,
    'BULL_CODE': 'auto',
    'BUY_VOLUME' : 300e3,
    'MAX_VOLUME' : 500e3,
    'ADJUST_BUY_DICT' : {
        'rise': [2, 3, 0],
        'fall': [2, 3, 2]
    },
    'ALLOW_ADD': True,
    'ADD_PRICE_DIFF': 0.004
})
