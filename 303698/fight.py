import sys
sys.path.append('../ft')
from utils.fight import start

start({
    'PORT' : 11111,
    'BUY_LIST' : [[60, 15, 100*1000]],
    'MAX_VOLUME' : 300*1000,
    'ADJUST_BUY_DICT' : {
        'rise': [2, 3, 0],
        'fall': [2, 3, 2]
    }
})
