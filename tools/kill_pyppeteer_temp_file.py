import shutil
from pyppeteer.launcher import CHROME_PROFILE_PATH


def kill_temp_file():
    shutil.rmtree(CHROME_PROFILE_PATH, True)


if __name__ == '__main__':
    kill_temp_file()
