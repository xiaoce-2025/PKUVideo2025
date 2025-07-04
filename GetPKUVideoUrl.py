import pyperclip
import asyncio
import pyppeteer as pyp
from random import uniform
import logging
import traceback
from datetime import datetime
import re
import os

# 缺省设置
course_id = 70000
Replay_maxNum = -1
IAAA_username = "2x000xxxxx"
IAAA_password = "xxxxxx"
ChromeExecutablePath = r"C:\Users\AppData\Local\pyppeteer\pyppeteer\local-chromium\588429\chrome.exe"
'''缺省配置说明
course_id: 课程id，在教学网点开该课程的网址中可以看到course_id=xxxx参数，五位数字
Replay_maxNum: 单个课程最大下载的回放数(int)，-1表示无限制
IAAA登录账密
ChormeExecutablePath: 你的Chrome浏览器安装地址，具体可以查看安装说明
'''

# 设置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def antiAntiCrawler(page):
    """为page添加反反爬虫手段"""
    await page.setUserAgent('Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.70 Safari/537.36')
    await page.evaluateOnNewDocument('() =>{ Object.defineProperties(navigator, { webdriver:{ get: () => false } }) }')


async def safe_wait_for_selector(page, selector, timeout=30000):
    """安全等待选择器出现"""
    try:
        logger.info(f"等待选择器: {selector}")
        await page.waitForSelector(selector, {'timeout': timeout})
        return True
    except Exception as e:
        logger.error(f"等待选择器失败: {selector} - {str(e)}")
        return False


async def login(page, username, password):
    """执行登录流程"""
    try:
        # 检查是否已在登录状态
        if await safe_wait_for_selector(page, "#global-nav-link", timeout=3000):
            logger.info("检测到已登录")
            return True

        # 处理IAAA登录
        logger.info("尝试登录")

        # 确保登录表单已加载
        await safe_wait_for_selector(page, "#user_name")
        logger.info("检测到登录表单")

        # 输入凭据
        await asyncio.sleep(uniform(1.0, 1.0))
        await page.type("#user_name", username)
        await asyncio.sleep(uniform(0.5, 1.0))
        await page.type("#password", password)
        await asyncio.sleep(uniform(0.5, 1.0))

        # 提交登录
        logger.info("提交登录表单")
        navigation_promise = page.waitForNavigation(
            options={'waitUntil': 'networkidle2', 'timeout': 30000}
        )
        await page.click("#logon_button")
        await navigation_promise

        # 验证登录成功
        if await safe_wait_for_selector(page, "#agree_button", timeout=20000):
            logger.info("登录成功")
            await asyncio.sleep(uniform(0.5, 1.0))
            await page.click("#agree_button")
            await asyncio.sleep(uniform(0.5, 1.0))
            return True
        else:
            logger.warning("登录状态验证失败")
            return False

    except Exception as e:
        logger.error(f"登录过程中出错: {str(e)}")
        return False


async def get_course_list(username, password, chrome_path):
    """登录并返回课程列表（[{name, key}]）"""
    loginUrl = "https://course.pku.edu.cn/webapps/bb-sso-BBLEARN/login.html"
    width, height = 1400, 800
    browser = await pyp.launch(
        headless=True,
        executablePath=chrome_path,
        userdataDir="c:/tymp",
        args=[
            f'--window-size={width},{height}',
            '--disable-infobars',
            '--disable-blink-features=AutomationControlled'
        ],
        ignoreDefaultArgs=['--enable-automation']
    )
    page = await browser.newPage()
    await antiAntiCrawler(page)
    await page.setViewport({'width': width, 'height': height})
    await page.setJavaScriptEnabled(True)
    await page.evaluate("() => { window.alert = () => {}; window.prompt = () => {}; window.confirm = () => true; }")
    await page.goto(loginUrl, {'waitUntil': 'networkidle2', 'timeout': 60000})
    if not await login(page, username, password):
        await browser.close()
        return []
    course_list = []
    if await safe_wait_for_selector(page, "#anonymous_element_5 > span"):
        logger.info("主页面加载成功")
        current_term_module = await page.querySelector("#module\\:_141_1")
        if current_term_module:
            logger.info("获取当前学期模块成功")
            course_links = await current_term_module.querySelectorAll("a[href]")
            print(course_links)
            for link in course_links:
                # 获取课程名
                name = await page.evaluate('(el) => el.textContent.trim()', link)
                # 获取 href
                href = await page.evaluate('(el) => el.getAttribute("href")', link)
                # 提取 key
                match = re.search(r"key=(_\d+_1)", href)
                key = match.group(1) if match else None
                if name and key:
                    course_list.append({"name": name, "key": key})
                    print(f"课程名: {name}, key: {key}")
                logger.info(f"当前学期课程信息: {course_list}")
        current_term_module = await page.querySelector("#module\\:_142_1")
        if current_term_module:
            logger.info("获取历史学期模块成功")
            course_links = await current_term_module.querySelectorAll("a[href]")
            print(course_links)
            for link in course_links:
                # 获取课程名
                name = await page.evaluate('(el) => el.textContent.trim()', link)
                # 获取 href
                href = await page.evaluate('(el) => el.getAttribute("href")', link)
                # 提取 key
                match = re.search(r"key=(_\d+_1)", href)
                key = match.group(1) if match else None
                if name and key:
                    course_list.append({"name": name, "key": key})
                    print(f"课程名: {name}, key: {key}")
                logger.info(f"历史学期课程信息: {course_list}")
    await browser.close()
    return course_list

