# frontend-tech-solution

前端技术方案生成技能。基于 PRD 和 Figma 设计稿 schema，生成完整的前端实现技术方案。

## 激活条件

当用户提到：
- 生成前端技术方案
- 前端实现方案
- 技术方案设计
- 提供 PRD + 设计稿 schema

## 输入

- 结构化 PRD（Markdown 格式）
- Figma 设计稿 schema（JSON 格式）
- 可选：原型图/流程图分析结果

## 输出

### 成功场景

**技术方案文档：**
- **飞书文档链接**（优先，调用飞书 API 创建）
- **或本地 Markdown 文件**（备选，当飞书 API 不可用时）
- 路径：`/workspace/output/<项目名>-<日期>.md`

**返回信息：**
```json
{
  "status": "success",
  "document": {
    "type": "feishu|local",
    "url": "https://...",
    "path": "/workspace/output/..."
  },
  "figmaUsed": true,
  "prdSource": "wiki|docx"
}
```

### 失败场景

**PRD 解析失败：**
```json
{
  "status": "error",
  "stage": "prd_parsing",
  "message": "PRD 文档解析失败，无法继续生成技术方案。请检查：...",
  "recoverable": false
}
```

**Figma 解析失败：**
```json
{
  "status": "error",
  "stage": "figma_parsing",
  "message": "Figma 设计稿解析异常，无法继续生成技术方案。请检查：...",
  "recoverable": false
}
```

**技术方案生成失败：**
```json
{
  "status": "error",
  "stage": "solution_generation",
  "message": "技术方案生成失败",
  "recoverable": true
}
```

## 飞书文档创建流程

### 1. 获取应用身份 Access Token

使用飞书应用的 `app_id` 和 `app_secret` 调用飞书开放平台 API：

```bash
curl -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "cli_xxx",
    "app_secret": "xxx"
  }'
```

返回：
```json
{
  "code": 0,
  "tenant_access_token": "t-at-xxx",
  "expire": 7200
}
```

### 2. 创建飞书文档

使用 access token 创建文档：

```bash
curl -X POST "https://open.feishu.cn/open-apis/docx/v1/documents" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer t-at-xxx" \
  -d '{
    "title": "前端技术方案 - 项目名称"
  }'
```

返回文档 `document_id`。

### 3. 写入文档内容

```bash
curl -X PUT "https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{block_id}/children" \
  -H "Authorization: Bearer t-at-xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "parent_block_id": "{block_id}",
    "elements": [...]
  }'
```

### 4. 转移文档权限给用户（可选）

将应用编辑权限转移给当前用户：

```bash
curl -X POST "https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/collaborators" \
  -H "Authorization: Bearer t-at-xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "member_id": "ou_xxx",
    "member_type": "user",
    "permission": "edit"
  }'
```

### 配置信息

飞书应用配置存储在 OpenClaw 配置文件中：

**配置路径：** `/home/admin/.openclaw/openclaw.json`

**配置结构：**
```json
{
  "channels": {
    "feishu": {
      "accounts": {
        "feishubot": {
          "appId": "cli_xxx",
          "appSecret": "xxx",
          "domain": "feishu"
        }
      }
    }
  }
}
```

**注意：** 不要将 `app_id` 和 `app_secret` 明文写入技能文档或提交到 Git。

## 技术栈默认配置

- **框架:** React 18+
- **语言:** TypeScript
- **样式:** TailwindCSS
- **组件库:** shadcn/ui
- **状态管理:** Zustand / React Context
- **路由:** React Router v6
- **HTTP 客户端:** Axios / TanStack Query
- **表单:** React Hook Form + Zod
- **测试:** Vitest + React Testing Library

## 使用方式

```bash
# 通过脚本调用
./scripts/generate-solution.sh <prd_path> <figma_schema_path>

# 或直接由 AI 生成
```

## 处理流程

### 前置步骤：生成飞书应用身份 Token

**在调用任何飞书 API 之前，必须先生成应用身份 access token！**

