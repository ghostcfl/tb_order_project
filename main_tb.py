import time
import schedule

from main import run

run('TB')

schedule.every(1).seconds.do(run, 'TB')
while 1:
    schedule.run_pending()
    time.sleep(1)
