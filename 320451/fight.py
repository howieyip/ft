import sys
sys.path.append('../ft')
from utils.fight import start
import datetime

start({
    'log_file': '320451/logs/fight.' + datetime.date.today().strftime('%Y-%m-%d') + '.log',
    'PORT' : 11112,
    'BUY_VOLUME' : 200e3,
    'MAX_VOLUME' : 300e3,
    'ADJUST_BUY_DICT' : {
        'rise': [2, 3, 1],
        'fall': [2, 3, 2]
    },
    'ALLOW_ADD': True,
    'ADD_PRICE_DIFF': 0.01
})
