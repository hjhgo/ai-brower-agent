#!/usr/bin/env python3
"""
AI驱动的浏览器自动化工具
使用deepseek-r1模型通过OpenAI兼容接口来规划和执行浏览器自动化任务
"""

import json
import time
import logging
import re
import argparse
import os
from typing import List, Dict, Any, Optional, Union
import openai

from openai import OpenAI
from browser_automation import BrowserAutomation
from config import BROWSER_CONFIG, LOG_CONFIG

from apis import apis_url

# 配置日志
logging.basicConfig(
    level=getattr(logging, LOG_CONFIG["level"]),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=LOG_CONFIG["file"] if LOG_CONFIG.get("file") else None
)
logger = logging.getLogger("ai_browser_automation")

# OpenAI兼容接口配置
OPENAI_API_BASE = "http://192.168.59.109:37299/v1"
OPENAI_API_KEY = "EMPTY"
MODEL = "deepseek-r1"

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_API_BASE,
)

class AIBrowserAutomation:
    """AI驱动的浏览器自动化类"""

    def __init__(self, model_name="openai", verbose=True):
        """
        初始化AI浏览器自动化
        
        参数:
            model_name: 使用的AI模型名称
            verbose: 是否启用详细日志
        """
        self.model_name = model_name
        self.verbose = verbose
        self.browser = BrowserAutomation()
        self.setup_model()
        logger.info(f"已初始化AI浏览器自动化 (模型: {model_name})")

    def setup_model(self):
        """设置AI模型"""
        if self.model_name == "openai":
            # 从环境变量获取API密钥
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("未设置OPENAI_API_KEY环境变量")
            openai.api_key = api_key
            logger.info("已设置OpenAI模型")

        elif self.model_name == "deepseek-r1":
            # 从环境变量获取API密钥
            # api_key = os.environ.get("DEEPSEEK_API_KEY")
            # if not api_key:
            #     raise ValueError("未设置DEEPSEEK_API_KEY环境变量")
            # os.environ["DEEPSEEK_API_KEY"] = api_key
            os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
            logger.info("已设置Deepseek模型")
        else:
            raise ValueError(f"不支持的模型: {self.model_name}")

    def generate_browser_plan(self, task_description: str) -> List[Dict[str, Any]]:
        """
        根据任务描述生成浏览器自动化计划

        参数:
            task_description: 任务描述

        返回:
            自动化步骤列表
        """
        system_prompt = f"""你是一个浏览器自动化专家。根据用户的任务描述，生成一个浏览器自动化计划。
计划应该是一系列明确的步骤，每一步都是一个特定的浏览器操作。
你的回应必须是一个有效的JSON数组，每个数组项是一个操作对象。

支持的操作类型包括:
{apis_url}

你的回应必须只包含JSON数组，不要包含任何其他解释或文本。
确保生成的JSON是有效的，每个操作都有正确的参数。
"""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                if self.verbose:
                    logger.info(f"尝试生成计划 (第{attempt + 1}次尝试)")

                # 根据不同模型调用不同的API
                if self.model_name == "openai":
                    pass
                elif self.model_name == "deepseek-r1":
                    response = client.chat.completions.create(
                        model="deepseek-r1",

                        messages=[
                            {
                                "role": "system",
                                "content": system_prompt
                            },
                            {
                                "role": "user",
                                "content": task_description
                            }
                        ],
                        temperature=0.7,
                    )

                    response_text = response.choices[0].message.content


                if self.verbose:
                    logger.info(f"原始响应: {response_text}")

                # 清理响应，提取JSON部分
                clean_response = self._clean_response(response_text)

                # 解析JSON
                plan = json.loads(clean_response)

                # 验证计划的基本结构
                if not isinstance(plan, list):
                    raise ValueError("计划必须是一个列表")

                if len(plan) == 0:
                    raise ValueError("计划不能为空")

                for step in plan:
                    if not isinstance(step, dict) or "action" not in step:
                        raise ValueError("每个步骤必须是一个包含'action'键的字典")

                if self.verbose:
                    logger.info(f"生成的计划: {json.dumps(plan, ensure_ascii=False, indent=2)}")

                return plan

            except Exception as e:
                logger.warning(f"生成计划失败 (第{attempt + 1}次尝试): {str(e)}")

                # 如果是最后一次尝试，尝试手动构建一个基本计划
                if attempt == max_retries - 1:
                    logger.warning("尝试手动构建基本计划")

                    # 基于任务描述构建一个简单的计划
                    try:
                        return self._construct_basic_plan(task_description)
                    except Exception as e2:
                        logger.error(f"手动构建计划失败: {str(e2)}")

        logger.error("所有尝试均失败，返回空计划")
        return []

    def _clean_response(self, response_text: str) -> str:
        """
        清理模型响应，提取JSON部分
        
        参数:
            response_text: 原始响应文本
            
        返回:
            清理后的JSON字符串
        """
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

    def _construct_basic_plan(self, task_description: str) -> List[Dict[str, Any]]:
        """
        从任务描述中构建一个基本的计划
        
        参数:
            task_description: 任务描述
            
        返回:
            基本的自动化计划
        """
        plan = []

        # 检查是否是搜索任务
        search_match = re.search(r'(搜索|查询)\s*["\']?([^"\']+)["\']?', task_description)
        if search_match:
            search_term = search_match.group(2).strip()

            # 检查是否指定了搜索引擎
            engine = "google"  # 默认引擎
            if "百度" in task_description or "baidu" in task_description.lower():
                engine = "baidu"
            elif "必应" in task_description or "bing" in task_description.lower():
                engine = "bing"

            # 添加搜索步骤
            plan.append({
                "action": "search",
                "query": search_term,
                "search_engine": engine
            })

            # 如果任务中提到了提取结果，添加提取步骤
            if "提取" in task_description or "获取" in task_description or "extract" in task_description.lower():
                plan.append({
                    "action": "extract_search_results",
                    "search_engine": engine
                })

            return plan

        # 检查是否是访问网站任务
        url_match = re.search(
            r'(访问|打开|导航到)\s*["\']?((?:https?:\/\/)?[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:/?#[\]@!\$&\'\(\)\*\+,;=.]+)["\']?',
            task_description)
        if url_match:
            url = url_match.group(2).strip()

            # 确保URL以http或https开头
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            # 添加导航步骤
            plan.append({
                "action": "navigate_to",
                "url": url
            })

            return plan

        # 如果无法识别特定任务，返回一个默认的计划
        plan.append({
            "action": "navigate_to",
            "url": "https://www.google.com"
        })
        plan.append({
            "action": "input_text",
            "selector": "input[name='q']",
            "text": task_description
        })

        return plan

    def _generate_next_step(self, context: Dict[str, Any], browser_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        根据浏览器工具调用返回内容生成下一步调用函数
        
        参数:
            context: 当前执行上下文
            browser_result: 浏览器工具调用返回的结果
            
        返回:
            下一步操作的步骤定义
        """

        system_prompt = f"""你是一个浏览器自动化专家。请根据当前执行结果和上下文，生成下一步的浏览器操作步骤。
你可以生成以下类型的操作：
{apis_url}

请基于以下信息生成下一步操作：
- 任务描述
- 已完成的步骤
- 当前步骤的结果
- 浏览器返回的内容
- 整体执行进度

你的回应必须是一个有效的JSON对象，包含action字段和必要的参数。
"""

        # 构建生成请求
        generation_request = {
            "task_description": context["task_description"],
            "completed_steps": context["completed_steps"],
            "current_step": context["current_step"],
            "browser_result": browser_result
        }

        try:
            response = client.chat.completions.create(
                model="deepseek-r1",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(generation_request,
                                                           ensure_ascii=False)}
                ],
                temperature=0.7,
            )
            
            next_step = response.choices[0].message.content.strip()

            # 解析json
            next_step = self._clean_response(next_step)
            
            # 尝试解析为JSON
            try:
                step = json.loads(next_step)
                if not isinstance(step, dict) or "action" not in step:
                    logger.warning(f"生成的步骤格式无效: {next_step}")
                    return None
                return step
            except json.JSONDecodeError:
                logger.warning(f"无法解析生成的步骤: {next_step}")
                return None
                
        except Exception as e:
            logger.error(f"生成下一步操作时出错: {str(e)}")
            return None

    def _execute_single_step(self, step: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        执行单个步骤
        
        参数:
            step: 要执行的步骤
            
        返回:
            执行结果
        """
        action = step.get("action")
        
        if action == "navigate_to":
            url = step.get("url")
            if url:
                self.browser.navigate_to(url)
                logger.info(f"已导航到: {url}")
                return {"action": "navigate_to",
                        "url": url,
                        "status": "success",
                        "page_title": self.browser.get_page_title()}
            logger.warning("navigate_to步骤缺少url参数")
            
        elif action == "search":
            query = step.get("query")
            engine = step.get("search_engine", "google")
            if query:
                self.browser.search(engine, query)
                logger.info(f"已在{engine}上搜索: {query}")
                return {
                    "action": "search", 
                    "query": query, 
                    "engine": engine, 
                    "status": "success",
                    "page_title": self.browser.get_page_title(),
                    "search_results": self.browser.get_search_results()
                }
            logger.warning("search步骤缺少query参数")
            
        elif action == "click_element":
            selector = step.get("selector")
            if selector:
                success = self.browser.click_element(selector)
                if success:
                    logger.info(f"已点击元素: {selector}")
                    return {
                        "action": "click_element", 
                        "selector": selector, 
                        "status": "success",
                        "page_title": self.browser.get_page_title(),
                        "element_text": self.browser.get_element_text(selector)
                    }
                logger.warning(f"无法点击元素: {selector}")
            logger.warning("click_element步骤缺少selector参数")
            
        elif action == "input_text":
            selector = step.get("selector")
            text = step.get("text")
            if selector and text:
                success = self.browser.input_text(selector, text)
                if success:
                    logger.info(f"已在{selector}中输入文本: {text}")
                    return {
                        "action": "input_text", 
                        "selector": selector, 
                        "text": text, 
                        "status": "success",
                        "page_title": self.browser.get_page_title(),
                        "input_value": self.browser.get_input_value(selector)
                    }
                logger.warning(f"无法在{selector}中输入文本")
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
                        "page_title": self.browser.get_page_title()
                    }
                logger.warning(f"未找到元素: {selector}")
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
                    "page_title": self.browser.get_page_title()
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
                "page_title": self.browser.get_page_title(),
                "scroll_position": self.browser.get_scroll_position()
            }
            
        elif action == "wait":
            seconds = step.get("seconds", 3)
            logger.info(f"等待 {seconds} 秒")
            time.sleep(seconds)
            return {
                "action": "wait", 
                "seconds": seconds, 
                "status": "success",
                "page_title": self.browser.get_page_title()
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
                "page_title": self.browser.get_page_title()
            }
            
        else:
            logger.warning(f"不支持的操作: {action}")
        
        return None

    def execute_task(self, task_description: str) -> Optional[List[Dict[str, Any]]]:

        logger.info(f"执行任务: {task_description}")


        # 当前状态
        results = []
        current_step = "无"
        step_result = "无"
        current_i = 0
        context = {
            "task_description": task_description,
            "completed_steps": [],
            "current_step": current_step,
            "results": results
        }

        while True:

            try:
                # 执行当前步骤
                current_i += 1
                current_step = self._generate_next_step(context, step_result)

                action = current_step.get("action")

                logger.info(f"执行步骤 {current_i}: {action}")
                step_result = self._execute_single_step(current_step)

                if step_result:
                    results.append(step_result)
                
                # 更新上下文
                context["completed_steps"].append({
                    "step": current_step,
                    "result": step_result
                })

                context["current_step"] = current_step
                context["results"] = results

                # 根据浏览器返回结果生成下一步



            except Exception as e:

                logger.error(f"执行步骤 {current_step} 时出错: {str(e)}")
                # 询问AI如何处理错误
                error_handling = self._handle_step_error(context, str(e))
                if error_handling == "retry":
                    continue
                elif error_handling == "skip":
                    current_step += 1
                else:
                    break

            # 每个步骤后短暂等待
            time.sleep(1)

        logger.info("任务执行完成")
        return results if results else None

    def _evaluate_step_result(self, context: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """
        评估步骤执行结果并决定下一步操作
        
        参数:
            context: 当前执行上下文
            
        返回:
            "continue": 继续执行下一步
            "retry": 重试当前步骤
            "stop": 停止执行
            Dict: 新的步骤
        """
        system_prompt = """你是一个浏览器自动化专家。请评估当前步骤的执行结果，并决定下一步操作。
你可以选择：
1. 继续执行下一步（返回 "continue"）
2. 重试当前步骤（返回 "retry"）
3. 停止执行（返回 "stop"）
4. 添加新的步骤（返回一个步骤对象）

请基于以下信息做出决策：
- 任务描述
- 已完成的步骤
- 当前步骤的结果
- 整体执行进度
"""

        # 构建评估请求
        evaluation_request = {
            "task_description": context["task_description"],
            "completed_steps": context["completed_steps"],
            "current_step": context["current_step"],
            "results": context["results"]
        }

        try:
            response = client.chat.completions.create(
                model="deepseek-r1",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(evaluation_request, ensure_ascii=False)}
                ],
                temperature=0.7,
            )
            
            decision = response.choices[0].message.content.strip()
            
            # 解析决策
            if decision.lower() in ["continue", "retry", "stop"]:
                return decision.lower()
            
            # 尝试解析为JSON（新步骤）
            try:
                return json.loads(decision)
            except json.JSONDecodeError:
                logger.warning(f"无法解析AI决策: {decision}")
                return "continue"
                
        except Exception as e:
            logger.error(f"评估步骤结果时出错: {str(e)}")
            return "continue"

    def _handle_step_error(self, context: Dict[str, Any], error: str) -> str:
        """
        处理步骤执行错误
        
        参数:
            context: 当前执行上下文
            error: 错误信息
            
        返回:
            "retry": 重试当前步骤
            "skip": 跳过当前步骤
            "stop": 停止执行
        """
        system_prompt = """你是一个浏览器自动化专家。请评估当前步骤的执行错误，并决定如何处理。
你可以选择：
1. 重试当前步骤（返回 "retry"）
2. 跳过当前步骤（返回 "skip"）
3. 停止执行（返回 "stop"）

请基于以下信息做出决策：
- 任务描述
- 已完成的步骤
- 错误信息
- 整体执行进度
"""

        # 构建错误处理请求
        error_request = {
            "task_description": context["task_description"],
            "completed_steps": context["completed_steps"],
            "current_step": context["current_step"],
            "error": error
        }

        try:
            response = client.chat.completions.create(
                model="deepseek-r1",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(error_request, ensure_ascii=False)}
                ],
                temperature=0.7,
            )
            
            decision = response.choices[0].message.content.strip().lower()
            
            if decision in ["retry", "skip", "stop"]:
                return decision
            
            logger.warning(f"无法解析AI错误处理决策: {decision}")
            return "skip"
                
        except Exception as e:
            logger.error(f"处理步骤错误时出错: {str(e)}")
            return "skip"

    def ask_ai(self, query: str, system_prompt: Optional[str] = None) -> str:
        """
        向AI模型提问

        参数:
            query: 用户问题
            system_prompt: 系统提示，用于指导AI回答方向

        返回:
            AI回答
        """
        if not system_prompt:
            system_prompt = """你是一个专业的浏览器自动化助手。
请简洁明了地回答用户关于浏览器自动化的问题。
"""

        try:
            if self.verbose:
                logger.info(f"向AI提问: {query}")

            # 根据不同模型调用不同的API
            if self.model_name == "openai":
                response = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    temperature=0.7,
                )
                answer = response.choices[0].message.content
            elif self.model_name == "deepseek-r1":
                try:
                    import deepseek
                    client = deepseek.Client()
                    response = client.chat.completions.create(
                        model="deepseek-r1",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": query}
                        ],
                        temperature=0.7,
                    )
                    answer = response.choices[0].message.content
                except ImportError:
                    raise ImportError("请先安装deepseek Python库")
            else:
                raise ValueError(f"不支持的模型: {self.model_name}")

            if self.verbose:
                logger.info(f"AI回答: {answer}")

            return answer

        except Exception as e:
            error_msg = f"AI回答出错: {str(e)}"
            logger.error(error_msg)
            return f"抱歉，我遇到了问题: {str(e)}"

    def close(self):
        """关闭浏览器"""
        if hasattr(self, 'browser') and self.browser:
            self.browser.close()
            logger.info("浏览器已关闭")


