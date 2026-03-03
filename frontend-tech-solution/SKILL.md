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

- **飞书文档链接**（优先，调用 feishu_doc 创建）
- **或本地 Markdown 文件**（备选，当飞书 API 不可用时）
- 技术方案 Markdown 内容

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

1. 读取 PRD 文档，提取功能需求
2. 读取 Figma schema，分析组件结构
3. 生成技术方案文档（包含以下章节）：
   - 项目概述
   - 技术栈说明
   - 组件设计（基于 shadcn）
   - 页面结构
   - API 接口设计
   - 状态管理方案
   - 路由设计
   - 测试计划
   - 开发计划
4. **尝试**调用 `feishu_wiki action=create` 创建飞书文档
5. **如果飞书 API 失败**，使用 `write` 保存到本地 `/当前工作区/output/` 目录
6. 返回文档链接（飞书或本地路径）

## 环境变量

无

## 依赖工具

- `feishu_wiki` — 创建飞书文档
- `write` — 生成临时文件

## 输出文档结构

````markdown
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

| 接口     | 方法 | 路径          | 说明 |
| -------- | ---- | ------------- | ---- |
| 获取产品 | GET  | /api/products | ...  |

## 6. 状态管理

- 全局状态：Zustand
- 本地状态：useState/useReducer

## 7. 路由设计

```tsx
// react-router 配置
```
````

## 8. 测试计划

- 单元测试
- 组件测试
- E2E 测试

## 9. 开发计划

| 阶段 | 任务     | 预计工时 |
| ---- | -------- | -------- |
| 1    | 环境搭建 | 2h       |
| ...  | ...      | ...      |

```

## 注意事项

- 组件优先使用 shadcn 开源方案
- 技术方案需要可执行、可落地
- 测试计划需要覆盖核心功能
- **飞书 API 可能失败**（权限/格式问题），需 fallback 到本地文件
- 本地文件保存路径：`/当前工作区/output/<项目名>-<日期>.md`
- 创建成功后优先返回飞书链接，其次返回本地路径
```