```bash
# 1. 从配置读取 app_id 和 app_secret
# 配置路径：/home/admin/.openclaw/openclaw.json

# 2. 调用飞书 API 获取 tenant_access_token
curl -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "cli_xxx",
    "app_secret": "xxx"
  }'

# 3. 返回结果
{
  "code": 0,
  "tenant_access_token": "t-at-xxx",
  "expire": 7200
}
```

**Token 管理规则：**
- ✅ Token 有效期：**2 小时**（7200 秒）
- ✅ 有效期内复用，不重复生成
- ✅ 建议缓存到内存或临时文件
- ❌ 每次调用都生成新 token（浪费且可能被限流）

---

### 步骤 1：解析 PRD 文档（必需）

**这是必需步骤，失败则中断整个流程！**

#### 1.1 识别文档格式

| 格式 | URL 示例 | Token 提取 |
|------|----------|------------|
| docx | `https://xxx.feishu.cn/docx/ABC123` | `ABC123` |
| wiki | `https://xxx.feishu.cn/wiki/XYZ789` | `XYZ789` |

#### 1.2 获取文档内容

**wiki 格式：**
```javascript
// 第一步：获取 obj_token
feishu_wiki {
  "action": "get",
  "token": "wiki_token_from_url"
}
// 返回：{ "obj_token": "xxx", "obj_type": "docx" }

// 第二步：使用 obj_token 读取文档
feishu_doc {
  "action": "read",
  "doc_token": "obj_token_from_above"
}
```

**docx 格式：**
```javascript
// 直接读取文档
feishu_doc {
  "action": "read",
  "doc_token": "doc_token_from_url"
}
```

#### 1.3 错误处理（重要！）

```javascript
if (feishu_doc.read 失败 || feishu_wiki.get 失败) {
  // ❌ 中断流程，不再继续
  return "PRD 文档解析失败，无法继续生成技术方案。请检查：
    1. 文档链接是否正确
    2. 是否有文档访问权限
    3. 飞书应用 token 是否有效";
}
```

**失败场景：**
- ❌ 文档链接无效
- ❌ 没有访问权限
- ❌ 飞书 API 故障
- ❌ Token 过期或无效

**成功场景：**
- ✅ 获取到文档标题、内容、结构
- ✅ 继续下一步

---

### 步骤 2：解析 Figma 设计稿（可选）

**这是可选步骤，根据用户是否提供 Figma URL 决定！**

#### 2.1 判断是否需要解析

```javascript
if (!用户提供了 Figma URL) {
  // 跳过 Figma 解析，直接进入步骤 3
  console.log("未提供设计稿，跳过 Figma 解析");
  figmaSchema = null;
} else {
  // 开始解析 Figma
  proceed_to_2_2();
}
```

#### 2.2 解析 Figma 节点

```bash
# 解析 URL 获取 file_key 和 node_id
# URL 格式：https://www.figma.com/file/:key/:name?node-id=:id

curl -X GET "https://api.figma.com/v1/files/{file_key}/nodes?ids={node_id}" \
  -H "X-Figma-Token: $FIGMA_TOKEN"
```

#### 2.3 验证解析结果（重要！）

```javascript
const figmaResponse = await callFigmaAPI();

// 验证是否包含有效节点信息
if (!figmaResponse.nodes || 
    !figmaResponse.nodes[node_id] ||
    !figmaResponse.nodes[node_id].name ||
    !figmaResponse.nodes[node_id].type) {
  
  // ❌ 中断流程，告知用户
  return "Figma 设计稿解析异常，无法继续生成技术方案。请检查：
    1. Figma URL 是否正确（包含 node-id 参数）
    2. FIGMA_TOKEN 是否有效
    3. 设计稿是否有访问权限
    4. 节点是否存在";
}

// ✅ 解析成功，提取关键信息
figmaSchema = {
  name: figmaResponse.nodes[node_id].name,
  type: figmaResponse.nodes[node_id].type,
  children: figmaResponse.nodes[node_id].children,
  // ...
};
```

