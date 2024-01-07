import sys
sys.path.append('../ft')
from utils.fight import start
import datetime

start({
    'log_file': '303698/logs/fight.' + datetime.date.today().strftime('%Y-%m-%d') + '.log',
    'PORT' : 11111,
    'BULL_CODE': 'auto',
    'BUY_VOLUME' : 600e3,
    'MAX_VOLUME' : 800e3,
    'ALLOW_ADD': True,
})
