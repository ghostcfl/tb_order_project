import time
import schedule

from core.spiders.store_item_page_spider import StoreItemPageSpider

if __name__ == '__main__':

    StoreItemPageSpider.run()

    schedule.every(1).seconds.do(StoreItemPageSpider.run)
    while 1:
        schedule.run_pending()
        time.sleep(1)
