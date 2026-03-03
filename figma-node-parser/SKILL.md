# Figma Assets Collect

> **角色定位**：Figma 资产采集 Skill，负责通过 `scripts/` 逻辑拉取节点树并导出图片，生成 `assets_Figma.json` 与导出索引。

---

## 激活条件

当用户提到：

- Figma 设计稿解析
- Figma URL 转 schema
- 设计稿节点分析
- 提供 Figma URL（格式：`https://figma.com/file/:key/:name?node-id=:id`）

## 输入

- Figma URL（包含 file key 和 node-id）

**输入检查规则**（validate_url）：

AI 按以下规则执行（无需调用脚本），任一条件不满足则停止并提示：

1. **域名**：必须是 `*.figma.com` 或 `figma.com`，否则提示「无效的 Figma 链接，请确保链接来自 figma.com 域名」
2. **路径格式**：必须为 `/file/` 或 `/design/` 之一，否则提示「无效的 Figma 链接，请使用 file 或 design 格式」
3. **file_key**：路径中必须包含有效的 file key（`/file/:key/` 或 `/design/:key/`，key 为字母数字），否则提示「无效的 Figma 链接，无法解析 file key」
4. **node-id**：URL 参数中必须包含 `node-id`（如 `?node-id=23615-579` 或 `&node-id=23615-579`），否则提示「无效的 Figma 链接，请确保包含 node-id 参数」
5. **不通过**：任一条件不满足则停止并提示；全部通过则继续后续步骤

---

## 输出

> 📄 产出物将保存到对应阶段的输出目录

**产出文件**：

- `当前工作区/output/figma/raw_parts/`（按 Figma 链接拆分的 raw 数据目录）
- `当前工作区/output/figma/figma-raw.json`（节点拉取主文件：统一使用索引结构）
- `当前工作区/output/figma/transform_parts/`（按链接拆分的已过滤节点树，每链接一个文件）
- `当前工作区/output/figma/figma-transform.json`（**索引结构**，指向 transform_parts，供 F01 按需加载，节省 token）
- `当前工作区/output/figma/assets_Figma.json`（**资产索引**，由 `scripts/generate_assets.py` 生成）
- `当前工作区/output/figma/exports/`（PNG 导出目录）
- `当前工作区/output/figma/figma-baseline-mapping.json`（导出索引：nodeId → filePath，供后续进行视觉对比）

**assets_Figma.json Schema**：

```json
{
  "mode": "url_index",
  "fileKey": "<file_key>",
  "version": "<version>",
  "lastModified": "<iso8601>",
  "exportTime": "<iso8601>",
  "nodes": {
    "<figma_url>": {
      "fileKey": "<file_key>",
      "nodeIds": ["<nodeid>"],
      "rawFilePath": "raw_parts/raw_<fileKey>_<nodeid_safe>.json",
      "transformFilePath": "transform_parts/transform_<fileKey>_<nodeid_safe>.json",
      "baselineMappingPath": "figma-baseline-mapping.json"
    }
  },
  "pages": [{ "nodeId": "...", "name": "...", "type": "...", "firstLevelNodes": [...] }],
  "nodeIndex": { "<nodeId>": { "nodeId": "...", "name": "...", "type": "..." } },
  "imageDownloads": {
    "<nodeId>": { "filePath": "exports/xxx.png", "fileName": "xxx.png", "format": "png", "scale": 1 }
  }
}
```

---

## 执行步骤

1. **输入确认**：收集 Figma 链接/节点列表，记录输出路径。
   - **解析 file_keys**：从 Figma URL 中解析文件 Key（如 `https://www.figma.com/file/<file_key>/...`）。
   - 统一写入共享状态 `figma.file_keys`（数组，单链接时长度为 1）。

2. **资产优先级检查**：若 `当前工作区/output/figma/assets_Figma.json` 已存在且可用，**优先直接读取并复用**。
   - 若 `当前工作区/output/figma/exports/` 完整可用：可跳过本轮拉取与导出。
   - 若 `当前工作区/output/figma/exports/` 缺失或不完整：跳过拉取，但仍需执行步骤 8 自动补导出（不询问用户）。
   - 仅当资产文件不存在或不可用时进入步骤 5。

