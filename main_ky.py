import time
import schedule

from main import run

run('KY')

schedule.every(1).seconds.do(run, 'KY')
while 1:
    schedule.run_pending()
    time.sleep(1)
