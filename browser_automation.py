from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import logging
from config import BROWSER_CONFIG, SEARCH_ENGINES, PROXY_CONFIG, SCREENSHOT_CONFIG, LOG_CONFIG


# 配置日志
logging.basicConfig(
    level=getattr(logging, LOG_CONFIG["level"]),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=LOG_CONFIG["file"] if LOG_CONFIG.get("file") else None
)
logger = logging.getLogger("BrowserAutomation")


class BrowserAutomation:
    """浏览器自动化类，提供与浏览器交互的基本功能"""
    
    def __init__(self, headless=None, browser_type=None, user_data_dir=None):
        """
        初始化浏览器
        
        Args:
            headless: 是否使用无头模式（不显示浏览器界面）
            browser_type: 浏览器类型，支持 "chrome" 和 "firefox"
            user_data_dir: 用户数据目录，可以保存登录状态等信息
        """
        # 使用参数或配置文件中的值
        headless = headless if headless is not None else BROWSER_CONFIG["headless"]
        browser_type = browser_type or BROWSER_CONFIG["browser_type"]
        user_data_dir = user_data_dir or BROWSER_CONFIG["user_data_dir"]
        
        self.browser_type = browser_type.lower()
        logger.info(f"初始化浏览器: {self.browser_type}, 无头模式: {headless}")
        
        # 确保截图目录存在
        if not os.path.exists(SCREENSHOT_CONFIG["save_dir"]):
            os.makedirs(SCREENSHOT_CONFIG["save_dir"])
        
        if self.browser_type == "chrome":
            # 配置Chrome选项
            chrome_options = Options()
            if headless:
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # 设置用户数据目录，可以保存登录状态等信息
            if user_data_dir:
                chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
            
            # 设置语言
            chrome_options.add_argument("--lang=zh-CN")
            
            # 添加跨域支持
            chrome_options.add_argument("--disable-web-security")
            
            # 设置代理
            if PROXY_CONFIG["use_proxy"]:
                if PROXY_CONFIG["http_proxy"]:
                    chrome_options.add_argument(f"--proxy-server={PROXY_CONFIG['http_proxy']}")
                    logger.info(f"使用代理: {PROXY_CONFIG['http_proxy']}")
            
            # 初始化WebDriver
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            
        elif self.browser_type == "firefox":
            from selenium.webdriver.firefox.service import Service as FirefoxService
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            from webdriver_manager.firefox import GeckoDriverManager
            
            firefox_options = FirefoxOptions()
            if headless:
                firefox_options.add_argument("--headless")
            
            # 设置代理
            if PROXY_CONFIG["use_proxy"] and PROXY_CONFIG["http_proxy"]:
                firefox_options.set_preference("network.proxy.type", 1)
                proxy_parts = PROXY_CONFIG["http_proxy"].replace("http://", "").split(":")
                firefox_options.set_preference("network.proxy.http", proxy_parts[0])
                if len(proxy_parts) > 1:
                    firefox_options.set_preference("network.proxy.http_port", int(proxy_parts[1]))
            
            self.driver = webdriver.Firefox(
                service=FirefoxService(GeckoDriverManager().install()),
                options=firefox_options
            )
            
        else:
            raise ValueError(f"不支持的浏览器类型: {browser_type}")
        
        # 设置隐式等待时间
        self.driver.implicitly_wait(BROWSER_CONFIG["implicit_wait"])
        logger.info("浏览器初始化完成")
        
    def navigate_to(self, url):

        logger.info(f"导航到: {url}")
        self.driver.get(url)
        
    def search(self, search_engine, query):

        if search_engine.lower() not in SEARCH_ENGINES:
            error_msg = f"不支持的搜索引擎: {search_engine}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        engine_info = SEARCH_ENGINES[search_engine.lower()]
        logger.info(f"在 {search_engine} 上搜索: {query}")
        
        # 导航到搜索引擎
        self.navigate_to(engine_info["url"])
        
        # 等待搜索框出现
        search_box = WebDriverWait(self.driver, BROWSER_CONFIG["explicit_wait"]).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, engine_info["input_selector"]))
        )
        
        # 输入搜索查询
        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)
        
        # 等待搜索结果加载
        time.sleep(2)
        
        # 返回页面源代码
        return self.driver.page_source
        
    def click_element(self, selector, selector_type=By.CSS_SELECTOR):

        try:
            logger.info(f"尝试点击元素: {selector}")
            element = WebDriverWait(self.driver, BROWSER_CONFIG["explicit_wait"]).until(
                EC.element_to_be_clickable((selector_type, selector))
            )
            element.click()
            logger.info(f"成功点击元素: {selector}")
            return True
        except Exception as e:
            logger.error(f"点击元素失败: {selector}, 原因: {e}")
            return False
    
    def get_page_title(self):

        try:
            logger.info("获取页面标题")
            title = self.driver.title
            logger.info(f"页面标题: {title}")
            return title
        except Exception as e:
            logger.error(f"获取页面标题失败: {e}")
            return ""

    def get_search_results(self):
        """
        获取当前页面的搜索结果
        
        Returns:
            list: 搜索结果列表，每个结果包含标题和链接
        """
        try:
            logger.info("获取搜索结果")
            # 获取所有搜索结果元素
            result_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.g")
            results = []
            
            for element in result_elements:
                try:
                    # 获取标题和链接
                    title_element = element.find_element(By.CSS_SELECTOR, "h3")
                    link_element = element.find_element(By.CSS_SELECTOR, "a")
                    
                    title = title_element.text
                    link = link_element.get_attribute("href")
                    
                    if title and link:
                        results.append({
                            "title": title,
                            "link": link,
                            "snippet": element.find_element(By.CSS_SELECTOR, "div.VwiC3b").text
                        })
                except Exception as e:
                    logger.warning(f"提取搜索结果项失败: {e}")
                    continue
            
            logger.info(f"成功获取 {len(results)} 个搜索结果")
            return results
        except Exception as e:
            logger.error(f"获取搜索结果失败: {e}")
            return []

    def get_element_text(self, selector, selector_type=By.CSS_SELECTOR):
        """
        获取元素的文本内容
        
        Args:
            selector: 元素选择器
            selector_type: 选择器类型 (默认CSS选择器)
            
        Returns:
            str: 元素的文本内容
        """
        try:
            logger.info(f"尝试获取元素文本: {selector}")
            element = WebDriverWait(self.driver, BROWSER_CONFIG["explicit_wait"]).until(
                EC.presence_of_element_located((selector_type, selector))
            )
            text = element.text
            logger.info(f"成功获取元素文本: {selector}")
            return text
        except Exception as e:
            logger.error(f"获取元素文本失败: {selector}, 原因: {e}")
            return ""

    def get_input_value(self, selector, selector_type=By.CSS_SELECTOR):
        """
        获取输入框的值
        
        Args:
            selector: 元素选择器
            selector_type: 选择器类型 (默认CSS选择器)
            
        Returns:
            str: 输入框的值
        """
        try:
            logger.info(f"尝试获取输入框值: {selector}")
            element = WebDriverWait(self.driver, BROWSER_CONFIG["explicit_wait"]).until(
                EC.presence_of_element_located((selector_type, selector))
            )
            value = element.get_attribute("value")
            logger.info(f"成功获取输入框值: {selector}")
            return value
        except Exception as e:
            logger.error(f"获取输入框值失败: {selector}, 原因: {e}")
            return ""

    def get_scroll_position(self):
        """
        获取当前页面的滚动位置
        
        Returns:
            dict: 包含x和y坐标的字典
        """
        try:
            logger.info("获取页面滚动位置")
            scroll_x = self.driver.execute_script("return window.pageXOffset;")
            scroll_y = self.driver.execute_script("return window.pageYOffset;")
            position = {"x": scroll_x, "y": scroll_y}
            logger.info(f"页面滚动位置: {position}")
            return position
        except Exception as e:
            logger.error(f"获取页面滚动位置失败: {e}")
            return {"x": 0, "y": 0}

    def scroll(self, direction="down", amount=500):
        """
        滚动页面
        
        Args:
            direction: 滚动方向 ("up" 或 "down")
            amount: 滚动距离（像素）
        """
        try:
            logger.info(f"滚动页面: {direction} {amount}px")
            if direction.lower() == "up":
                amount = -amount
            
            self.driver.execute_script(f"window.scrollBy(0, {amount});")
            time.sleep(0.5)  # 等待滚动完成
            logger.info("页面滚动完成")
        except Exception as e:
            logger.error(f"滚动页面失败: {e}")

    def extract_search_results(self, search_engine):
        """
        提取搜索结果
        
        Args:
            search_engine: 搜索引擎名称
            
        Returns:
            list: 搜索结果列表 (标题、链接和摘要)
        """
        if search_engine.lower() not in SEARCH_ENGINES:
            error_msg = f"不支持的搜索引擎: {search_engine}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        selectors = SEARCH_ENGINES[search_engine.lower()]
        logger.info(f"提取 {search_engine} 搜索结果")
        
        # 等待搜索结果加载
        WebDriverWait(self.driver, BROWSER_CONFIG["explicit_wait"]).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selectors["results"]))
        )
        
        # 获取所有搜索结果
        results = []
        result_elements = self.driver.find_elements(By.CSS_SELECTOR, selectors["results"])
        
        for element in result_elements:
            try:
                title_element = element.find_element(By.CSS_SELECTOR, selectors["title"])
                link_element = element.find_element(By.CSS_SELECTOR, selectors["link"])
                
                title = title_element.text
                link = link_element.get_attribute("href")
                
                # 尝试获取摘要
                try:
                    snippet = element.find_element(By.CSS_SELECTOR, selectors.get("snippet", "div.VwiC3b")).text
                except:
                    snippet = ""
                
                if title and link:
                    results.append({
                        "title": title,
                        "link": link,
                        "snippet": snippet
                    })
            except Exception as e:
                logger.warning(f"提取搜索结果项失败: {e}")
                continue
        
        logger.info(f"成功提取 {len(results)} 个搜索结果")
        return results
    
    def screenshot(self, filename=None):
        """
        截取当前页面的屏幕截图
        
        Args:
            filename: 保存的文件名，如果未提供，将使用时间戳
        """
        if not filename:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.{SCREENSHOT_CONFIG['format']}"
        
        # 如果文件名不包含路径，则使用配置中的保存目录
        if not os.path.dirname(filename):
            filename = os.path.join(SCREENSHOT_CONFIG["save_dir"], filename)
        
        logger.info(f"截取屏幕截图: {filename}")
        self.driver.save_screenshot(filename)
        return filename
        
    def close(self):
        """关闭浏览器"""
        if self.driver:
            logger.info("关闭浏览器")
            self.driver.quit()


# 示例用法
if __name__ == "__main__":
    try:
        # 初始化浏览器自动化
        browser = BrowserAutomation(headless=False)
        
        # 在百度上搜索
        browser.search("baidu", "Python自动化")
        
        # 提取搜索结果
        results = browser.extract_search_results("baidu")
        
        # 打印结果
        print("搜索结果:")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']}")
            print(f"   链接: {result['link']}")
            print()
        
        # 点击第一个结果
        if results:
            browser.navigate_to(results[0]["link"])
            
        # 等待查看结果
        time.sleep(5)
        
        # 截图
        browser.screenshot()
        
    finally:
        # 确保浏览器被关闭
        browser.close() 