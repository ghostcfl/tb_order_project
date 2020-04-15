import time
import schedule

from main import run

run('YK')

schedule.every(1).seconds.do(run, 'YK')
while 1:
    schedule.run_pending()
    time.sleep(1)
