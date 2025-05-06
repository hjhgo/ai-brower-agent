import json
import re
import time

from openai import OpenAI

from brower_playwriter import apis_url
from brower_playwriter import Browser

import logging

from config import LOG_CONFIG

logging.basicConfig(
    level=getattr(logging, LOG_CONFIG["level"]),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=LOG_CONFIG["file"] if LOG_CONFIG.get("file") else None
)
logger = logging.getLogger("ai_browser_automation")


class AIBrowser:
    def __init__(self, task_summary = ""):

        self.browser = Browser(headless=False)

        self.init_model()
        self.task_summary = task_summary



    def init_model(self):

        self._MODEL_NAME_ = "/home/Qwen2___5-72B-Instruct-GPTQ-Int4"
        OPENAI_API_BASE = "http://192.168.59.104:31245/v1"
        OPENAI_API_KEY = "EMPTY"
        self.client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_API_BASE,
        )

    def _clean_response(self, response_text: str) -> str:

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


    def request_from_model(self, messages, temperature=0.6, top_p=0.6):

        response = self.client.chat.completions.create(
            model=self._MODEL_NAME_,
            messages=messages,
            temperature=temperature,
            top_p=top_p
        )

        content =  response.choices[0].message.content

        content = self._clean_response(content)

        return content



    def next_action(self,
                    task_summary ,
                    action_commpletion,
                    action_summary):
        system_prompt = f"""你是一个任务执行专家, 现在给你提供一些浏览器工具去完成任务。

你可以进行以下类型的动作：
{apis_url}

请基于任务已经执行的信息生成下一步的动作：
# 输入信息
- 任务描述 
- 已完成的动作情况 
- 当前任务总结

# 输出要求
- 如果已经完成任务或者评估已经无法完成任务，请返回stop 动作，给出总结
- 请严格按json结构进行返回
"""
        prompt = f"""任务描述:{task_summary}
已完成动作: {action_commpletion}
当前任务总结: {action_summary}
"""

        messages = []
        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        ret = self.request_from_model(messages=messages)
        return ret


    def do_action(self, step):
        """
        do action reteturn page_content
        """
        action = step.get("action")

        if action == "navigate_to":
            url = step.get("url")
            if url:
                self.browser.navigate(url)
                logger.info(f"已导航到: {url}")
                return {
                    "action": "navigate_to",
                    "url": url,
                    "status": "success",
                }
            logger.warning("navigate_to步骤缺少url参数")

        elif action == "click_element":
            selector = step.get("selector")
            selector_type = step.get("selector_type")
            success, info = self.browser.click(selector_type=selector_type, selector=selector)
            return {
                        "action": "click_element",
                        "selector": selector,
                        "selector_type": selector_type,
                        "success":info
            }

        elif action == "input_text":
            selector = step.get("selector")
            text = step.get("text")
            selector_type = step.get("selector_type")
            if selector and text:
                success , info= self.browser.input(selector=selector, text=text, selector_type=selector_type)
                if success:
                    logger.info(f"已在{selector}中输入文本: {text}")
                else:
                    logger.warning(f"无法在{selector}中输入文本")
            # logger.warning("input_text步骤缺少selector或text参数")
                return {
                    "action": "input_text",
                    "selector": selector,
                    "text": text,
                    "status": info
                }
            logger.warning("input_text步骤缺少selector或text参数")


        elif action == "enter_input":
            selector = step.get("selector")
            text = step.get("text")
            selector_type = step.get("selector_type")
            if selector and text:
                success, info = self.browser.enter_input(selector=selector, text=text, selector_type=selector_type)
                if success:
                    logger.info(f"已在{selector}中输入文本: {text}")
                else:
                    logger.warning(f"无法在{selector}中输入文本, {info}")

                return {
                    "action": "enter_input",
                    "selector": selector,
                    "text": text,
                    "status": info
                }

            logger.warning("input_text步骤缺少selector或text参数")

        elif action == "extract_content":
            selector = step.get("selector")
            attribute = step.get("attribute", "text")
            if selector:
                if attribute == "text":
                    content = self.browser.get_element_text(selector)
                else:
                    content = self.browser.get_elements_attribute(selector, attribute)

                if content:
                    logger.info(f"已提取内容 ({len(content)} 个元素)")
                    return {
                        "action": "extract_content",
                        "selector": selector,
                        "attribute": attribute,
                        "content": content,
                        "status": "success",
                    }
                logger.warning(f"未找到元素: {selector}")

            else:
                logger.warning("extract_content步骤缺少selector参数")

        elif action == "extract_search_results":
            engine = step.get("search_engine", "google")
            search_results = self.browser.extract_search_results(engine)
            if search_results:
                logger.info(f"已提取搜索结果 ({len(search_results)} 个)")
                return {
                    "action": "extract_search_results",
                    "search_engine": engine,
                    "results": search_results,
                    "status": "success",

                }
            logger.warning("未找到搜索结果")

        elif action == "scroll":
            direction = step.get("direction", "down")
            amount = step.get("amount", 500)
            self.browser.scroll(direction, amount)
            logger.info(f"已滚动页面: {direction} {amount}px")
            return {
                "action": "scroll",
                "direction": direction,
                "amount": amount,
                "status": "success",
            }

        elif action == "wait":
            seconds = step.get("seconds", 3)
            logger.info(f"等待 {seconds} 秒")
            time.sleep(seconds)
            return {
                "action": "wait",
                "seconds": seconds,
                "status": "success",
            }

        elif action == "screenshot":
            filename = step.get("filename")
            if not filename:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"

            self.browser.screenshot(filename)
            logger.info(f"已保存截图: {filename}")
            return {
                "action": "screenshot",
                "filename": filename,
                "status": "success",
            }

        else:
            logger.warning(f"不支持的操作: {action}")

        return None

    def one_action_summary(self,task_summary,
                           current_ation,
                           action_commpletion,
                           page_content):
        system_prompt = f"""你是一个任务执行专家, 现在基于任务目标执行了一些动作，总结当前动作的执行情况，保留下一步需要的重要信息

已有的动作如下：
{apis_url}

请基于当前的任务执行情况：
- 任务描述 
- 已完成的动作情况 
- 当前的动作
- 动作返回的页面信息
进行终结，返回摘要内容
"""
        prompt = f"""任务描述: {task_summary}
已完成动作: {action_commpletion}
当前的动作: {current_ation}
动作返回的页面信息: {page_content}

基于以上内容，进行当前的动作总结摘要：
"""

        messages = []
        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        ret = self.request_from_model(messages=messages)
        return ret

    def build_element_prompt(self, page_content:str, elements: list) -> str:

        """构建给AI的提示词"""
        elements_str = "\n".join([
            f"{idx}: {elem['tag']} | 文本: {elem['text']} | 类: {elem['classes']} | ID: {elem['id']} | XPath: {elem['xpath']}"
            for idx, elem in enumerate(elements)
        ])

        return f"""根据当前页面元素信息，完成用户指令：

    页面元素列表：
    {elements_str}
    
    页面文本：
    {page_content}
"""


    def one_by_one_step(self):

        action_completions = []
        steps_index = 0
        task_summary = self.task_summary
        action_summary = ""
        actions = []
        while True:

            steps_index += 1

            step = self.next_action(
                                      task_summary=task_summary,
                                      action_commpletion=action_completions,
                                      action_summary=action_summary,
                                    )
            logger.info(f"第{steps_index}步: {step}")
            step = json.loads(step)
            actions.append(step)

            try:
                if step.get("action") == "stop":
                    self.browser.close()
                    return step.get("summary", "")

                step = self.do_action(step)

                page_content = self.browser.get_page_text()
                page_elements = self.browser.get_page_elements()

                content_page  = self.build_element_prompt(
                        page_content=page_content,
                        elements = page_elements
                )

                action_summary = self.one_action_summary(
                               task_summary=self.task_summary,
                               current_ation=step,
                               action_commpletion=action_completions,
                               page_content=content_page
                )

            except Exception as e:
                action_summary = f"执行动作错误，{e}"

            logger.info(action_summary)
            # step["summary"] = action_summary
            action_completions.append(step)

            time.sleep(1)


    def excute_task(self,actions):

        for action in actions:
            print(action)

            step = self.do_action(action)
            print(step)
            time.sleep(1)
        time.sleep(10000)

    def run(self):
        ret = self.one_by_one_step()
        logger.info(f"已完成任务：, {ret}")

if __name__ == '__main__':
    brower_agent = AIBrowser("使用百度，世界上最高的山峰")
    brower_agent.run()
    # actions = [
    #            {"action": "navigate_to", "url": "https://www.google.com"},
    #            {"action": "enter_input", "selector": "APjFqb", "selector_type": "id", "text": "世界上最高的山峰"},
    #            ]
    #
    # brower_agent.excute_task(actions=actions)