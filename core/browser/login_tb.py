import asyncio
import random
from pyppeteer.launcher import launch
from pyppeteer import errors

from settings import LAUNCH_SETTING, WIDTH, HEIGHT, S_T_P_L, P_I, U_I, MAIL_RECEIVERS, CAPTCHA
from settings import CAPTCHA_ERROR, CAPTCHA_ERROR_CLICK, LOGIN_SUBMIT, TEST_SERVER_DB_TEST
from settings import PHONE_CHECK_INPUT, PHONE_GET_CODE, PHONE_SUBMIT_BTN, CAPTCHA_SUCCESS
from tools.tools_method import my_sleep, my_async_sleep
from tools.logger import logger
from tools.mail import mail
from tools.request_user_agent import get_request_user_agent
from db.my_sql import MySql


class LoginTB(object):
    page = None
    browser = None

    def __init__(self):
        pass

    async def set_page(self, **kwargs):
        LAUNCH_SETTING['args'].append(kwargs['window_position'])
        self.browser = await launch(**LAUNCH_SETTING)
        p = await self.browser.pages()
        self.page = p[0]
        await self.page.setViewport({"width": WIDTH, "height": HEIGHT})

    async def new_page(self):
        page = await self.browser.newPage()
        await page.setViewport({"width": WIDTH, "height": HEIGHT})
        return page

    async def do_login(self, **kwargs):
        await self.set_page(**kwargs)
        while 1:
            try:
                await self.page.goto("https://login.taobao.com", timeout=30000)
            except Exception as e:
                logger.error("网络连接异常，5秒后重连，原因" + str(e))
                my_sleep(5)
            else:
                break

        while 1:
            try:
                await self.page.waitForSelector(S_T_P_L, visible=True, timeout=10000)
                await self.page.click(S_T_P_L)
            except errors.TimeoutError:
                pass
            except errors.ElementHandleError:
                await self.page.reload()
                continue
            finally:
                result = await self.type_with_login_info(kwargs)
                if result:
                    break
                else:
                    mail("登陆错误", "登陆CSS错误，请查看CSS是否正确", MAIL_RECEIVERS)
        slider = await self.check_captcha(page=self.page)  # 检测是否有滑块

        if slider:
            logger.info("检测页面出现滑块")
            t = await self.slider(page=self.page)
            if not t:
                try:
                    await self.page.click(LOGIN_SUBMIT[0])  # 调用page模拟点击登录按钮。
                except Exception as e:
                    str(e)
                    await self.page.click(LOGIN_SUBMIT[1])  # 调用page模拟点击登录按钮。
                    my_sleep(5)
        else:
            try:
                await self.page.click(LOGIN_SUBMIT[0])  # 调用page模拟点击登录按钮。
            except Exception as e:
                str(e)
                await self.page.click(LOGIN_SUBMIT[1])  # 调用page模拟点击登录按钮。

        t = await self.phone_verify(self.page, kwargs['fromStore'])
        if t:
            exit("登陆失败退出程序")
        return self.browser, self.page, kwargs['fromStore']

    @staticmethod
    async def check_captcha(page):
        try:
            await page.waitForSelector(CAPTCHA, visible=True, timeout=5000)
            # 检测页面滑块是否可见，如果可见表示出现滑块
        except errors.TimeoutError:
            slider = 0  # 检测超时表示，没有出现滑块
        else:
            slider = 1
        return slider

    async def type_with_login_info(self, kwargs):
        for i in range(len(U_I)):
            try:
                await self.page.type(U_I[i], kwargs['username'], {'delay': self.input_time_random() - 50})
                await self.page.type(P_I[i], kwargs['password'], {'delay': self.input_time_random()})
            except Exception as e:
                logger.error(str(e) + "[" + U_I[i] + "][" + P_I[i] + "]")
                continue
            else:
                return 1
        return 0

    @staticmethod
    def input_time_random():
        return random.randint(100, 151)

    @staticmethod
    async def get_nc_frame(frames):
        for frame in frames:
            slider = await frame.J(CAPTCHA)
            if slider:
                return frame
        return None

    async def slider(self, page):
        await asyncio.sleep(3)
        frames = page.frames
        frame = await self.get_nc_frame(frames)
        if frame:
            await page.bringToFront()
            try_times = 0
            nc = await frame.J(CAPTCHA)
            nc_detail = await nc.boundingBox()
            print(nc_detail)
            x = int(nc_detail['x'] + 1)
            y = int(nc_detail['y'] + 1)
            width = int(nc_detail['width'] - 1)
            height = int(nc_detail['height'] - 1)
            logger.info("条形验证码")
            logger.info("第" + str(try_times) + "次尝试滑动验证码")
            while 1:
                if try_times > 15:
                    raise Exception
                try_times += 1
                await asyncio.sleep(1)
                start_x = random.uniform(x, x + width)
                start_y = random.uniform(y, y + height)
                a = y - start_y
                await page.mouse.move(start_x, start_y)
                await page.mouse.down()
                await page.mouse.move(start_x + random.uniform(300, 400),
                                      start_y + random.uniform(a, 34 - abs(a)),
                                      {"steps": random.randint(30, 100)})
                await page.mouse.up()
                while 1:
                    try:
                        await frame.waitForSelector(CAPTCHA_ERROR, timeout=10000)
                    except Exception as e:
                        if await frame.J(CAPTCHA_SUCCESS):
                            return 0
                        slider = await self.check_captcha(page)
                        if not slider:
                            return 0
                        break
                    else:
                        await my_async_sleep(2, True)
                        await frame.click(CAPTCHA_ERROR_CLICK)
                        break
        else:
            return 0

    async def phone_verify(self, page, fromStore):
        try:
            await page.waitForSelector("#container", timeout=30000)
        except errors.TimeoutError:
            logger.info("超时末扫码或需要手机验证！")
            await self.verify(page, fromStore)
            await page.goto("https://myseller.taobao.com/home.htm")
        finally:
            await page.waitForSelector("#container", timeout=0)
            while 1:
                try:
                    await page.goto("https://trade.taobao.com/trade/itemlist/list_sold_items.htm")
                    await page.waitForSelector(".pagination-mod__show-more-page-button___txdoB", timeout=10000)
                except Exception as e:
                    str(e)
                    await self.verify(page, fromStore)
                finally:
                    if page.url == "https://trade.taobao.com/trade/itemlist/list_sold_items.htm":
                        t = await self.slider(self.page)
                        if not t:
                            await page.click(".pagination-mod__show-more-page-button___txdoB")  # 显示全部页码
                            break
            t = await self.slider(page)
            if t:
                return t
            else:
                return 0

    async def verify(self, page, fromStore):
        frame = None
        frames = page.frames
        try:
            for f in frames:
                input_box1 = await f.J(PHONE_CHECK_INPUT[0])
                input_box2 = await f.J(PHONE_CHECK_INPUT[1])
                if input_box1 or input_box2:
                    frame = f
            if frame:
                await frame.waitForSelector(PHONE_CHECK_INPUT[0], timeout=10000)
            else:
                return 0
                # logger.error("手机验证码输入框验证码错误")
                # exit("手机验证码输入框验证码错误")
        except errors.TimeoutError:
            try:
                await frame.waitForSelector(PHONE_CHECK_INPUT[1], timeout=10000)
            except errors.TimeoutError:
                pass
            else:
                await self.input_verify_code(frame, fromStore, 1)
        else:
            await self.input_verify_code(frame, fromStore, 0)

    async def input_verify_code(self, frame, fromStore, type):
        logger.info("需要要手机验证码")
        ms = MySql(db_setting=TEST_SERVER_DB_TEST)
        ms.delete(t='phone_verify', c={'fromStore': fromStore})
        ms.insert(t="phone_verify", d={"fromStore": fromStore})
        mail(fromStore + "手机验证码", fromStore + "登陆需要手机验证码", MAIL_RECEIVERS)
        verify_code = "0"
        while 1:
            if type == 0:
                await frame.click(PHONE_GET_CODE[0])
            else:
                await frame.click(PHONE_GET_CODE[1])
            for i in range(120):
                await asyncio.sleep(5)
                verify_code = ms.get_one(t='phone_verify', cn=['verify_code'], c={"fromStore": fromStore})
                if verify_code != "0":
                    ms.delete(t='phone_verify', c={'fromStore': fromStore})
                    del ms
                    break
            if verify_code != "0":
                break
            await asyncio.sleep(10)
        if type == 0:
            await frame.type(PHONE_CHECK_INPUT[0], verify_code, {'delay': self.input_time_random() - 50})
            await frame.click(PHONE_SUBMIT_BTN[0])
        else:
            await frame.type(PHONE_CHECK_INPUT[1], verify_code, {'delay': self.input_time_random() - 50})
            await frame.click(PHONE_SUBMIT_BTN[1])

    @staticmethod
    async def get_cookie(page):
        """获取登录后cookie"""
        cookies_list = await page.cookies()
        cookies = ''
        for cookie in cookies_list:
            str_cookie = '{0}={1};'
            str_cookie = str_cookie.format(cookie.get('name'), cookie.get('value'))
            cookies += str_cookie
        return cookies

    @classmethod
    async def run(cls, **kwargs):
        lt = LoginTB()
        b, p, f = await lt.do_login(**kwargs)
        return lt, b, p, f


if __name__ == '__main__':
    from settings import STORE_INFO

    # lt = LoginTB()
    asyncio.get_event_loop().run_until_complete(LoginTB.run(**STORE_INFO['YJ']))
