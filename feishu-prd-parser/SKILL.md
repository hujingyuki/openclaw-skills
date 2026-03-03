# feishu-prd-parser

飞书 PRD 文档解析技能。将飞书文档转化为结构化 Markdown PRD，提取内嵌图片和流程图。

## 激活条件

当用户提到：
- 飞书文档解析
- PRD 文档读取
- 需求文档结构化
- 提供飞书 docx 链接

## 说明

下载**飞书文档**内容，产出：
- **文档内容（documentContent）**：Markdown 格式的文档正文
- **文档元数据（summary）**：块数、图片数、画板数等
- **本地文件**：文档保存到 `save_path`，图片和画板均保存到同目录下 `images/`

支持输入：
- **Wiki 文档**：`https://xxx.feishu.cn/wiki/xxx`
- **Docx 文档**：`https://xxx.feishu.cn/docx/xxx`
- **Docs 文档**：`https://xxx.feishu.cn/docs/xxx`

---

## 1. 输入参数

### 必传参数

- `feishu_url` (string): 飞书文档链接
  - 支持：Wiki / Docx / Docs 三种类型

### 可选参数（由 AI 自动决定）

- `save_path` (string): 文档保存位置
  - **用户未指定时**：AI 根据当前工作目录和上下文自动选择
  - **建议格式**：`/当前工作区/output/feishu_docs/<文档名>.md`
  - 图片和画板会自动保存到 `save_path` 所在目录下的 `images/`

### 约束与建议

- 链接必须来自 `*.feishu.cn` 域名
- AI 应根据项目结构选择合适的保存目录

---

## 2. 输出格式

`fetch_document` 成功后会保存文件并输出信息：

```json
{
  "documentId": "xxx",
  "documentContent": "# 文档标题\n\n文档内容...",
  "summary": {
    "totalBlocks": 10,
    "imageCount": 2,
    "attachmentCount": 0,
    "whiteboardCount": 1
  },
  "images": [{ "blockId": "xxx", "filePath": "/abs/path/images/image-xxx.png", "token": "xxx" }],
  "whiteboards": [{ "blockId": "xxx", "filePath": "/abs/path/images/xxx_whiteboard_1.png", "whiteboardId": "xxx" }],
  "attachments": []
}
```

字段含义：
- `documentId`：文档唯一标识
- `documentContent`：Markdown 格式的文档内容
- `summary`：文档统计信息
- `images`：图片列表，`filePath` 为本地保存路径
- `whiteboards`：画板/流程图列表，`filePath` 为本地保存路径
- `attachments`：附件列表

---

## 3. 退出码说明

| 退出码 | 含义       | 后续操作     |
|--------|------------|--------------|
| 0      | 成功       | 继续执行     |
| 1      | 失败       | 停止执行，报告错误 |

---

## 4. 执行步骤

### Step 0: validate_url

校验 `feishu_url` 是否为有效的飞书文档链接。AI 按以下规则执行（无需调用脚本）：

1. **非空**：链接不能为空，否则提示「飞书链接不能为空」
2. **域名**：必须是 `*.feishu.cn`，否则提示「无效的飞书链接，请确保链接来自 feishu.cn 域名」
3. **格式**：必须为 Wiki / Docx / Docs 之一
4. **不通过**：任一条件不满足则停止并提示；通过则继续 Step 1

---

### Step 1: fetch_document

获取飞书文档内容并保存到本地。

**重要**：`save_path` 根据以下规则决定：
1. 优先使用 `当前工作区/output/feishu_docs/` 目录
2. 文件名使用 `feishu_<timestamp>.md` 或根据上下文命名
3. 脚本会自动创建目录

**能力调用**：

```bash
python scripts/fetchFeishuDocHandler.py fetch "$feishu_url" "$save_path"
```

**退出码处理**：
- 0：成功，文档已保存，图片和画板在 `save_path` 同目录的 `images/`
- 1：失败，停止执行，报告错误信息

---

## 5. 环境变量

| 变量               | 必填 | 说明                     |
|--------------------|------|--------------------------|
| `FEISHU_APP_ID`    | 是   | 飞书应用 ID             |
| `FEISHU_APP_SECRET`| 是   | 飞书应用密钥            |
| `DEBUG`            | 否   | 非空时输出详细错误堆栈  |

**获取方式**：查找环境变量，获取 App ID 和 App Secret。

---

## 6. 常见问题

- **请配置 FEISHU_APP_ID 和 FEISHU_APP_SECRET**
  - 脚本直接调用飞书 Open API，无需 MCP 服务
  - 需在飞书开放平台创建应用并配置权限（文档读写等）

- **获取租户访问令牌失败**
  - 检查 App ID 和 App Secret 是否正确
  - 确认应用已发布或已添加为自建应用

- **链接可打开但获取失败**
  - 检查链接是否为 wiki/docx/docs 的真实地址
  - 确认应用是否有访问该文档的权限

- **文档内容不完整**
  - 部分复杂格式（表格、公式等）可能转换不完美
  - 图片和流程图会保存到本地，路径在输出中列出

---

## 7. 安全与合规

- 飞书文档可能包含敏感信息，注意保存位置的权限控制
- App Secret 不要提交到 Git，建议通过环境变量配置
- **Python 中间产物**：脚本运行后产生的 `scripts/__pycache__/` 及 `.pyc` 文件为中间产物，执行完成后应删除或加入 `.gitignore`，不纳入版本管理
