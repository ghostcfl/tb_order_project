import asyncio

from core.spiders.base_spider import BaseSpider
from tools.logger import logger


class CaptchaCheck(BaseSpider):
    async def find_captcha(self):
        pages = self.browser.pages
        for page in pages:
            frames = page.frames
            frame = await self.login.get_nc_frame(frames)
            if frame:
                await self.login.slider()

    @classmethod
    async def run(cls):
        while 1:
            logger.info("验证码检测")
            await asyncio.sleep(60)
            captcha_check = CaptchaCheck()
            await captcha_check.find_captcha()
