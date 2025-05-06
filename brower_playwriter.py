import json
import re

from openai import OpenAI

apis_url = """
1. navigate_to: 导航到特定URL
   示例: {"action": "navigate_to", "url": "https://www.example.com"}

2. click_element: 通过来点击一个可点击区域, selector_type可选 id, css, xpath
   示例: {"action": "click_element", "selector": "su", "selector_type":"id"}

3. input_text: 在输入框中输入文本, selector_type可选 id, css, xpath
   示例: {"action": "input_text", "selector": "#search-box", "selector_type":"css" "text": "搜索内容"}

4. enter_input: 在输入框中输入文本，并进行enter，  selector_type可选 id, css, xpath
   示例: {"action": "enter_input", "selector": "#search-box", "selector_type":"css" "text": "搜索内容"}

5. wait: 等待
   示例: {"action": "wait", "seconds": 3}

6. screenshot: 截图
   示例: {"action": "screenshot", "filename": "search_results.png"}

7. stop: 结束
   示例: {"action": "stop", "summary": "任务总结"}
"""


def get_xpath(element):
    """生成元素的近似XPath"""
    return element.evaluate('''el => {
        if (el.id) return `//*[@id="${el.id}"]`;
        let path = [];
        while (el.nodeType === Node.ELEMENT_NODE) {
            let selector = el.tagName.toLowerCase();
            if (el.id) {
                path.unshift(`//${selector}[@id="${el.id}"]`);
                break;
            } else {
                let sib = el, nth = 1;
                while (sib = sib.previousElementSibling) {
                    if (sib.tagName === el.tagName) nth++;
                }
                selector += nth > 1 ? `[${nth}]` : '';
            }
            path.unshift(selector);
            el = el.parentNode;
        }
        return '/' + path.join('/');
    }''')


def build_element_prompt(user_instruction: str, elements: list) -> str:
    """构建给AI的提示词"""
    elements_str = "\n".join([
        f"{idx}: {elem['tag']} | 文本: {elem['text']} | 类: {elem['classes']} | ID: {elem['id']} | XPath: {elem['xpath']}"
        for idx, elem in enumerate(elements)
    ])

    return f"""根据当前页面元素信息，完成用户指令：

用户指令：{user_instruction}

页面元素列表：
{elements_str}

请用JSON格式返回操作步骤，包含以下字段：
- action (必填): goto/click/type/wait
- selector_type (可选): css/xpath/text
- selector (必填): 选择器表达式
- text (仅type操作需要): 输入内容
- confidence (0-1): 选择置信度

示例：
{{"action": "click", "selector_type": "xpath", "selector": "//button[contains(text(),'搜索')]", "confidence": 0.9}}"""


_MODEL_NAME_ = "/home/Qwen2___5-72B-Instruct-GPTQ-Int4"
OPENAI_API_BASE = "http://192.168.59.104:31245/v1"
OPENAI_API_KEY = "EMPTY"
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_API_BASE,
)

from playwright.sync_api import sync_playwright
from typing import Optional, Tuple



def generate_selector_actions(messages: list) -> list:
    response = client.chat.completions.create(
        model=_MODEL_NAME_,
        messages=messages,
        temperature=0.6,
        top_p=0.6
    )

    response_text = response.choices[0].message.content

    response_text = re.sub(r'<think>([\s\S]*?)</think>', '', response_text)

    # 尝试提取开头和结尾的 ```json 和 ``` 标记之间的内容
    json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    match = re.search(json_pattern, response_text)
    if match:
        return match.group(1).strip()

    # 尝试提取 [ 和 ] 之间的JSON数组
    array_pattern = r'(\[\s*\{.*\}\s*\])'
    match = re.search(array_pattern, response_text, re.DOTALL)
    if match:
        return match.group(1).strip()

        # 如果没有找到明确的JSON标记，假设整个回复都是JSON
    return response_text.strip()


