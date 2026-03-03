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

### 前置步骤：生成飞书应用身份 Token

**在调用任何飞书 API 之前，必须先生成应用身份 access token！**

```bash
curl -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "cli_xxx",
    "app_secret": "xxx"
  }'
```

**Token 管理：**
- 有效期：2 小时
- 有效期内复用，不重复生成
- 建议缓存到内存或临时文件

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

### 错误处理（重要！）

**如果任何步骤失败，立即中断流程并返回错误信息：**

```javascript
if (feishu_wiki.get 失败) {
  return {
    success: false,
    error: "Wiki 节点获取失败，请检查链接是否正确",
    stage: "wiki_get"
  };
}

if (feishu_doc.read 失败) {
  return {
    success: false,
    error: "文档内容读取失败，可能没有访问权限",
    stage: "doc_read"
  };
}

if (文档内容为空) {
  return {
    success: false,
    error: "文档内容为空，无法解析",
    stage: "content_empty"
  };
}
```

**失败不继续：** PRD 解析失败时，不继续后续流程，直接告知用户。

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
