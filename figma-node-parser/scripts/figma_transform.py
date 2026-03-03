#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Figma 预处理：过滤不可见节点，产出 transform 节点树。
规则见 references/figma-node-interpretation.md 第 1 节。
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional


def _filter_fills_strokes(arr: Optional[List[Dict]], key: str) -> Optional[List[Dict]]:
    """过滤 fills/strokes/effects 中 visible=false 或 opacity=0 的项"""
    if not isinstance(arr, list):
        return arr
    out = []
    for item in arr:
        if not isinstance(item, dict):
            out.append(item)
            continue
        if item.get("visible") is False:
            continue
        op = item.get("opacity")
        if op is not None and (op == 0 or (isinstance(op, (int, float)) and op < 1e-6)):
            continue
        out.append(item)
    return out if out else None


def _filter_node(node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """递归过滤不可见节点"""
    if node.get("visible") is False:
        return None
    op = node.get("opacity")
    if op is not None and (op == 0 or (isinstance(op, (int, float)) and op < 1e-6)):
        return None

    out = dict(node)
    # 过滤 fills/strokes/effects
    for key in ("fills", "strokes", "effects"):
        if key in out and out[key] is not None:
            filtered = _filter_fills_strokes(out[key], key)
            out[key] = filtered

    children = out.get("children")
    if isinstance(children, list):
        filtered_children = []
        for c in children:
            fc = _filter_node(c)
            if fc is not None:
                filtered_children.append(fc)
        out["children"] = filtered_children if filtered_children else []

    return out


def transform_raw(raw_path: str, output_path: str) -> None:
    """从 raw 文件读取，过滤后写入 transform 文件"""
    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 支持 figma_llm_tool 返回格式 { success, data: { nodes: {...} } }
    if not isinstance(data, dict):
        raise ValueError("raw 格式无效")
    nodes_data = data.get("data") or data
    nodes = nodes_data.get("nodes", {})
    if not nodes:
        raise ValueError("raw 中无 nodes")

    result_nodes = {}
    for node_id, node_obj in nodes.items():
        doc = node_obj.get("document")
        if not doc:
            result_nodes[node_id] = node_obj
            continue
        filtered_doc = _filter_node(doc)
        if filtered_doc is not None:
            result_nodes[node_id] = {"document": filtered_doc}

    out_data = {"nodes": result_nodes}
    if "name" in nodes_data:
        out_data["name"] = nodes_data["name"]
    if "lastModified" in nodes_data:
        out_data["lastModified"] = nodes_data["lastModified"]
    if "version" in nodes_data:
        out_data["version"] = nodes_data["version"]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(out_data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: figma_transform.py <raw_path> <output_path>", file=sys.stderr)
        sys.exit(1)
    raw_path = sys.argv[1]
    output_path = sys.argv[2]
    transform_raw(raw_path, output_path)
