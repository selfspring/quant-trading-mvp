# Apify Web Scraping Skill

使用 Apify 平台进行网页抓取、数据提取和网页自动化。

## 功能

- 使用 Apify Actors 进行网页抓取
- 提取结构化数据
- 自动化浏览器操作
- 处理动态内容和 JavaScript 渲染
- 大规模数据采集

## 前置条件

1. **Apify 账号**
   - 注册：https://apify.com/
   - 获取 API Token：https://console.apify.com/account/integrations

2. **安装 Apify SDK**
   ```bash
   pip install apify-client
   ```

3. **配置环境变量**
   ```bash
   # 在 .env 文件中添加
   APIFY_API_TOKEN=your_api_token_here
   ```

## 基本用法

### 1. 初始化客户端

```python
from apify_client import ApifyClient

# 从环境变量读取 token
import os
client = ApifyClient(os.getenv('APIFY_API_TOKEN'))
```

### 2. 运行 Actor（预构建的爬虫）

```python
# 运行 Google Search Results Scraper
run_input = {
    "queries": "OpenAI GPT-4",
    "maxPagesPerQuery": 1,
    "resultsPerPage": 10
}

run = client.actor("apify/google-search-scraper").call(run_input=run_input)

# 获取结果
for item in client.dataset(run["defaultDatasetId"]).iterate_items():
    print(item)
```

### 3. 常用 Actors

#### Google Search Scraper
```python
run_input = {
    "queries": "量化交易 Python",
    "maxPagesPerQuery": 3,
    "resultsPerPage": 100
}
run = client.actor("apify/google-search-scraper").call(run_input=run_input)
```

#### Web Scraper
```python
run_input = {
    "startUrls": [{"url": "https://example.com"}],
    "pageFunction": """
        async function pageFunction(context) {
            const { page, request } = context;
            const title = await page.title();
            return { title, url: request.url };
        }
    """
}
run = client.actor("apify/web-scraper").call(run_input=run_input)
```

#### Instagram Scraper
```python
run_input = {
    "usernames": ["openai"],
    "resultsLimit": 50
}
run = client.actor("apify/instagram-scraper").call(run_input=run_input)
```

### 4. 自定义爬虫

```python
from apify import Actor

async def main():
    async with Actor:
        # 获取输入
        actor_input = await Actor.get_input() or {}
        urls = actor_input.get('urls', [])
        
        # 抓取数据
        for url in urls:
            # 使用 requests 或 playwright
            data = await scrape_url(url)
            
            # 保存到 dataset
            await Actor.push_data(data)
```

## 高级功能

### 1. 使用代理

```python
run_input = {
    "startUrls": [{"url": "https://example.com"}],
    "proxyConfiguration": {
        "useApifyProxy": True,
        "apifyProxyGroups": ["RESIDENTIAL"]
    }
}
```

### 2. 处理分页

```python
run_input = {
    "startUrls": [{"url": "https://example.com/page/1"}],
    "maxCrawlDepth": 5,
    "maxCrawlPages": 100
}
```

### 3. 数据导出

```python
# 导出为 JSON
dataset = client.dataset(run["defaultDatasetId"])
data = dataset.list_items().items

# 导出为 CSV
import csv
with open('output.csv', 'w', newline='', encoding='utf-8') as f:
    if data:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
```

## 实用示例

### 示例1：抓取新闻网站

```python
from apify_client import ApifyClient
import os

client = ApifyClient(os.getenv('APIFY_API_TOKEN'))

# 抓取新浪财经黄金新闻
run_input = {
    "startUrls": [
        {"url": "https://finance.sina.com.cn/money/future/"}
    ],
    "pageFunction": """
        async function pageFunction(context) {
            const { page } = context;
            const articles = await page.$$eval('.news-item', items => {
                return items.map(item => ({
                    title: item.querySelector('h3')?.textContent,
                    link: item.querySelector('a')?.href,
                    time: item.querySelector('.time')?.textContent
                }));
            });
            return articles;
        }
    """
}

run = client.actor("apify/web-scraper").call(run_input=run_input)
```

