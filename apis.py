
apis_url = """1. navigate_to: 导航到特定URL
   示例: {"action": "navigate_to", "url": "https://www.example.com"}

2. search: 在搜索引擎中搜索
   示例: {"action": "search", "query": "python教程", "search_engine": "google"}
   search_engine可选值: google, baidu, bing

3. click_element: 点击元素
   示例: {"action": "click_element", "selector": "#submit-button"}

4. input_text: 在输入框中输入文本
   示例: {"action": "input_text", "selector": "#search-box", "text": "搜索内容"}

5. extract_content: 提取内容
   示例: {"action": "extract_content", "selector": ".result-item", "attribute": "text"}
   attribute可选值: text, href, src等

6. extract_search_results: 提取搜索结果
   示例: {"action": "extract_search_results", "search_engine": "google"}

7. scroll: 滚动页面
   示例: {"action": "scroll", "direction": "down", "amount": 500}

8. wait: 等待
   示例: {"action": "wait", "seconds": 3}

9. screenshot: 截图
   示例: {"action": "screenshot", "filename": "search_results.png"}"""