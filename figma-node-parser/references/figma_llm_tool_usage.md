# Figma Python LLM 调用文档

本文面向大模型/Agent，配合 `../scripts/figma_llm_tool.py` 使用。

## 1. 目标

让模型在不同任务场景下，稳定选择正确能力并得到可解析结果。

调用入口：

- `python3 ../scripts/figma_llm_tool.py --tool <tool_name> --args-json '<json>'`

统一返回：

- 成功：`{"success": true, "tool": "...", "data": ..., "message": "..." }`
- 失败：`{"success": false, "tool": "...", "message": "...", "error": {"type": "...", "message": "..."}}`

## 2. 工具清单（能力卡片）

### 2.1 `get_file`

用途：拉取整个 Figma 文件 JSON。  
适用：做结构分析、离线缓存、后续筛选。  
不适用：仅想拉某几个节点时。

必填参数：

- `figmaUrl: string`

可选参数：

- `accessToken: string`
- `timeoutSeconds: number`（默认 60）

### 2.2 `get_nodes`

用途：按节点 ID 拉取 JSON（nodes API）。  
适用：只关注局部节点或子树。  
不适用：需要全量文件结构时。

入参优先级：

- 优先 `figmaUrl`
- 若无 `figmaUrl`，则 `fileKey` 与 `nodeIds` 必填

可选参数：

- `accessToken: string`
- `timeoutSeconds: number`

### 2.3 `get_nodeids_images`

用途：按 `nodeId/nodeIds` 直传下载，不做过滤。  
适用：明确要导出指定节点。  
不适用：需要按子树筛选时。

必填参数：

- `fileKey: string`
- `nodeId: string` 或 `nodeIds: string[]`
- `outputDir: string`（可选，默认 `./.temp`，最终会转为绝对路径）

可选参数：

- `format: "png" | "jpg" | "svg"`（默认 png）
- `scale: number`（默认 1）
- `nodeIds: string[]`（可选，批量下载）
- `nodesJson: object`（可选，外部传入 nodes API 返回）
- `rootDocument: object`（可选，外部传入 nodes.<nodeId>.document）
- `batchSize: number`（默认 50）
- `intervalMs: number`（默认 5000）
- `force: boolean`（默认 false）
- `useManifest: boolean`（默认 true）
- `accessToken: string`
- `timeoutSeconds: number`

返回值：

- `object`，以 `nodeId:format:scale` 为 key 的映射（`nodeId` 中的 `:` 会替换为 `-`），value 至少包含 `filePath` 与 `fileName`。

门禁校验（模型侧语义规则）：

- `get_file` 必须返回 `document` 对象；否则视为结构异常，直接报错。
- `get_nodes` 必须返回 `nodes` 对象；否则视为结构异常，直接报错。
- `get_nodeids_images/get_images_tree` 必须返回映射对象，且每项包含 `filePath` 与 `fileName`；否则视为结构异常，直接报错。

### 2.4 `get_images_tree`

用途：递归下载子树图片集合，支持过滤。  
适用：需要按子树/规则批量导出。  
不适用：只导出少量已知节点。

必填参数：

- `fileKey: string`
- `nodeId: string` 或 `nodeIds: string[]`
- `outputDir: string`（可选，默认 `./.temp`，最终会转为绝对路径）

可选参数：

- `format: "png" | "jpg" | "svg"`（可选）
- `scale: number`（默认 1）
- `filters: object`（支持 `id/name/type/characters/hasField`）
- `nodesJson: object`（可选，外部传入 nodes API 返回）
- `rootDocument: object`（可选，外部传入 nodes.<nodeId>.document）
- `batchSize: number`（默认 50）
- `intervalMs: number`（默认 5000）
- `force: boolean`（默认 false）
- `useManifest: boolean`（默认 true）
- `accessToken: string`
- `timeoutSeconds: number`

默认过滤规则：

- 未显式传 `filters` 时，仅下载满足 `exportSettings` 或 `IMAGE` fill 的节点。

空结果说明：

- `get_images_tree` 若未命中可下载节点，将返回空对象并附带 `message`，不视为错误。

## 3. 场景路由（决策表）

- 任务是“先拿完整文件结构”：用 `get_file`
- 任务是“只拿某几个节点”：用 `get_nodes`
- 任务是“导出图片（直传节点）”：用 `get_nodeids_images`
- 任务是“导出图片（递归子树）”：用 `get_images_tree`

