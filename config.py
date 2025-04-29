"""
浏览器自动化工具的配置文件
可根据需要修改环境设置
"""

# 浏览器设置
BROWSER_CONFIG = {
    # 浏览器类型: "chrome" 或 "firefox"
    "browser_type": "chrome",
    
    # 是否使用无头模式（不显示浏览器界面）
    "headless": False,
    
    # 用户数据目录，可以保存登录状态等信息
    # 例如: "/home/user/.config/chrome-profile"
    "user_data_dir": None,
    
    # 等待时间（秒）
    "implicit_wait": 10,
    "explicit_wait": 15,
}

# 搜索引擎设置
SEARCH_ENGINES = {
    "google": {
        "url": "https://www.google.com",
        "input_selector": "textarea[name='q']",
        "results": "div.g",
        "title": "h3",
        "link": "a",
    },
    "baidu": {
        "url": "https://www.baidu.com",
        "input_selector": "#kw",
        "results": ".result.c-container",
        "title": "h3",
        "link": "h3 a",
    },
    "bing": {
        "url": "https://www.bing.com",
        "input_selector": "#sb_form_q",
        "results": ".b_algo",
        "title": "h2",
        "link": "h2 a",
    }
}

# 代理设置（如果需要）
PROXY_CONFIG = {
    "use_proxy": False,
    "http_proxy": "",
    "https_proxy": "",
    "no_proxy": "localhost,127.0.0.1"
}

# 截图设置
SCREENSHOT_CONFIG = {
    "save_dir": "./screenshots",
    "format": "png"
}

# 日志设置
LOG_CONFIG = {
    "level": "INFO",  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    # "file": "browser_automation.log",
    "max_size": 10 * 1024 * 1024,  # 10MB
    "backup_count": 3
}

# 天气抓取设置
WEATHER_CONFIG = {
    "save_dir": "./weather_data",
    "update_interval": 3600  # 更新间隔（秒）
} 