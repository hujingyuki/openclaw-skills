# OpenClaw Skills - 前端技术方案生成

全栈研发专家技能集合，支持从飞书 PRD 和 Figma 设计稿生成前端技术方案。

## 技能列表

### 1. feishu-prd-parser

飞书 PRD 文档解析技能。将飞书文档转化为结构化 Markdown PRD，提取内嵌图片和流程图。

**输入：** 飞书 docx 链接  
**输出：** 结构化 Markdown PRD + 图片 URL 列表

### 2. figma-node-parser

Figma 设计稿节点解析技能。通过 Figma API 获取设计稿节点树，输出 JSON schema。

**输入：** Figma URL（包含 file key 和 node-id）  
**输出：** JSON schema（组件层级、样式、约束、自动布局）

**环境变量：**
- `FIGMA_TOKEN` — Figma Personal Access Token

### 3. frontend-tech-solution

前端技术方案生成技能。基于 PRD 和 Figma 设计稿 schema，生成完整的前端实现技术方案。

**输入：** 结构化 PRD + Figma schema  
**输出：** 飞书文档链接（技术方案）

**技术栈：** React + TypeScript + TailwindCSS + shadcn/ui

---

## 使用流程

```
1. 提供飞书 PRD 文档链接
   ↓
2. feishu-prd-parser 解析 PRD → 结构化 Markdown
   ↓
3. 提供 Figma 设计稿 URL
   ↓
4. figma-node-parser 解析设计稿 → JSON schema
   ↓
5. frontend-tech-solution 生成技术方案 → 飞书文档链接
```

---

## 安装

将技能文件夹复制到 OpenClaw 技能目录：

```bash
cp -r feishu-prd-parser ~/.openclaw/workspace/skills/
cp -r figma-node-parser ~/.openclaw/workspace/skills/
cp -r frontend-tech-solution ~/.openclaw/workspace/skills/
```

---

## 配置

### Figma Token

在环境变量中配置：

```bash
export FIGMA_TOKEN=figd_xxx
```

或在 `.env` 文件中配置：

```
FIGMA_TOKEN=figd_xxx
```

---

## 开发

### 目录结构

```
skills/
├── feishu-prd-parser/
│   ├── SKILL.md
│   ├── scripts/
│   │   └── parse-prd.sh
│   └── templates/
│       └── prd-output.md
├── figma-node-parser/
│   ├── SKILL.md
│   ├── scripts/
│   │   └── parse-figma.sh
│   └── schemas/
│       └── ui-component.schema.json
└── frontend-tech-solution/
    ├── SKILL.md
    ├── scripts/
    │   └── generate-solution.sh
    └── templates/
        └── tech-solution.md
```

### SKILL.md 结构

每个技能的 `SKILL.md` 包含：
- 激活条件
- 输入/输出说明
- 使用方式
- 处理流程
- 环境变量
- 依赖工具
- 示例

---

## 技术栈偏好

- **框架:** React 18+
- **语言:** TypeScript
- **样式:** TailwindCSS
- **组件库:** shadcn/ui
- **状态管理:** Zustand
- **路由:** React Router v6
- **HTTP 客户端:** Axios + TanStack Query
- **表单:** React Hook Form + Zod
- **测试:** Vitest + React Testing Library

---

## 作者

灵码 (LingMa) 🦞 — Full-Stack R&D Expert

## 仓库

https://github.com/hujingyuki/openclaw-skills

---

## License

MIT