3. **节点拉取**：默认走 `scripts/` 内的逻辑；当脚本**无法执行/下载失败**时允许使用 MCP 作为兜底，并记录兜底原因。
   - 优先使用 `scripts/figma_llm_tool.py` 作为统一入口，按 `references/figma_llm_tool_usage.md` 的规范路由到 `get_file` / `get_nodes`。
   - 若需全量结构分析：调用 `get_file`；若需局部子树：调用 `get_nodes`。
   - **URL 调用策略**：若存在一个或多个 Figma 链接，均必须按链接逐次调用 `get_nodes`（一条链接一次调用），禁止合并为一次调用，避免超时与上下文过大。
   - **raw 落盘要求**：必须基于链接生成 raw 文件，按链接落盘到 `当前工作区/output/figma/raw_parts/`（示例：`raw_<fileKey>_<nodeid_safe>.json`，`nodeid_safe` 需将 `:` 转为 `-`）。
   - **统一主 raw 策略**：`当前工作区/output/figma/figma-raw.json` 必须使用索引结构，且索引存放在 `nodes` 字段中。
   - **统一索引 Schema（强制）**：
     ```json
     {
       "mode": "url_index",
       "nodes": {
         "<figma_url_or_hash>": {
           "fileKey": "<file_key>",
           "nodeIds": ["<nodeid>"],
           "rawFilePath": "当前工作区/output/figma/raw_parts/raw_<fileKey>_<nodeid_safe>.json"
         }
       }
     }
     ```
   - **结构门禁**：`figma-raw.json` 必须符合上述索引 Schema（单链接时 `nodes` 仅包含 1 个索引项）。
   - **本地落盘要求**：节点拉取完成后，必须至少落盘 `raw_parts/*.json`，并产出索引口径 `figma-raw.json`。
   - **失败门禁**：脚本入口不可用、调用失败或产物结构不一致时，必须 `BLOCK` 并停止推进；仅允许在记录“失败原因 + 兜底方案 + 结构校验结果”后继续。

4. **节点记录与资产索引**：在步骤 3、5、7 完成后，调用 `scripts/generate_assets.py` 生成 `当前工作区/output/figma/assets_Figma.json`。脚本汇总 figma-raw、figma-transform、figma-baseline-mapping 与 raw_parts，产出完整索引（nodes、pages、nodeIndex、imageDownloads）。

   ```bash
   python3 scripts/generate_assets.py [当前工作区/output/figma]
   ```

5. **预处理（figma-transform，索引模式）**：从 `figma-raw.json` 索引读取 `raw_parts` 文件，逐个解析节点树，过滤不可见节点（`visible === false`、`opacity < 1e-6`），**按链接分别输出**到 `当前工作区/output/figma/transform_parts/`（示例：`transform_<fileKey>_<nodeid_safe>.json`），并生成索引 `当前工作区/output/figma/figma-transform.json`。索引 Schema 与 figma-raw 一致，便于 F01 按需加载，**避免全量合并带来的 token 消耗**。详见 `references/figma-node-interpretation.md` 第 1 节过滤规则。

**figma-transform.json 索引 Schema**：

```json
{
  "mode": "url_index",
  "nodes": {
    "<figma_url_or_hash>": {
      "fileKey": "<file_key>",
      "nodeIds": ["<nodeid>"],
      "transformFilePath": "transform_parts/transform_<fileKey>_<nodeid_safe>.json"
    }
  }
}
```

> `transformFilePath` 相对于 `figma-transform.json` 所在目录，便于后续阶段按需解析。

6. **导出策略**：仅导出**第一层 layer 节点**图片（first-level layer nodes），不包含倍率导出（无 1x/2x 概念）。

7. **资产导出**（**默认需要导出图片**，且**必须自动执行**，无需用户确认）：完成步骤 5-6 后，**立即**调用 `scripts/figma_llm_tool.py` 导出 PNG，**优先使用 `get_nodeids_images`**；当需要按子树规则补充导出或兜底时再使用 `get_images_tree`。仅对第一层 layer 节点执行导出，输出到 `当前工作区/output/figma/exports/`，并写入导出索引 `当前工作区/output/figma/figma-baseline-mapping.json`（nodeId → filePath 映射）。禁止分步询问用户是否导出，Asset 采集流程应一气呵成。导出完成后**必须**调用 `scripts/generate_assets.py` 生成 `assets_Figma.json`。

8. **跳过处理**（用户选择「没有」时执行）：
   - 设置 `shared.figma.skipped = true`
   - 记录跳过原因到状态管理器
   - **不阻断后续流程**，继续执行下一个 SKILL

9. **完整性自检**（仅在有 Figma 时执行）：核对节点覆盖、导出数量与索引一致性。若发现异常，仅通过 `scripts/` 逻辑重试修复。

## 当前工作区/output/figma/exports 清理规则

- **覆盖重跑**：删除旧 `当前工作区/output/figma/exports/` 再导出。
- **续跑补导出**：保留旧导出，仅补齐缺失第一层 layer 节点。
- **禁止混用**：不允许在旧导出目录上增量追加（除非选择“续跑补导出”）。

---

## 脚本清单

| 脚本 | 用途 |
|------|------|
| `figma_llm_tool.py` | 统一入口：get_nodes / get_file / get_nodeids_images / get_images_tree |
| `figma_transform.py` | 预处理：过滤不可见节点，产出 transform_parts |
| `generate_assets.py` | 生成 assets_Figma.json（依赖 raw、transform、baseline-mapping） |

---

## 环境变量

- `FIGMA_TOKEN` / `FIGMA_ACCESS_TOKEN` — Figma Personal Access Token

## 注意事项

- Figma Token 需要妥善保管，不要提交到 Git，不要明文暴露给用户
- 节点 ID 格式：`-1:0` 或 `123:456`
- 支持解析 Frame、Component、Instance、Text、Rectangle 等节点类型
- **Python 中间产物**：脚本运行后产生的 `scripts/__pycache__/` 及 `.pyc` 文件为中间产物，执行完成后应删除或加入 `.gitignore`，不纳入版本管理