### 示例2：监控价格变化

```python
# 定期运行 Actor 监控价格
run_input = {
    "startUrls": [{"url": "https://example.com/product"}],
    "pageFunction": """
        async function pageFunction(context) {
            const { page } = context;
            const price = await page.$eval('.price', el => el.textContent);
            return { price, timestamp: new Date().toISOString() };
        }
    """
}

# 设置定时任务（每小时运行一次）
schedule = client.schedules().create(
    actor_id="apify/web-scraper",
    cron_expression="0 * * * *",
    input=run_input
)
```

### 示例3：批量数据采集

```python
# 批量抓取多个 URL
urls = [
    "https://example.com/page1",
    "https://example.com/page2",
    "https://example.com/page3"
]

run_input = {
    "startUrls": [{"url": url} for url in urls],
    "maxConcurrency": 10  # 并发数
}

run = client.actor("apify/web-scraper").call(run_input=run_input)
```

## 最佳实践

### 1. 错误处理

```python
try:
    run = client.actor("apify/web-scraper").call(run_input=run_input)
    
    # 检查运行状态
    if run["status"] == "SUCCEEDED":
        data = client.dataset(run["defaultDatasetId"]).list_items().items
    else:
        print(f"Actor failed: {run['status']}")
        
except Exception as e:
    print(f"Error: {e}")
```

### 2. 速率限制

```python
run_input = {
    "startUrls": urls,
    "maxConcurrency": 5,  # 限制并发
    "maxRequestRetries": 3,  # 重试次数
    "requestHandlerTimeoutSecs": 60  # 超时时间
}
```

### 3. 数据清洗

```python
def clean_data(items):
    cleaned = []
    for item in items:
        # 去除空值
        item = {k: v for k, v in item.items() if v}
        # 去重
        if item not in cleaned:
            cleaned.append(item)
    return cleaned

data = client.dataset(run["defaultDatasetId"]).list_items().items
cleaned_data = clean_data(data)
```

## 常见问题

### Q: 如何处理需要登录的网站？

```python
run_input = {
    "startUrls": [{"url": "https://example.com"}],
    "preNavigationHooks": """
        async function preNavigationHook(context) {
            const { page } = context;
            await page.goto('https://example.com/login');
            await page.fill('#username', 'your_username');
            await page.fill('#password', 'your_password');
            await page.click('button[type="submit"]');
            await page.waitForNavigation();
        }
    """
}
```

### Q: 如何处理动态加载的内容？

```python
run_input = {
    "waitUntil": "networkidle",  # 等待网络空闲
    "pageFunction": """
        async function pageFunction(context) {
            const { page } = context;
            // 滚动到底部触发加载
            await page.evaluate(() => {
                window.scrollTo(0, document.body.scrollHeight);
            });
            await page.waitForTimeout(2000);
            // 提取数据
        }
    """
}
```

### Q: 如何避免被封禁？

1. 使用代理：`"useApifyProxy": True`
2. 降低并发：`"maxConcurrency": 1`
3. 添加延迟：`await page.waitForTimeout(1000)`
4. 模拟真实用户：设置 User-Agent

## 费用说明

- **免费套餐**：每月 $5 免费额度
- **按需付费**：超出部分按使用量计费
- **Actor 运行时间**：按秒计费
- **代理使用**：额外收费

## 参考资源

- 官方文档：https://docs.apify.com/
- Python SDK：https://docs.apify.com/sdk/python
- Actor Store：https://apify.com/store
- 社区论坛：https://community.apify.com/

## 注意事项

1. **遵守网站 robots.txt**
2. **尊重速率限制**
3. **不要抓取敏感数据**
4. **遵守当地法律法规**
5. **合理使用代理**

---

**最后更新**：2026-03-09  
**维护者**：主 agent