class Browser:
    def __init__(
            self,
            headless: bool = True,
            slow_mo: int = 0,
            timeout: int = 30000,
            browser_type: str = "chromium"
    ):
        """
        初始化浏览器实例
        :param headless: 是否无头模式
        :param slow_mo: 操作延迟（毫秒）
        :param timeout: 默认超时时间（毫秒）
        :param browser_type: 浏览器类型（chromium/firefox/webkit）
        """
        self.playwright = sync_playwright().start()
        self.browser = getattr(self.playwright, browser_type).launch(
            headless=headless,
            slow_mo=slow_mo
        )
        self.page = self.browser.new_page()
        self.page.set_default_timeout(timeout)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_element(self, selector_type="id", selector=""):
        if selector_type == "id":
            if not selector.startswith("#"):
                selector = "#"+selector
            return self.page.locator(selector)
        if selector_type == "xpath":
            return self.page.locator(f"xpath={selector}")
        else:
            return self.page.locator(selector)

    def navigate(self, url: str) -> Tuple[bool, str]:
        """导航到指定URL"""
        try:
            self.page.goto(url)
            return True, "导航成功"
        except Exception as e:
            return False, f"导航失败: {str(e)}"

    def input(self, selector: str, text: str,  selector_type="id", clear: bool = True, check_input_type=True) -> Tuple[bool, str]:
        """
        在指定输入框输入文本
        :param selector: CSS选择器
        :param text: 要输入的文本
        :param clear: 是否先清空输入框
        """

        try:
            element = self.get_element(selector_type=selector_type, selector=selector)

            # 检查是否为<input>元素（可选）
            if check_input_type:
                tag_name = element.evaluate("el => el.tagName.toLowerCase()")
                if tag_name != "input":
                    return False, f"目标元素不是<input>，而是<{tag_name}>"

            if clear:
                element.clear()
            element.fill(text)
            return True, "输入成功"
        except Exception as e:
            return False, f"输入失败: {str(e)}"

    def enter_input(
            self,
            selector: str,
            text: str,
            selector_type: str = "id",
            press_enter: bool = True,  # 是否输入后按回车
            input_type: Optional[str] = None  # 验证<input type="...">（如"text"/"password"）
    ) -> Tuple[bool, str]:
        """
        专门处理<input>元素的输入
        :param press_enter: 输入后是否按回车键
        :param input_type: 验证<input>的type属性（可选）
        """
        try:
            element = self.get_element(selector_type=selector_type, selector=selector)

            # 验证元素是<input>且type匹配
            tag_name = element.evaluate("el => el.tagName.toLowerCase()")
            if tag_name != "input" and tag_name != "textarea":
                return False, f"元素不是<input>，而是<{tag_name}>"

            if input_type:
                actual_type = element.get_attribute("type") or "text"
                if actual_type != input_type:
                    return False, f"<input>类型应为'{input_type}'，实际是'{actual_type}'"

            element.clear()
            element.fill(text)

            if press_enter:
                element.press("Enter")

            return True, "输入成功"
        except Exception as e:
            return False, f"输入失败: {str(e)}"

    def click(self, selector_type="id", selector: str="", delay: int = 20) -> Tuple[bool, str]:
        """
        点击指定元素
        :param selector: CSS选择器
        :param delay: 点击后等待时间（毫秒）
        """
        try:
            element = self.get_element(selector_type=selector_type, selector=selector)
            element.click(delay=delay)
            return True, "点击成功"
        except Exception as e:
            return False, f"点击失败: {str(e)}"

    def type_text(self, selector: str, text: str, selector_type="id", delay: int = 100) -> Tuple[bool, str]:
        """
        模拟键盘输入（带延迟）
        :param selector: CSS选择器
        :param text: 要输入的文本
        :param delay: 每个字符输入间隔（毫秒）
        """
        try:
            element = self.get_element(selector_type=selector_type, selector=selector)
            element.type(text, delay=delay)
            return True, "输入成功"
        except Exception as e:
            return False, f"输入失败: {str(e)}"

    def wait_for_selector(self, selector: str, timeout: Optional[int] = None) -> Tuple[bool, str]:
        """等待元素出现"""
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            return True, "元素已找到"
        except Exception as e:
            return False, f"等待元素超时: {str(e)}"

    def get_page_content(self) -> str:
        """获取当前页面HTML内容"""
        return self.page.content()

    def screenshot(self, path: str = "screenshot.png") -> Tuple[bool, str]:
        """截取页面截图"""
        try:
            self.page.screenshot(path=path)
            return True, "截图成功"
        except Exception as e:
            return False, f"截图失败: {str(e)}"

    def close(self):
        """关闭浏览器"""
        self.browser.close()
        self.playwright.stop()

    def get_page_text(self, include_hidden: bool = False) -> str:
        """
        获取当前页面的纯文本内容（过滤HTML标签）
        :param include_hidden: 是否包含隐藏元素的文本
        :return: 纯文本字符串
        """
        if include_hidden:
            return self.page.text_content('body') or ''
        return self.page.inner_text('body') or ''


    def get_page_elements(self) -> list:
        """获取页面可见元素的关键信息"""

        elements = self.page.query_selector_all('body *:visible')
        element_data = []

        for idx, element in enumerate(elements[:50]):  # 限制数量防止信息过载
            try:
                data = {
                    "index": idx,
                    "tag": element.evaluate("el => el.tagName.toLowerCase()"),
                    "text": element.text_content().strip()[:50],
                    "classes": element.get_attribute("class") or "",
                    "id": element.get_attribute("id") or "",
                    "xpath": get_xpath(element),
                    "is_clickable": element.is_enabled(),
                    "bounding_box": element.bounding_box()
                }
                element_data.append(data)
            except:
                continue

            # browser.close()
        return element_data


def execute_ai_instruction(url, user_instruction):
    # 获取页面元素
    with Browser(headless=False, slow_mo=100) as browser:
        success, message = browser.navigate("https://www.baidu.com")
        print(f"导航结果: {success} - {message}")

        elements  = browser.get_page_elements()

        # 生成AI提示
        prompt = build_element_prompt(user_instruction, elements)

        # 获取AI指令
        messages = [{
            "role": "system",
            "content": """你是一个专业的网页自动化助手，需要准确识别页面元素并生成可靠的选择器"""
        }, {
            "role": "user",
            "content": prompt
        }]

        actions = generate_selector_actions(messages)

        actions = json.loads(actions)

        # locator = SmartLocator(page)

        for action in actions:
            print(action)
            if action["action"] == "click":
                success,text = browser.click(
                    selector=action["selector"],
                    selector_type=action["selector_type"]
                )
                if not success:
                    raise Exception(f"元素定位失败：{action['selector']}")
            elif action["action"] == "type":
                success,text = browser.type_text(
                    selector=action["selector"],
                    selector_type=action["selector_type"],
                    text=action["text"])
                # page.type(action["selector"], action["text"])
                if not success:
                    raise Exception(f"元素定位失败：{action['selector']}")


if __name__ == '__main__':
    execute_ai_instruction("",
                           user_instruction="搜索世界上最高的山")
