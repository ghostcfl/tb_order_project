import shutil
from pyppeteer.launcher import CHROME_PROFILE_PATH

if __name__ == '__main__':
    shutil.rmtree(CHROME_PROFILE_PATH, True)
