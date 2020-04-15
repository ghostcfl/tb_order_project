import time
import schedule

from main import run

run('YJ')

schedule.every(1).seconds.do(run, 'YJ')
while 1:
    schedule.run_pending()
    time.sleep(1)
