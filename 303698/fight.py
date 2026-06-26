import sys
sys.path.append('../ft')
from utils.fight import start
import datetime

start({
    'log_file': '303698/logs/fight.' + datetime.date.today().strftime('%Y-%m-%d') + '.log',
    'PORT' : 11111,
    'acc_id': 281756481226004224,
    'PASSWORD_MD5': 'd7866f93b87fc9c1b0a06a6a6669bada',
    'AUTO_BUY': True,
    # 'BULL_CODE': 'auto',
    # 'BUY_VOLUME' : 200e3,
    # 'MAX_VOLUME': 400e3,
    # 'CUR_PRICE_MIN': 0.04,
    # 'CUR_PRICE_MAX': 0.16,
    # 'ADD_ORDER_DIFF': 0.004,
    # 'EVERY_ORDER_DIFF': 0.002,
    # 'NEED_LOSS': True,
    'BULL_CODE': 'HK.69345',
    'ADD_ORDER_DIFF': 0.032,
    'EVERY_ORDER_DIFF': 0.016,
    'FAR_ORDER_LIST': [[40e3, 40e3]],
})
