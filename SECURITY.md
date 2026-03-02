# 安全配置说明

## Token 存储位置

### GitHub Token
- **存储位置:** `~/.git-credentials` (git credential store)
- **权限:** 仅当前用户可读 (600)
- **用途:** 自动推送代码到 GitHub

### Figma Token
- **存储位置:** 环境变量 `FIGMA_TOKEN`
- **建议:** 添加到 `~/.bashrc` 或 `~/.zshrc`
- **用途:** 调用 Figma API 解析设计稿

## 安全实践

1. **不在代码中硬编码 Token**
   - `.env.example` 使用占位符
   - 真实 Token 通过环境变量或凭证存储

2. **不在对话中显示 Token**
   - 任何输出中不打印完整 Token
   - 需要调试时用 `***` 遮蔽

3. **定期轮换 Token**
   - GitHub: https://github.com/settings/tokens
   - Figma: https://www.figma.com/developers/api

## 检查清单

- [x] `.env.example` 使用占位符
- [x] Git credentials 存储在 `~/.git-credentials`
- [x] Remote URL 不包含 Token
- [x] 对话中不显示敏感信息
