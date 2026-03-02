# 前端技术方案：{{project_name}}

## 1. 项目概述

### 业务背景
{{business_background}}

### 目标用户
{{target_users}}

### 核心功能
{{core_features}}

---

## 2. 技术栈

| 类别 | 技术选型 | 说明 |
|------|----------|------|
| 框架 | React 18+ | 主流前端框架 |
| 语言 | TypeScript | 类型安全 |
| 样式 | TailwindCSS | 原子化 CSS |
| 组件库 | shadcn/ui | 开源可定制组件 |
| 状态管理 | Zustand | 轻量级全局状态 |
| 路由 | React Router v6 | 声明式路由 |
| HTTP 客户端 | Axios + TanStack Query | 数据请求与缓存 |
| 表单 | React Hook Form + Zod | 表单验证 |
| 测试 | Vitest + React Testing Library | 单元/组件测试 |

---

## 3. 组件设计

### 3.1 原子组件（shadcn）

以下组件直接使用 shadcn/ui：

- `Button` — 按钮
- `Input` — 输入框
- `Form` — 表单容器
- `Dialog` — 对话框
- `Table` — 表格
- `Card` — 卡片
- `Select` — 下拉选择
- `Tabs` — 标签页
- `Toast` — 消息提示

安装命令：
```bash
npx shadcn-ui@latest add button input form dialog table card select tabs toast
```

### 3.2 业务组件

根据 PRD 需求定制：

{{custom_components}}

---

## 4. 页面结构

{{page_structure}}

---

## 5. API 接口设计

| 接口名称 | 方法 | 路径 | 请求参数 | 响应数据 | 说明 |
|----------|------|------|----------|----------|------|
| {{api_name}} | {{method}} | {{path}} | {{request}} | {{response}} | {{description}} |

---

## 6. 状态管理方案

### 全局状态（Zustand）

```typescript
// stores/{{store_name}}.ts
import { create } from 'zustand'

interface {{store_name}}State {
  // 状态定义
}

interface {{store_name}}Actions {
  // 动作定义
}

export const use{{store_name}}Store = create<{{store_name}}State & {{store_name}}Actions>()((set) => ({
  // 实现
}))
```

### 本地状态

- 组件内部状态使用 `useState` / `useReducer`
- 表单状态使用 `React Hook Form`

---

## 7. 路由设计

```typescript
// App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/products" element={<ProductList />} />
        {/* 其他路由 */}
      </Routes>
    </BrowserRouter>
  )
}
```

---

## 8. 测试计划

### 8.1 单元测试

- 工具函数测试
- 自定义 Hooks 测试

### 8.2 组件测试

- 原子组件交互测试
- 业务组件渲染测试

### 8.3 E2E 测试

- 核心用户流程测试
- 关键路径测试

---

## 9. 开发计划

| 阶段 | 任务 | 预计工时 | 交付物 |
|------|------|----------|--------|
| 1 | 环境搭建 + 基础配置 | 2h | 项目初始化 |
| 2 | 原子组件集成 | 4h | shadcn 组件库 |
| 3 | 业务组件开发 | {{hours}} | 定制组件 |
| 4 | 页面开发 | {{hours}} | 完整页面 |
| 5 | API 对接 | {{hours}} | 数据联调 |
| 6 | 测试 + 修复 | {{hours}} | 测试报告 |
| 7 | 部署上线 | 2h | 生产环境 |

---

## 10. 附录

### 10.1 项目结构

```
src/
├── components/
│   ├── ui/          # shadcn 组件
│   └── business/    # 业务组件
├── pages/           # 页面组件
├── stores/          # Zustand stores
├── hooks/           # 自定义 Hooks
├── utils/           # 工具函数
├── types/           # TypeScript 类型
├── api/             # API 调用
└── App.tsx
```

### 10.2 参考链接

- [shadcn/ui 文档](https://ui.shadcn.com/)
- [React 文档](https://react.dev/)
- [TailwindCSS 文档](https://tailwindcss.com/)

---

*文档生成时间：{{timestamp}}*
