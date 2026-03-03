#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 assets_Figma.json：汇总节点索引、页面索引、导出索引。
依赖：figma-raw.json、figma-transform.json、figma-baseline-mapping.json、raw_parts。
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_pages_and_node_index(raw_data: Dict[str, Any]) -> tuple[List[Dict], Dict[str, Dict]]:
    """从 raw 数据提取 pages 和 nodeIndex（第一层 layer 节点）"""
    nodes_data = raw_data.get("data") or raw_data
    nodes = nodes_data.get("nodes", {})
    pages: List[Dict] = []
    node_index: Dict[str, Dict] = {}

    for node_id, node_obj in nodes.items():
        doc = node_obj.get("document")
        if not doc:
            continue
        children = doc.get("children") or []
        first_level = []
        for c in children:
            item = {
                "nodeId": c.get("id"),
                "name": c.get("name"),
                "type": c.get("type", ""),
            }
            first_level.append(item)
            if c.get("id"):
                node_index[c["id"]] = item

        pages.append({
            "nodeId": node_id,
            "name": doc.get("name", ""),
            "type": doc.get("type", ""),
            "firstLevelNodes": first_level,
        })

    return pages, node_index


def _build_image_downloads(
    baseline_mapping: Dict[str, str],
    figma_dir: str,
    format: str = "png",
    scale: int = 1,
) -> Dict[str, Dict[str, Any]]:
    """从 figma-baseline-mapping.json 构建 imageDownloads（路径为相对 figma 目录）"""
    result: Dict[str, Dict[str, Any]] = {}
    for node_id, path in baseline_mapping.items():
        if not isinstance(path, str):
            continue
        path = path.strip().replace("\\", "/")
        if not path:
            continue
        if os.path.isabs(path):
            try:
                path = os.path.relpath(path, figma_dir)
            except ValueError:
                pass
        fileName = os.path.basename(path)
        result[node_id] = {
            "filePath": path,
            "fileName": fileName,
            "format": format,
            "scale": scale,
        }
    return result


def generate_assets(figma_dir: str) -> Dict[str, Any]:
    """
    生成 assets_Figma.json 内容。
    figma_dir: output/figma 目录的绝对路径
    """
    figma_dir = os.path.abspath(figma_dir)
    raw_index_path = os.path.join(figma_dir, "figma-raw.json")
    transform_index_path = os.path.join(figma_dir, "figma-transform.json")
    baseline_path = os.path.join(figma_dir, "figma-baseline-mapping.json")

    raw_index = _load_json(raw_index_path)
    if not raw_index or "nodes" not in raw_index:
        raise FileNotFoundError(f"未找到有效 figma-raw.json: {raw_index_path}")

    transform_index = _load_json(transform_index_path)
    baseline_mapping = _load_json(baseline_path) or {}

    # 合并 nodes 索引（raw + transform + baseline）
    nodes_index: Dict[str, Dict] = {}
    raw_nodes = raw_index.get("nodes", {})
    transform_nodes = (transform_index or {}).get("nodes", {})

    for url_key, raw_entry in raw_nodes.items():
        entry = dict(raw_entry)
        transform_entry = transform_nodes.get(url_key, {})
        if "transformFilePath" in transform_entry:
            entry["transformFilePath"] = transform_entry["transformFilePath"]
        else:
            raw_path = entry.get("rawFilePath", "")
            if raw_path:
                # 推导 transform 路径
                base = os.path.basename(raw_path).replace("raw_", "transform_")
                entry["transformFilePath"] = f"transform_parts/{base}"
        entry["baselineMappingPath"] = "figma-baseline-mapping.json"
        nodes_index[url_key] = entry

    # 从第一个 raw 文件提取 pages、nodeIndex、version、lastModified
    pages: List[Dict] = []
    node_index: Dict[str, Dict] = {}
    version = ""
    last_modified = ""

    for url_key, entry in raw_nodes.items():
        raw_path = entry.get("rawFilePath")
        if not raw_path:
            continue
        abs_raw = os.path.join(figma_dir, raw_path)
        raw_data = _load_json(abs_raw)
        if not raw_data:
            continue
        nodes_data = raw_data.get("data") or raw_data
        version = nodes_data.get("version", "") or version
        last_modified = nodes_data.get("lastModified", "") or last_modified
        p, ni = _extract_pages_and_node_index(raw_data)
        pages.extend(p)
        node_index.update(ni)

    file_key = ""
    if raw_nodes:
        first_entry = next(iter(raw_nodes.values()))
        file_key = first_entry.get("fileKey", "")

    image_downloads = _build_image_downloads(baseline_mapping, figma_dir)

    return {
        "mode": "url_index",
        "fileKey": file_key,
        "version": version,
        "lastModified": last_modified,
        "exportTime": datetime.now(timezone.utc).isoformat(),
        "nodes": nodes_index,
        "pages": pages,
        "nodeIndex": node_index,
        "imageDownloads": image_downloads,
    }


def main() -> int:
    if len(sys.argv) < 2:
        # 默认使用脚本所在目录的 output/figma
        script_dir = os.path.dirname(os.path.abspath(__file__))
        figma_dir = os.path.join(os.path.dirname(script_dir), "output", "figma")
    else:
        figma_dir = sys.argv[1]

    try:
        assets = generate_assets(figma_dir)
        out_path = os.path.join(os.path.abspath(figma_dir), "assets_Figma.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(assets, f, ensure_ascii=False, indent=2)
        print(f"已生成: {out_path}")
        return 0
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