def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description="AI驱动的浏览器自动化工具")
    parser.add_argument("task", nargs="?", help="要执行的自动化任务描述")
    parser.add_argument("--headless", action="store_true", help="使用无头模式（不显示浏览器界面）")
    parser.add_argument("--browser", choices=["chrome", "firefox"], default=BROWSER_CONFIG["browser_type"],
                        help="浏览器类型")
    parser.add_argument("--temperature", type=float, default=0.7, help="AI模型温度参数 (0.0-1.0)")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细信息")

    args = parser.parse_args()

    if not args.task:
        # 交互式模式
        print("AI驱动的浏览器自动化工具")
        print("输入 'exit' 或 'quit' 退出")
        print()

        ai_automation = AIBrowserAutomation(
            model_name="deepseek-r1",
            verbose=args.verbose
        )

        while True:
            try:
                task = input("\n请输入要执行的任务 (exit 退出): ")
                if task.lower() in ("exit", "quit"):
                    break

                if not task:
                    continue

                summary = ai_automation.execute_task(task)
                print("\n任务总结:")
                print(summary)

            except KeyboardInterrupt:
                print("\n收到中断信号，退出...")
                break

            except Exception as e:
                print(f"发生错误: {e}")
    else:
        # 直接执行任务
        ai_automation = AIBrowserAutomation(
            model_name=args.browser,
            verbose=args.verbose
        )

        summary = ai_automation.run(args.task)
        print("\n任务总结:")
        print(summary)


if __name__ == "__main__":
    main()
