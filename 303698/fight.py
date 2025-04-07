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
    # 'CUR_PRICE_MIN': 0.06,
    # 'CUR_PRICE_MAX': 0.16,
    # 'ADD_ORDER_DIFF': 0.004,
    # 'EVERY_ORDER_DIFF': 0.003,
    # 'NEED_LOSS': True,
    'BULL_CODE': 'HK.50756',
    # 'BUY_VOLUME' : 120e3,
    # 'ADD_ORDER_DIFF': 0.02,
    # 'EVERY_ORDER_DIFF': 0.005,
})
