# Figma Scripts Reference

本文档汇总 `scripts/` 目录下的 Python Figma 工具能力，面向 LLM/Agent 与脚本调用。

## 文件列表

- `../scripts/figma_core.py`: Figma 基础能力（URL 解析、files/nodes/images 请求、筛选、下载）
- `../scripts/figma_fetch.py`: 对外封装能力（`get_file`、`get_nodes`、`get_nodeids_images`、`get_images_tree`）
- `../scripts/figma_llm_tool.py`: 面向大模型的统一调用入口（JSON 入参/出参，三类能力）
- `../scripts/figma_transform.py`: 预处理：过滤不可见节点，产出 transform_parts
- `../scripts/generate_assets.py`: 生成 assets_Figma.json（汇总 nodes、pages、nodeIndex、imageDownloads 索引）
- `./figma_llm_tool_usage.md`: 面向大模型的调用规范与场景路由文档

## 核心能力口径

- URL 解析：`parse_figma_url`
- 拉取整文件 JSON：`get_file`
- 拉取节点 JSON（URL 优先）：`get_nodes`
- 图片下载（直传节点，无条件）：`get_nodeids_images`
- 图片下载（递归子树，带过滤）：`get_images_tree`

## 场景说明（给模型）

- `get_file`：用于全量结构分析、缓存、后续批处理。
- `get_nodes`：用于已知节点 ID 的局部子树获取。
- `get_nodeids_images`：用于产出图片文件，不适合仅做结构分析。

## 返回结构与自定义 Key

### Python API（figma_fetch / figma_core）

- `get_file(figmaUrl, ...) -> dict`
  - 返回：Figma `files` 接口原始 JSON（字典）。
  - 顶层字段（常见）：`document`、`components`、`componentSets`、`styles`、`name`、`lastModified`、`thumbnailUrl`、`version`、`role`、`editorType`、`linkAccess`。
  - 关键字段类型（常见）：`document: object`，`components: object`，`componentSets: object`，`styles: object`，`name: string`，`lastModified: string`。

- `get_nodes(figmaUrl | fileKey+nodeIds, ...) -> dict`
  - 返回：Figma `nodes` 接口原始 JSON（字典）。
  - 顶层字段（常见）：`name`、`lastModified`、`thumbnailUrl`、`version`、`role`、`editorType`、`linkAccess`、`nodes`。
  - 关键字段类型（常见）：`nodes: object`（key 为 nodeId）。
  - `nodes.<nodeId>` 常见字段：`document`、`components`、`componentSets`、`schemaVersion`、`styles`。
  - `nodes.<nodeId>.document` 类型：object（节点子树）。

- `get_nodeids_images(...) -> object`
  - 返回：以 `nodeId:format:scale` 为 key 的映射对象（`nodeId` 中的 `:` 会替换为 `-`），value 至少包含 `filePath` 与 `fileName`。
  - 示例：`{\"1-199:png:2\":{\"filePath\":\"/abs/path/xxx.png\",\"fileName\":\"xxx.png\"}}`
  - 说明：仅按 `nodeId/nodeIds` 直传下载，不做过滤。
  - 说明：`outputDir` 可省略，默认 `./.temp`（最终转为绝对路径）。

- `get_images_tree(...) -> object`
  - 返回结构同 `get_nodeids_images`。
  - 默认过滤规则：`exportSettings` 或 `IMAGE` fill 命中才下载。
  - 可用 `filters` 覆盖默认规则。
  - manifest：默认开启，记录下载状态与元信息，便于中断后继续。

## get_images_tree 实现思路（高层）

1. 统一校验入参：`fileKey/nodeId/outputDir` 必填，`outputDir` 必须绝对路径。
2. 优先使用外部传入的 `nodesJson` 或 `rootDocument`；没有则再通过 `get_nodes` 拉取节点子树 JSON。
4. 在子树内按 `filters` 过滤节点（支持 `id/name/type/characters/hasField`）。
5. 若未显式传 `filters`，默认过滤规则为：`exportSettings` 或 `IMAGE` fill。
6. 为每个命中节点确定导出格式：
   - 若显式传入 `format`，统一使用该格式。
   - 否则优先 `exportSettings.format`，再 fallback 到 `IMAGE` fill 时使用 `png`。
7. 按格式分组调用 images API 批量下载（`batchSize/intervalMs` 节流），并原子写入文件。
8. 若子树解析失败或无可下载节点，直接抛出可读错误，交由上层决定是否改用单节点下载。
9. 下载过程可生成 manifest（默认开启），支持断点续跑与已完成跳过。

## Manifest 结构（示例）

```json
{
  "items": {
    "1-172:png:2.0": {
      "nodeId": "1:172",
      "format": "png",
      "scale": 2.0,
      "filePath": "/abs/path/images/xxxx.png",
      "fileName": "xxxx.png",
      "url": "https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/xxxx"
    }
  }
}
```

### LLM CLI（figma_llm_tool.py）

统一返回 JSON，包含以下**自定义 key**：

