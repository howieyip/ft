import sys
sys.path.append('../ft')
from utils.fight import start
import datetime

start({
    'log_file': '320451/logs/fight.' + datetime.date.today().strftime('%Y-%m-%d') + '.log',
    'PORT' : 11112,
    'acc_id': 281756480765285182,
    'PASSWORD_MD5': 'd7866f93b87fc9c1b0a06a6a6669bada',
})
