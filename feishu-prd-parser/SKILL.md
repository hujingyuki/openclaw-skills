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

### docx 格式文档

1. 解析 URL 获取 doc_token（格式：`https://[domain].feishu.cn/docx/XXX` → `XXX`）
2. 调用 `feishu_doc action=read` 读取文档
3. 调用 `feishu_doc action=list_blocks` 获取所有块
4. 识别图片块（image 类型）并提取 URL
5. 识别流程图/原型图（通过 image 工具分析）
6. 输出结构化 Markdown

### wiki 格式文档

1. 解析 URL 获取 wiki_token（格式：`https://[domain].feishu.cn/wiki/XXX` → `XXX`）
2. 调用 `feishu_wiki action=get` 获取节点信息，返回 `obj_token` 和 `obj_type`
3. 使用 `obj_token` 调用 `feishu_doc action=read` 读取文档内容
4. 调用 `feishu_doc action=list_blocks` 获取所有块
5. 识别图片块并提取 URL
6. 输出结构化 Markdown

## URL 格式识别

| 格式 | URL 示例 | Token 提取 | 处理方式 |
|------|----------|------------|----------|
| docx | `https://xxx.feishu.cn/docx/ABC123` | `ABC123` | 直接用 `feishu_doc` |
| wiki | `https://xxx.feishu.cn/wiki/XYZ789` | `XYZ789` | 先用 `feishu_wiki` 获取 `obj_token` |

## 依赖工具

- `feishu_doc` — 读取飞书文档内容
- `feishu_wiki` — 获取 wiki 节点信息（wiki 格式需要）
- `image` — 分析流程图/原型图

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