## 3.1 场景说明（给模型）

- `get_file`
  - 适用：需要全量结构分析、缓存、后续批处理。
  - 不适用：只关心某几个节点，或只想导图。
- `get_nodes`
  - 适用：已知节点 ID，只需要局部子树。
  - 不适用：需要全量结构，或没有 node-id 的 URL。
- `get_nodeids_images`
  - 适用：明确要产出图片文件（单点或子树）。
  - 不适用：仅做结构分析或筛选。

## 4. 标准调用模板

### 4.1 拉整文件

```bash
python3 ../scripts/figma_llm_tool.py \
  --tool get_file \
  --args-json '{"figmaUrl":"https://www.figma.com/design/<fileKey>/xxx"}'
```

### 4.2 拉节点子树

```bash
python3 ../scripts/figma_llm_tool.py \
  --tool get_nodes \
  --args-json '{"fileKey":"<fileKey>","nodeIds":["7:2589","7:2590"]}'
```

### 4.3 下载图片（单节点）

```bash
python3 ../scripts/figma_llm_tool.py \
  --tool get_nodeids_images \
  --args-json '{
    "fileKey":"<fileKey>",
    "nodeId":"7:2589",
    "outputDir":"/abs/path/images",
    "format":"png",
    "scale":2
  }'
```

### 4.4 递归下载子树图片

```bash
python3 ../scripts/figma_llm_tool.py \
  --tool get_images_tree \
  --args-json '{
    "fileKey":"<fileKey>",
    "nodeId":"1:2",
    "outputDir":"/abs/path/tree-images",
    "filters":{"hasField":"exportSettings"}
  }'
```

### 4.5 多 Figma 链接索引化输出

当用户输入多个 Figma 地址时，不要将多个 node-id 合并到一次 `get_nodes` 调用中。应按链接逐次调用 `get_nodes` 并分别保存结果，最终将索引写入 `figma-raw.json.nodes`（不强制合并为单一节点树）：

```bash
# 逐链接获取并落盘
python3 ../scripts/figma_llm_tool.py --tool get_nodes --args-json '{"figmaUrl":"<url_a>"}' > /abs/path/figma/raw_parts/raw_<fileKeyA>_<nodeidA>.json
python3 ../scripts/figma_llm_tool.py --tool get_nodes --args-json '{"figmaUrl":"<url_b>"}' > /abs/path/figma/raw_parts/raw_<fileKeyB>_<nodeidB>.json

# 生成 figma-raw.json（索引口径）示意：
# {
#   "mode": "url_index",
#   "nodes": {
#     "<figma_url_or_hash>": {
#       "fileKey": "<file_key>",
#       "nodeIds": ["<nodeid>"],
#       "rawFilePath": "/abs/path/figma/raw_parts/raw_<fileKey>_<nodeid_safe>.json"
#     }
#   }
# }
```

## 5. 错误处理规范（模型策略）

第一步：始终先判断 `success`。  
第二步：若失败，仅修正最相关参数后重试一次。  
第三步：仍失败时输出 `error.type` 和 `error.message`，停止盲重试。

常见错误与处理：

- `accessToken is required`
  - 设置 `FIGMA_ACCESS_TOKEN` 或传 `accessToken`
- `outputDir 必须是绝对路径`
  - 改为绝对路径
- `nodeIds 不能为空`
  - 提供非空节点列表
- `Figma API 限流 (429)`
  - 增大 `intervalMs`，减小 `batchSize`

## 6. 推荐默认参数（大模型）

- 下载任务默认：`batchSize=50`, `intervalMs=5000`
- 大文件/高并发环境：`batchSize=20`, `intervalMs=8000`
- 首次调试：开启 `--pretty`，必要时加 `--verbose`

## 7. 超时说明

- 脚本内 HTTP 请求默认 `timeoutSeconds=60`。若在 **命令执行环境有 30 秒总超时**（如部分 CI/IDE）下运行，可能未等 Figma 返回就被终止。
- **建议**：在此类环境下传 `timeoutSeconds: 25`，让请求在总超时前结束，便于拿到明确成功/失败结果；或延长命令执行器的超时时间（如 90–120 秒）再跑完整 60 秒请求。
