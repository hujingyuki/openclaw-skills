#!/bin/bash
# parse-prd.sh - 飞书 PRD 文档解析脚本

set -e

DOCX_URL="$1"

if [ -z "$DOCX_URL" ]; then
    echo "Usage: $0 <feishu_docx_url>"
    exit 1
fi

# 从 URL 提取 doc_token (格式：/docx/XXX)
DOC_TOKEN=$(echo "$DOCX_URL" | grep -oP '/docx/\K[A-Za-z0-9]+' || true)

if [ -z "$DOC_TOKEN" ]; then
    echo "Error: Invalid feishu docx URL"
    exit 1
fi

echo "Parsing PRD from: $DOCX_URL"
echo "Doc Token: $DOC_TOKEN"

# 调用 feishu_doc 读取文档
echo "Reading document..."
# 这里通过 openclaw 工具调用，实际使用时由 AI 调用 feishu_doc 工具

echo "Done. Output will be structured markdown."