- 成功：
  - `success: true`
  - `tool: "get_file" | "get_nodes" | "get_nodeids_images" | "get_images_tree"`
  - `data: <Python API 返回值>`

- 失败：
  - `success: false`
  - `tool: "get_file" | "get_nodes" | "get_nodeids_images" | "get_images_tree"`
  - `error.type: string`
  - `error.message: string`

## generate_assets.py 使用

在节点拉取、预处理、资产导出完成后调用，生成 `assets_Figma.json`：

```bash
# 默认使用 output/figma
python3 scripts/generate_assets.py

# 指定 figma 目录
python3 scripts/generate_assets.py /abs/path/output/figma
```

依赖：`figma-raw.json`、`figma-transform.json`、`figma-baseline-mapping.json`、`raw_parts/*.json`。

## 快速入口

1. 再按 API 使用：`../scripts/figma_fetch.py`
2. 给大模型接入：`./figma_llm_tool_usage.md`

## 调用建议（产品站）

- 先拉取 `figma-raw.json`，按规则拆屏生成 `assets_Figma.json`，用户确认后再导图。
- 导图入口建议使用明确的节点白名单。
- 多 Figma 链接场景：按链接逐次调用 `get_nodes` 并分别落盘；`figma-raw.json` 使用索引结构（`nodes` 存各链接 raw 映射），不强制合并为单一节点树。

## 多链接索引示例

```bash
# 1) 按链接逐次拉取 get_nodes 并落盘到 raw_parts/
python3 ../scripts/figma_llm_tool.py --tool get_nodes --args-json '{"figmaUrl":"<url_a>"}' > /abs/path/figma/raw_parts/raw_<fileKeyA>_<nodeidA>.json
python3 ../scripts/figma_llm_tool.py --tool get_nodes --args-json '{"figmaUrl":"<url_b>"}' > /abs/path/figma/raw_parts/raw_<fileKeyB>_<nodeidB>.json

# 2) 生成索引化 figma-raw.json（示意）
# figma-raw.json.nodes: { "<figma_url_or_hash>": { "fileKey": "...", "nodeIds": [...], "rawFilePath": "..." } }
```

## 约束与注意事项

- 环境变量：`FIGMA_ACCESS_TOKEN`
- `outputDir` / `filePath` 必须使用绝对路径。
- 对外落盘到 `assets_Figma.json.imageDownloads` 时，路径字段统一使用 `filePath`。
- 图片命名统一基于图片 URL 末尾 token 生成文件名。
- 支持格式：`png` / `jpg` / `svg`
- 下载过程使用原子写入（`.part` 临时文件 -> 重命名），避免中断产生损坏文件。
- 规则优先级以本 Skill 的规则文档与阶段主文档为准。

## FIGMA_ACCESS_TOKEN 配置方法（完整）

适用变量名（固定）：`FIGMA_ACCESS_TOKEN`
读取优先级：`显式 accessToken 参数` > `系统环境变量` > `.env` 文件。

1) 当前终端临时生效（最常用）：
```bash
export FIGMA_ACCESS_TOKEN="figd_xxx"
```

2) `.env` 文件（推荐，项目级）：
在项目根目录创建 `.env`：
```dotenv
FIGMA_ACCESS_TOKEN=figd_xxx
```
说明：
- 脚本会自动尝试读取 `.env`（从当前工作目录及脚本目录向上查找）。
- 若已存在同名系统环境变量，则不会被 `.env` 覆盖。

3) 仅单次命令注入（不污染当前 shell）：
```bash
FIGMA_ACCESS_TOKEN="figd_xxx" python3 ../scripts/figma_llm_tool.py --tool fetch_file_json --args-json '{"figmaInput":"<FIGMA_URL>"}'
```

4) zsh 持久化（新终端自动生效）：
```bash
echo 'export FIGMA_ACCESS_TOKEN="figd_xxx"' >> ~/.zshrc
source ~/.zshrc
```

5) bash 持久化（使用 bash 时）：
```bash
echo 'export FIGMA_ACCESS_TOKEN="figd_xxx"' >> ~/.bashrc
source ~/.bashrc
```

6) 显式参数传入（代码/API 优先于环境变量）：
- Python:
```python
from figma_fetch import FigmaFetch
client = FigmaFetch(accessToken="figd_xxx")
```
- LLM JSON 入参：在 `args-json` 中传 `accessToken` 字段。

7) 验证是否配置成功：
```bash
[ -n "$FIGMA_ACCESS_TOKEN" ] && echo "FIGMA_ACCESS_TOKEN 已配置" || echo "未配置"
```

常见错误排查：
- 变量名拼写错误（必须全大写：`FIGMA_ACCESS_TOKEN`）。
- `.env` 不在脚本可搜索路径上（建议放项目根目录）。
- 写入 `~/.zshrc` 后未执行 `source ~/.zshrc`。
- 在 A 终端设置，实际在 B 终端运行（环境未同步）。
- token 已过期或被撤销。

## 设计原则

- 默认提供节流参数（`batchSize`、`intervalMs`）以应对 API 限流
