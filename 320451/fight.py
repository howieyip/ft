import sys
sys.path.append('../ft')
from utils.fight import start

start({
    'log_file': '320451/logs/fight.log',
    'PORT' : 11112,
    'BUY_LIST' : [[60, 15, 200*1000]],
    'MAX_VOLUME' : 300*1000,
    'ADJUST_BUY_DICT' : {
        'rise': [2, 3, 1],
        'fall': [2, 3, 2]
    },
    'ALLOW_ADD': True,
    'ADD_PRICE_DIFF': 0.01
})