**失败场景：**
- ❌ Token 无效（403 Invalid token）
- ❌ 文件/节点不存在（404）
- ❌ 没有访问权限
- ❌ URL 格式错误（缺少 node-id）
- ❌ 返回数据不包含有效节点信息

**成功场景：**
- ✅ 获取到设计稿名称、类型、组件结构
- ✅ 继续步骤 3

---

### 步骤 3：生成技术方案

**基于 PRD（必需）+ Figma（可选）生成技术方案**

```javascript
// 输入
const prdContent = step1_result; // 必需
const figmaSchema = step2_result; // 可选，可能为 null

// 生成技术方案文档
const solution = generateSolution({
  prd: prdContent,
  figma: figmaSchema, // 如果有
});

// 输出
if (solution.success) {
  return {
    status: "success",
    document: solution.content,
    figmaUsed: figmaSchema !== null,
  };
} else {
  return {
    status: "error",
    message: "技术方案生成失败",
  };
}
```

---

### 完整流程图

```
开始
  ↓
[前置] 生成飞书应用身份 token（2 小时有效期）
  ↓
[步骤 1] 解析 PRD 文档（必需）
  ↓
  成功？───否───→ ❌ 中断流程，告知用户
  ↓是
[步骤 2] 用户提供了 Figma URL？
  ↓
  是 ──→ 解析 Figma 设计稿
          ↓
          包含有效节点信息？───否───→ ❌ 中断流程，告知用户
          ↓是
          提取设计稿 schema
  ↓
  否（跳过 Figma）
  ↓
[步骤 3] 生成技术方案（PRD + 可选 Figma）
  ↓
完成 → 返回技术方案文档
```

## 环境变量

无

## 依赖工具

- `feishu_doc` — 创建飞书文档
- `write` — 生成临时文件

## 输出文档结构

```markdown
# 前端技术方案：[项目名称]

## 1. 项目概述
- 业务背景
- 目标用户
- 核心功能

## 2. 技术栈
- React + TypeScript + TailwindCSS
- shadcn/ui 组件库
- ...

## 3. 组件设计
### 3.1 原子组件
- Button (shadcn)
- Input (shadcn)
- ...

### 3.2 业务组件
- UserForm
- ProductList
- ...

## 4. 页面结构
- /home — 首页
- /products — 产品列表
- ...

## 5. API 接口
| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 获取产品 | GET | /api/products | ... |

## 6. 状态管理
- 全局状态：Zustand
- 本地状态：useState/useReducer

## 7. 路由设计
```tsx
// react-router 配置
```

## 8. 测试计划
- 单元测试
- 组件测试
- E2E 测试

## 9. 开发计划
| 阶段 | 任务 | 预计工时 |
|------|------|----------|
| 1 | 环境搭建 | 2h |
| ... | ... | ... |
```

## 注意事项

- 组件优先使用 shadcn 开源方案
- 技术方案需要可执行、可落地
- 测试计划需要覆盖核心功能
- **飞书 API 可能失败**（权限/格式问题），需 fallback 到本地文件
- 本地文件保存路径：`/workspace/output/<项目名>-<日期>.md`
- 创建成功后优先返回飞书链接，其次返回本地路径
- **权限转移**：文档创建后建议调用权限转移接口，将编辑权限转给当前用户
- **Token 缓存**：`tenant_access_token` 有效期 2 小时，可缓存复用
- **安全配置**：`app_id` 和 `app_secret` 存储在 OpenClaw 配置中，不要明文写入技能文档或提交到 Git

## 依赖的飞书 API 权限

- `docs:document:write` — 创建和编辑文档
- `docs:document.content:write` — 写入文档内容
- `wiki:wiki` — 访问知识库（wiki 格式文档）

## 安全实践

- ✅ 飞书应用配置存储在 `/home/admin/.openclaw/openclaw.json`（本地文件）
- ✅ 技能文档中只记录配置路径，不写入实际值
- ✅ `.gitignore` 已配置，排除敏感配置文件
- ❌ 不要在技能文档、示例代码或注释中写入真实的 `app_id` 和 `app_secret`
- ❌ 不要将包含敏感信息的文件提交到 Git 仓库
