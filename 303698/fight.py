import sys
sys.path.append('../ft')
from utils.fight import start
import datetime

start({
    'log_file': '303698/logs/fight.' + datetime.date.today().strftime('%Y-%m-%d') + '.log',
    'PORT' : 11111,
    'acc_id': 281756481226004224,
    'PASSWORD_MD5': 'd7866f93b87fc9c1b0a06a6a6669bada',
    # 'exclude_code_list': ['HK.58498'],
    # 'include_code_list': ['HK.62976'],
    # 'AUTO_BUY': True,
    # 'BULL_CODE': 'auto',
    # 'BEAR_CODE': 'auto',
    # 'BUY_VOLUME' : 400e3,
    # 'CUR_PRICE_MAX': 0.13,
    # 'AUTO_ADJUST': True,
    # 'AUTO_ADJUST_BUY': True,
})
