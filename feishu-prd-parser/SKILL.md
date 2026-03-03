# feishu-prd-parser

飞书 PRD 文档解析技能。将飞书文档转化为结构化 Markdown PRD，提取内嵌图片和流程图。

## 激活条件

当用户提到：
- 飞书文档解析
- PRD 文档读取
- 需求文档结构化
- 提供飞书 docx 链接

## 输入

- 飞书文档 URL（格式：`https://[domain].feishu.cn/docx/XXX`）

## 输出

- 结构化 Markdown PRD
- 图片/流程图 URL 列表
- 业务逻辑摘要

## 使用方式

```bash
# 通过脚本调用
./scripts/parse-prd.sh <docx_url>

# 或直接使用 feishu_doc 工具
```

## 处理流程

1. 解析 URL 获取 doc_token
2. **尝试**调用 `feishu_doc action=read` 读取文档
3. **如果失败**，尝试 `feishu_doc action=list_blocks` 获取块
4. **如果仍失败**（wiki 格式不支持），使用 `web_fetch` 抓取页面内容
5. 识别图片块（image 类型）并提取 URL
6. 识别流程图/原型图（通过 image 工具分析）
7. 输出结构化 Markdown

## 已知限制

- **wiki 格式文档**：`feishu_doc` 工具仅支持 docx 格式，wiki 格式返回 400 错误
- **解决方案**：wiki 链接使用 `web_fetch` 抓取，或转换为 docx 格式
- **权限问题**：需要飞书应用具有 `docs:document.content:read` 权限

## 环境变量

无

## 依赖工具

- `feishu_doc` — 读取飞书文档
- `image` — 分析流程图/原型图

## 示例输出

```markdown
# PRD: [文档标题]

## 1. 业务背景
...

## 2. 功能列表
- 功能 A
- 功能 B

## 3. 流程图
![流程图](image_url)

## 4. 原型图
![原型图](image_url)

## 5. 数据字段
...

## 6. 边界情况
...
```
