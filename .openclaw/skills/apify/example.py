"""
Apify 使用示例
演示如何使用 Apify 进行网页抓取
"""
from apify_client import ApifyClient
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def example_google_search():
    """示例1：Google 搜索"""
    client = ApifyClient(os.getenv('APIFY_API_TOKEN'))
    
    run_input = {
        "queries": "量化交易 Python",
        "maxPagesPerQuery": 1,
        "resultsPerPage": 10
    }
    
    print("正在运行 Google Search Scraper...")
    run = client.actor("apify/google-search-scraper").call(run_input=run_input)
    
    print(f"运行状态: {run['status']}")
    
    if run["status"] == "SUCCEEDED":
        items = client.dataset(run["defaultDatasetId"]).list_items().items
        print(f"\n找到 {len(items)} 条结果：\n")
        
        for i, item in enumerate(items[:5], 1):
            print(f"{i}. {item.get('title')}")
            print(f"   URL: {item.get('url')}")
            print()

def example_web_scraper():
    """示例2：自定义网页抓取"""
    client = ApifyClient(os.getenv('APIFY_API_TOKEN'))
    
    run_input = {
        "startUrls": [{"url": "https://news.ycombinator.com/"}],
        "pageFunction": """
            async function pageFunction(context) {
                const { page } = context;
                const stories = await page.$$eval('.athing', items => {
                    return items.slice(0, 10).map(item => ({
                        title: item.querySelector('.titleline a')?.textContent,
                        url: item.querySelector('.titleline a')?.href
                    }));
                });
                return stories;
            }
        """
    }
    
    print("正在抓取 Hacker News...")
    run = client.actor("apify/web-scraper").call(run_input=run_input)
    
    if run["status"] == "SUCCEEDED":
        items = client.dataset(run["defaultDatasetId"]).list_items().items
        print(f"\n抓取到 {len(items)} 条新闻：\n")
        
        for i, item in enumerate(items, 1):
            print(f"{i}. {item.get('title')}")
            print(f"   {item.get('url')}")
            print()

def example_batch_scraping():
    """示例3：批量抓取"""
    client = ApifyClient(os.getenv('APIFY_API_TOKEN'))
    
    urls = [
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/page3"
    ]
    
    run_input = {
        "startUrls": [{"url": url} for url in urls],
        "maxConcurrency": 3
    }
    
    print("正在批量抓取...")
    run = client.actor("apify/web-scraper").call(run_input=run_input)
    
    print(f"运行状态: {run['status']}")

if __name__ == "__main__":
    # 检查 API Token
    if not os.getenv('APIFY_API_TOKEN'):
        print("错误：请设置 APIFY_API_TOKEN 环境变量")
        print("1. 注册 Apify 账号：https://apify.com/")
        print("2. 获取 API Token：https://console.apify.com/account/integrations")
        print("3. 在 .env 文件中添加：APIFY_API_TOKEN=your_token")
        exit(1)
    
    print("=== Apify 使用示例 ===\n")
    
    # 运行示例
    try:
        example_google_search()
        # example_web_scraper()
        # example_batch_scraping()
    except Exception as e:
        print(f"错误：{e}")
