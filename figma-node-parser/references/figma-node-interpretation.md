# Figma 节点解读规则

> **用途**：F01 `figma-design-analysis` SKILL 在高保真模式下，从 `figma-transform.json` 识别布局模式、提取组件结构、执行语义分组时遵循本规则。产出物为结构化的 `page_component_spec.json`，不直接生成 CSS 代码。

## 目录

1. 输入与预处理
2. 布局模式识别
3. 组件归并规则

---

## 1. 输入与预处理

> 如果已产出 `figma-transform.json` 时，不可见节点过滤已自动完成，AI 直接消费过滤后的数据，**跳过下方手动过滤规则**。仅当预处理未运行或运行失败时，才按下方规则手动处理。

- **数据来源**：`figma-transform` 为目标数据源。`figma-transform.json` 始终为索引模式（`mode: "url_index"`），从 `transform_parts/` 按需加载各文件。数据由 `figma-node-parser` 从 `raw_parts/` 过滤不可见节点产出。布局与样式的数值（宽高、间距、字号、颜色、圆角等）**必须从节点字段读取**，不得使用设计稿外的默认值或估算值。
- **输入源**：`fileKey + node-id` 的节点树（`FRAME / INSTANCE / TEXT / VECTOR`）、`layout`、`fills/strokes`、`textStyle`、`absoluteBoundingBox`。
- **过滤不可见节点**（必须先执行，再参与识别）：
  - 节点级：`node.visible === false` 的节点整节点移除；`node.opacity === 0`（或数值小于 1e-6）的节点整节点移除。
  - 数组项：`fills` / `strokes` / `effects` / `background` 中 `visible === false` 或 `opacity === 0` 的项移除。
  - 后续识别必须基于「已做可见性过滤」的子树。
- 只保留目标子树，忽略无关画板与远程库噪声。
- `INSTANCE` 先展开可渲染结构，再应用 override（文字、状态、尺寸）。
- 输出前先做**语义分组**：导航、筛选、列表、表格、卡片、操作区。

---

## 2. 布局模式识别

> 本节规则用于从 Figma 节点的 `layout` 属性中识别页面布局模式，输出到 `page_component_spec.json` 的 `layout` 字段。

### 2.1 Flex 布局识别

从 Figma 节点的 `layout` 属性推断布局模式：

- `layout.mode = row` → 水平排列（对应 CSS `flex-direction: row`）
- `layout.mode = column` → 垂直排列（对应 CSS `flex-direction: column`）
- `gap / padding / alignItems / justifyContent` → 从节点的 `itemSpacing`、`paddingLeft/Right/Top/Bottom`、`counterAxisAlignItems` 等字段读取

### 2.2 尺寸模式识别

- `fixed` → 固定尺寸，数值从 `absoluteBoundingBox` 或 layout 相关字段读取
- `fill` → 弹性填充（主轴方向）
- `hug` → 内容自适应

### 2.3 定位模式识别

- `layout.mode = none`：
  - 纯定位场景 → `position: absolute`，记录 `x/y/width/height`
  - 业务区块场景 → 标注为流式布局候选

### 2.4 高级布局模式

从组件结构组合推断高级布局模式（输出到 `page_component_spec.json` 的 `patterns` 字段）：

- **sidebar-content**：左侧固定宽度窄栏 + 右侧弹性内容区
- **master-detail**：左侧列表 + 右侧详情面板
- **filter-bar**：搜索框 + 筛选下拉 + 日期选择 + 操作按钮的水平排列
- **table**：表头 + 数据行 + 分页，可含排序/筛选/展开/选择
- **accordion**：可折叠面板组，可嵌套表格或表单
- **modal**：对话框覆盖层

---

## 3. 组件归并规则

> 本节规则用于将 Figma 中的多个原子/分子节点归并为语义类型。F01 只输出库无关的语义类型（如 Table / Select），不输出具体组件库信息。分子归并规则由 adapter config 的 `molecule_merge` 字段定义。

### 3.1 通用归并原则

- 同构结构合并为同一组件类型（列表项、表格行、标签、按钮）
- 组件拆分优先按**业务语义**，而不是 Figma 图层命名
- 图标策略：识别阶段记录图标节点位置，不做具体 SVG 提取

### 3.2 分子组件归并

分子组件的归并规则由 adapter config 的 `molecule_merge` 字段定义。通用模式：

- 表头节点 + 单元格节点 → 表格组件（表头 → `columns` 定义，单元格 → 行数据）
- 选择器分子节点 → 下拉选择组件
- 筛选/排序实例 → 表格 `columns` 属性

### 3.3 Variant 属性记录

F01 在识别阶段**只记录原始 Variant 值**，不做 Props 转换。Props 转换由 F03 通过 adapter 的 `variant_props` 完成。

- 记录原始 key-value 对，如 `{ "颜色": "品牌色", "尺寸": "大", "状态": "禁用" }`
- 写入 `page_component_spec.json` 的 `components[].variants` 字段

### 3.4 INSTANCE 节点识别（库无关）

- 遍历所有 INSTANCE 节点
- 节点名称即为语义类型（如 `Button`、`Table`、`Select`）
- 若 adapter config 的 `recognition.aliases` 中有该节点名称的映射，转为通用语义类型
- **不查 import 路径、不查默认 Props**（这些由 F03 通过 adapter 的 `implementation` 完成）
- 未被识别的 INSTANCE 节点标注 `[待确认]`
