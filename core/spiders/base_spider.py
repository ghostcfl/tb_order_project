import re


class BaseSpider(object):
    completed = 0
    captcha = False

    def __init__(self, login, browser, page, fromStore):
        self.login = login
        self.browser = browser
        self.page = page
        self.fromStore = fromStore

    async def intercept_request(self, req):
        # punish?x5secdata
        is_captcha = re.search("punish\?x5secdata", req.url)
        if is_captcha:
            await self.login.slider(self.page)
        await req.continue_()

    async def intercept_response(self, res):
        """截取response响应"""
        pass

    async def listening(self, page):
        await page.setRequestInterception(True)
        page.on('request', self.intercept_request)
        page.on('response', self.intercept_response)
