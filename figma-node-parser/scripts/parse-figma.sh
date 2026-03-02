#!/bin/bash
# parse-figma.sh - Figma 设计稿节点解析脚本

set -e

FIGMA_URL="$1"
FIGMA_TOKEN="${FIGMA_TOKEN:-}"

if [ -z "$FIGMA_URL" ]; then
    echo "Usage: $0 <figma_url>"
    exit 1
fi

if [ -z "$FIGMA_TOKEN" ]; then
    echo "Error: FIGMA_TOKEN environment variable not set"
    exit 1
fi

# 从 URL 提取 file_key 和 node_id
# 格式：https://figma.com/file/:key/:name?node-id=:id
FILE_KEY=$(echo "$FIGMA_URL" | grep -oP '/file/\K[A-Za-z0-9]+' || true)
NODE_ID=$(echo "$FIGMA_URL" | grep -oP 'node-id=\K[0-9-:]+' || true)

if [ -z "$FILE_KEY" ] || [ -z "$NODE_ID" ]; then
    echo "Error: Invalid Figma URL. Expected format: https://figma.com/file/:key/:name?node-id=:id"
    exit 1
fi

echo "Parsing Figma design: $FIGMA_URL"
echo "File Key: $FILE_KEY"
echo "Node ID: $NODE_ID"

# 调用 Figma API
API_URL="https://api.figma.com/v1/files/${FILE_KEY}/nodes?ids=${NODE_ID}"
echo "Calling Figma API: $API_URL"

RESPONSE=$(curl -s -X GET "$API_URL" \
    -H "X-Figma-Token: $FIGMA_TOKEN" \
    -H "Content-Type: application/json")

echo "$RESPONSE" | jq '.'

echo "Done. Output is JSON schema."