async def download_replay_links(username, password, chrome_path, course_keys, max_num, log_callback=None, save_path=None):
    """批量抓取所选课程的回放下载链接，course_keys为key列表，log_callback为日志回调，save_path为保存目录"""
    loginUrl = "https://course.pku.edu.cn/webapps/bb-sso-BBLEARN/login.html"
    width, height = 1400, 800
    for course_key in course_keys:
        replay_data = []
        browser = await pyp.launch(
            headless=True,
            executablePath=chrome_path,
            userdataDir="c:/tymp",
            args=[
                f'--window-size={width},{height}',
                '--disable-infobars',
                '--disable-blink-features=AutomationControlled'
            ],
            ignoreDefaultArgs=['--enable-automation']
        )
        page = await browser.newPage()
        await antiAntiCrawler(page)
        await page.setViewport({'width': width, 'height': height})
        await page.setJavaScriptEnabled(True)
        await page.evaluate("() => { window.alert = () => {}; window.prompt = () => {}; window.confirm = () => true; }")
        await page.goto(loginUrl, {'waitUntil': 'networkidle2', 'timeout': 60000})
        if not await login(page, username, password):
            if log_callback:
                log_callback(f"课程 {course_key} 登录失败")
            await browser.close()
            continue
        target_review_url = f"https://course.pku.edu.cn/webapps/bb-streammedia-hqy-BBLEARN/videoList.action?course_id={course_key}&mode=view"
        await page.goto(target_review_url, {'waitUntil': 'networkidle0', 'timeout': 30000})
        if log_callback:
            log_callback(f"已进入课程 {course_key} 回放列表页面")
        try:
            page_count = 0
            replay_item_count = 0
            while True:
                await safe_wait_for_selector(page, "#listContainer_databody", timeout=20000)
                await asyncio.sleep(uniform(2, 1.0))
                page_count += 1
                replay_rows = await page.querySelectorAll("#listContainer_databody tr")
                for i, row in enumerate(replay_rows):
                    if (max_num != -1 and i == max_num):
                        break
                    try:
                        name_el = await row.querySelector("th[scope='row']")
                        name = await page.evaluate('(el) => el.textContent.trim()', name_el) if name_el else ""
                        time_td = await row.querySelector("td:nth-child(2)")
                        time = ""
                        if time_td:
                            time_span = await time_td.querySelector(".table-data-cell-value")
                            time = await page.evaluate('(el) => el.textContent.trim()', time_span) if time_span else ""
                        teacher_td = await row.querySelector("td:nth-child(3)")
                        teacher = ""
                        if teacher_td:
                            teacher_span = await teacher_td.querySelector(".table-data-cell-value")
                            teacher = await page.evaluate('(el) => el.textContent.trim()', teacher_span) if teacher_span else ""
                        action_td = await row.querySelector("td:last-child")
                        watch_url = ""
                        if action_td:
                            link_el = await action_td.querySelector("a.inlineAction")
                            if link_el:
                                watch_url = await page.evaluate('(el) => el.href', link_el)
                        replay_data.append({
                            "index": i + 1,
                            "name": name,
                            "time": time,
                            "teacher": teacher,
                            "url": watch_url,
                        })
                    except Exception as e:
                        if log_callback:
                            log_callback(f"解析第 {i+1} 项时出错: {str(e)}")
                        continue
                replay_item_count += len(replay_rows)
                if (await safe_wait_for_selector(page, "#listContainer_nextpage_bot",50)):
                    await page.click("#listContainer_nextpage_bot")
                    await asyncio.sleep(uniform(0.5, 0.2))
                else:
                    break
        except Exception as e:
            if log_callback:
                log_callback(f"解析回放列表失败: {str(e)}")
        # 获取每个回放的下载链接
        for i in range(len(replay_data)):
            try:
                url = replay_data[i]["url"]
                await page.goto(url, {'waitUntil': 'networkidle0', 'timeout': 30000})
                await safe_wait_for_selector(page, "#containerdiv > iframe", timeout=20000)
                frame = await page.waitForSelector("#containerdiv > iframe", timeout=15000)
                frame = await frame.contentFrame()
                await frame.waitForSelector('body', timeout=10000)
                await frame.waitForSelector("#app > div.container > div > div > div.course-info__wrap > div.course-info__footer > button:nth-child(2)", timeout=15000)
                await asyncio.sleep(uniform(1, 1.0))
                await frame.click(
                    "#app > div.container > div > div > div.course-info__wrap > div.course-info__footer > button:nth-child(2)")
                await asyncio.sleep(0.5)
                url = pyperclip.paste()
                replay_data[i]["url"] = url
                if log_callback:
                    log_callback(f"成功获取第 {i+1} 项下载链接: {url}")
            except Exception as e:
                if log_callback:
                    log_callback(f"获取第 {i+1} 项下载链接时出错: {str(e)}")
                continue
        # 保存到文件
        if save_path:
            os.makedirs(save_path, exist_ok=True)
            filename = os.path.join(save_path, f"output_{course_key}_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt")
        else:
            filename = f"output_{course_key}_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(str(replay_data))
        if log_callback:
            log_callback(f"课程 {course_key} 下载完成，结果已保存到 {filename}")
        await browser.close()


def main():
    url = "https://course.pku.edu.cn/webapps/bb-sso-BBLEARN/login.html"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(get_course_list(IAAA_username, IAAA_password, ChromeExecutablePath))


if __name__ == "__main__":
    course_id = int(input())
    main()
