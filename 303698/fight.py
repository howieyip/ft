import sys
sys.path.append('../ft')
from utils.fight import start

start({
    'log_file': '303698/logs/fight.log',
    'PORT' : 11111,
    'BUY_LIST' : [[60, 15, 300*1000]],
    'MAX_VOLUME' : 500*1000,
    'ADJUST_BUY_DICT' : {
        'rise': [2, 3, 0],
        'fall': [2, 3, 2]
    }
})
