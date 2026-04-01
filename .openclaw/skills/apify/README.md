# Apify Web Scraping Skill

强大的网页抓取和自动化工具，基于 Apify 平台。

## 快速开始

### 1. 安装依赖

```bash
pip install apify-client python-dotenv
```

### 2. 配置 API Token

在 `.env` 文件中添加：

```bash
APIFY_API_TOKEN=your_api_token_here
```

获取 Token：https://console.apify.com/account/integrations

### 3. 运行示例

```bash
python example.py
```

## 主要功能

- ✅ Google 搜索结果抓取
- ✅ 自定义网页抓取
- ✅ 批量 URL 处理
- ✅ 动态内容处理
- ✅ 代理支持
- ✅ 定时任务

## 文档

详细使用说明请查看 [SKILL.md](SKILL.md)

## 常用场景

1. **搜索引擎抓取**：Google、Bing、百度
2. **社交媒体**：Instagram、Twitter、LinkedIn
3. **电商平台**：Amazon、淘宝、京东
4. **新闻网站**：财经新闻、科技资讯
5. **数据监控**：价格监控、内容变化

## 注意事项

- 遵守网站 robots.txt
- 尊重速率限制
- 合理使用代理
- 遵守法律法规
