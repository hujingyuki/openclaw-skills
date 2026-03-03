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

1. 解析 URL 获取 file_key 和 node_id
2. 调用 Figma API `GET /v1/files/:key/nodes?ids=:node_id`
3. 解析节点树结构
4. 提取组件信息（名称、类型、样式、约束、自动布局）
5. 输出 JSON schema

## 环境变量

- `FIGMA_TOKEN` — Figma Personal Access Token
- **配置位置**：`~/.bashrc` 或 `~/.zshrc` 或系统环境变量
- **获取方式**：https://www.figma.com/developers/api#access-tokens

## 故障排查

- **403 Invalid token**：检查 `FIGMA_TOKEN` 是否正确配置
- **环境变量未生效**：在当前 shell 执行 `export FIGMA_TOKEN=xxx` 或重启终端
- **权限不足**：确认 Token 具有文件读取权限（file_read scope）

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
