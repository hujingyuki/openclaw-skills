# figma-node-parser

Figma 设计稿节点解析技能。通过 Figma API 获取设计稿节点树，输出 JSON schema。

## 激活条件

当用户提到：
- Figma 设计稿解析
- Figma URL 转 schema
- 设计稿节点分析
- 提供 Figma URL（格式：`https://figma.com/file/:key/:name?node-id=:id`）

## 输入

- Figma URL（包含 file key 和 node-id）

## 输出

- JSON schema（组件层级、样式、约束、自动布局、交互信息）

## 使用方式

```bash
# 通过脚本调用
./scripts/parse-figma.sh <figma_url>

# 或直接调用 Figma API
```

## 处理流程

### 1. 解析 URL

从 Figma URL 提取 file_key 和 node_id：

```
URL: https://www.figma.com/file/:key/:name?node-id=:id
示例：https://www.figma.com/file/UlhwonfWpF1Az9huFEZ9ib/IPD-R?node-id=23615-579

提取：
- file_key: UlhwonfWpF1Az9huFEZ9ib
- node_id: 23615-579
```

**验证：** 如果 URL 不包含 `node-id` 参数，返回错误。

### 2. 调用 Figma API

```bash
curl -X GET "https://api.figma.com/v1/files/{file_key}/nodes?ids={node_id}" \
  -H "X-Figma-Token: $FIGMA_TOKEN"
```

### 3. 验证解析结果（重要！）

**必须验证返回数据包含有效节点信息：**

```javascript
const response = await callFigmaAPI();

// 验证 nodes 对象存在
if (!response.nodes) {
  return {
    success: false,
    error: "Figma API 返回数据不包含 nodes 字段",
    stage: "api_response_invalid"
  };
}

// 验证请求的节点存在
if (!response.nodes[node_id]) {
  return {
    success: false,
    error: `节点 ${node_id} 不存在，请检查 URL 是否正确`,
    stage: "node_not_found"
  };
}

const node = response.nodes[node_id];

// 验证节点包含必要信息
if (!node.name || !node.type) {
  return {
    success: false,
    error: "节点数据不完整，缺少 name 或 type 字段",
    stage: "node_data_invalid"
  };
}

// ✅ 验证通过
return {
  success: true,
  schema: {
    id: node.id,
    name: node.name,
    type: node.type,
    children: node.children,
    // ...
  }
};
```

### 4. 提取组件信息

- 名称、类型、样式、约束、自动布局
- 子节点层级结构
- 交互信息（如果有）

### 5. 输出 JSON schema

```json
{
  "success": true,
  "schema": {
    "name": "Frame 1",
    "type": "FRAME",
    "children": [...],
    "styles": {...}
  }
}
```

### 错误处理（重要！）

**如果解析失败，立即中断并返回错误：**

| 错误 | 返回信息 |
|------|----------|
| Token 无效 | `403 Invalid token` - FIGMA_TOKEN 配置错误 |
| 文件不存在 | `404 Not found` - file_key 错误 |
| 节点不存在 | 节点 ID 错误或设计稿已删除 |
| 无访问权限 | 设计稿为私有，需要申请权限 |
| URL 格式错误 | URL 不包含 node-id 参数 |

**失败不继续：** Figma 解析失败时，不继续后续流程，直接告知用户。

## 环境变量

- `FIGMA_TOKEN` — Figma Personal Access Token
- **配置位置**：`~/.bashrc` 或 `~/.zshrc` 或系统环境变量
- **获取方式**：https://www.figma.com/developers/api#access-tokens

## 配置方式

```bash
# 临时配置（当前会话）
export FIGMA_TOKEN="figd_your_token_here"

# 永久配置（添加到 ~/.bashrc 或 ~/.zshrc）
echo 'export FIGMA_TOKEN="figd_your_token_here"' >> ~/.bashrc
source ~/.bashrc
```

## 故障排查

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `403 Invalid token` | Token 不正确或已过期 | 重新生成 Token 并更新配置 |
| `404 Not found` | 文件 ID 错误或无权限 | 确认文件 URL 和访问权限 |
| 环境变量未生效 | 未在当前 shell 中设置 | 执行 `export FIGMA_TOKEN=xxx` |
| `401 Unauthorized` | Token 格式错误 | 确认以 `figd_` 开头 |

## 测试命令

```bash
# 测试 API 连接
curl -s -X GET "https://api.figma.com/v1/files/{file_key}/nodes?ids={node_id}" \
  -H "X-Figma-Token: $FIGMA_TOKEN" | jq '.nodes'
```

## 依赖工具

- `exec` — 调用 Figma API（curl）
- `write` — 输出 JSON schema 文件

## Figma API 端点

```
GET https://api.figma.com/v1/files/{file_key}/nodes?ids={node_id}
Header: X-Figma-Token: {token}
```

## 示例输出

```json
{
  "name": "Frame 1",
  "type": "FRAME",
  "children": [
    {
      "name": "Button",
      "type": "RECTANGLE",
      "fills": [{"type": "SOLID", "color": {"r": 0, "g": 0, "b": 1}}],
      "constraints": {"horizontal": "LEFT_RIGHT", "vertical": "TOP"},
      "autoLayout": null
    }
  ],
  "styles": {...}
}
```

## 注意事项

- Figma Token 需要妥善保管，不要提交到 Git
- 节点 ID 格式：`-1:0` 或 `123:456`
- 支持解析 Frame、Component、Instance、Text、Rectangle 等节点类型
