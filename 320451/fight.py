import sys
sys.path.append('../ft')
from utils.fight import start
import datetime

start({
    'log_file': '320451/logs/fight.' + datetime.date.today().strftime('%Y-%m-%d') + '.log',
    'PORT' : 11112,
})
