import sys
sys.path.append('../ft')
from utils.fight import start
import datetime

start({
    'log_file': '320451/logs/fight.' + datetime.date.today().strftime('%Y-%m-%d') + '.log',
    'PORT' : 11112,
    'BULL_CODE': '',
    'BUY_VOLUME' : 200e3,
    'MAX_VOLUME' : 300e3,
    'ALLOW_ADD': True,
})
