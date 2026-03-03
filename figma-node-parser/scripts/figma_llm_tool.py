#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM 统一调用入口：get_file / get_nodes / get_nodeids_images / get_images_tree"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict

from figma_core import FigmaError
from figma_fetch import FigmaFetch


def _print(data: Dict[str, Any], pretty: bool) -> None:
    if pretty:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(data, ensure_ascii=False))


def _success(tool: str, data: Any, message: str = "") -> Dict[str, Any]:
    return {"success": True, "tool": tool, "data": data, "message": message}


def _failure(tool: str, err: FigmaError) -> Dict[str, Any]:
    return {
        "success": False,
        "tool": tool,
        "message": err.message,
        "error": {"type": err.error_type, "message": err.message},
    }


def _validate_get_file(data: Any) -> None:
    if not isinstance(data, dict):
        raise FigmaError("SchemaError", "get_file 返回值必须是 object")
    doc = data.get("document")
    if not isinstance(doc, dict):
        raise FigmaError("SchemaError", "get_file 返回值缺少 document object")


def _validate_get_nodes(data: Any) -> None:
    if not isinstance(data, dict):
        raise FigmaError("SchemaError", "get_nodes 返回值必须是 object")
    nodes = data.get("nodes")
    if not isinstance(nodes, dict):
        raise FigmaError("SchemaError", "get_nodes 返回值缺少 nodes object")


def _validate_images_map(data: Any) -> None:
    if not isinstance(data, dict):
        raise FigmaError("SchemaError", "images 返回值必须是 object")
    for key, val in data.items():
        if not isinstance(key, str) or not isinstance(val, dict):
            raise FigmaError("SchemaError", "images 返回值结构不合法")
        if "filePath" not in val or "fileName" not in val:
            raise FigmaError("SchemaError", "images 每项必须包含 filePath 和 fileName")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", required=True)
    parser.add_argument("--args-json", required=True)
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    tool = args.tool
    try:
        payload = json.loads(args.args_json)
    except Exception as exc:
        _print(_failure(tool, FigmaError("ParamError", f"args-json 非法: {exc}")), args.pretty)
        return 2

    access_token = payload.get("accessToken")
    client = FigmaFetch(accessToken=access_token)

    try:
        if tool == "get_file":
            data = client.get_file(figmaUrl=payload.get("figmaUrl"), timeoutSeconds=payload.get("timeoutSeconds", 60))
            _validate_get_file(data)
        elif tool == "get_nodes":
            data = client.get_nodes(
                figmaUrl=payload.get("figmaUrl"),
                fileKey=payload.get("fileKey"),
                nodeIds=payload.get("nodeIds"),
                timeoutSeconds=payload.get("timeoutSeconds", 60),
            )
            _validate_get_nodes(data)
        elif tool == "get_nodeids_images":
            output_dir = payload.get("outputDir") or os.path.abspath(".temp")
            data = client.get_nodeids_images(
                fileKey=payload.get("fileKey"),
                nodeId=payload.get("nodeId"),
                nodeIds=payload.get("nodeIds"),
                outputDir=output_dir,
                format=payload.get("format", "png"),
                scale=payload.get("scale", 1),
                batchSize=payload.get("batchSize", 50),
                intervalMs=payload.get("intervalMs", 5000),
                force=payload.get("force", False),
                useManifest=payload.get("useManifest", True),
                timeoutSeconds=payload.get("timeoutSeconds", 60),
            )
            _validate_images_map(data)
        elif tool == "get_images_tree":
            output_dir = payload.get("outputDir") or os.path.abspath(".temp")
            data = client.get_images_tree(
                fileKey=payload.get("fileKey"),
                nodeId=payload.get("nodeId"),
                nodeIds=payload.get("nodeIds"),
                outputDir=output_dir,
                format=payload.get("format"),
                scale=payload.get("scale", 1),
                filters=payload.get("filters"),
                nodesJson=payload.get("nodesJson"),
                rootDocument=payload.get("rootDocument"),
                batchSize=payload.get("batchSize", 50),
                intervalMs=payload.get("intervalMs", 5000),
                force=payload.get("force", False),
                useManifest=payload.get("useManifest", True),
                timeoutSeconds=payload.get("timeoutSeconds", 60),
            )
            _validate_images_map(data)
            if not data:
                _print(
                    _success(
                        tool,
                        data,
                        "未命中可下载节点，返回空结果。可调整 filters/format 或改用 get_nodeids_images。",
                    ),
                    args.pretty,
                )
                return 0
        else:
            raise FigmaError("ParamError", f"未知 tool: {tool}")
        _print(_success(tool, data, "ok"), args.pretty)
        return 0
    except FigmaError as err:
        if args.verbose:
            _print(_failure(tool, err), args.pretty)
        else:
            _print(_failure(tool, err), args.pretty)
        return 1


if __name__ == "__main__":
    sys.exit(main())
