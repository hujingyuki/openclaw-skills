#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对外封装能力：FigmaFetch"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional
import json
import os
import re

from figma_core import FigmaError, get_file, get_nodeids_images, get_nodes


def _iter_subtree(node: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    stack = [node]
    while stack:
        cur = stack.pop()
        yield cur
        for child in cur.get("children", []) or []:
            stack.append(child)


def _filter_match(node: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    if node.get("type") in {"DOCUMENT", "CANVAS"}:
        return False
    if "id" in filters and node.get("id") != filters["id"]:
        return False
    if "name" in filters and node.get("name") != filters["name"]:
        return False
    if "type" in filters and node.get("type") != filters["type"]:
        return False
    if "characters" in filters:
        text = node.get("characters", "")
        if filters["characters"] not in text:
            return False
    if "hasField" in filters:
        field = filters["hasField"]
        if field not in node:
            return False
    return True


def _resolve_export_settings(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    export_settings = node.get("exportSettings")
    if isinstance(export_settings, list) and export_settings:
        return export_settings

    fills = node.get("fills")
    if not isinstance(fills, list):
        return []

    fallbacks: List[Dict[str, Any]] = []
    for fill in fills:
        if not isinstance(fill, dict) or fill.get("type") != "IMAGE":
            continue
        guessed = None
        name = node.get("name")
        if isinstance(name, str):
            marker = re.search(r"#(png|jpg|svg)#", name, re.IGNORECASE)
            if marker:
                guessed = marker.group(1).lower()
        fallbacks.append(
            {
                "suffix": "",
                "format": guessed or "png",
                "constraint": {
                    "type": "SCALE",
                    "value": 1,
                },
            }
        )
    return fallbacks


class FigmaFetch:
    def __init__(self, accessToken: Optional[str] = None) -> None:
        self.access_token = accessToken

    def get_file(self, figmaUrl: str, timeoutSeconds: int = 60) -> Dict[str, Any]:
        return get_file(figmaUrl, access_token=self.access_token, timeout_seconds=timeoutSeconds)

    def get_nodes(
        self,
        figmaUrl: Optional[str] = None,
        fileKey: Optional[str] = None,
        nodeIds: Optional[List[str]] = None,
        timeoutSeconds: int = 60,
    ) -> Dict[str, Any]:
        return get_nodes(
            figma_url=figmaUrl,
            file_key=fileKey,
            node_ids=nodeIds,
            access_token=self.access_token,
            timeout_seconds=timeoutSeconds,
        )

    def get_nodeids_images(
        self,
        fileKey: str,
        outputDir: str,
        nodeId: Optional[str] = None,
        nodeIds: Optional[List[str]] = None,
        format: Optional[str] = "png",
        scale: int = 1,
        batchSize: int = 50,
        intervalMs: int = 5000,
        force: bool = False,
        useManifest: bool = True,
        timeoutSeconds: int = 60,
    ) -> Dict[str, Dict[str, Any]]:
        return get_nodeids_images(
            file_key=fileKey,
            node_id=nodeId,
            node_ids=nodeIds,
            output_dir=outputDir,
            format=format,
            scale=scale,
            batch_size=batchSize,
            interval_ms=intervalMs,
            force=force,
            use_manifest=useManifest,
            access_token=self.access_token,
            timeout_seconds=timeoutSeconds,
        )

    def get_images_tree(
        self,
        fileKey: str,
        outputDir: str,
        nodeId: Optional[str] = None,
        nodeIds: Optional[List[str]] = None,
        format: Optional[str] = None,
        scale: int = 1,
        filters: Optional[Dict[str, Any]] = None,
        nodesJson: Optional[Dict[str, Any]] = None,
        rootDocument: Optional[Dict[str, Any]] = None,
        batchSize: int = 50,
        intervalMs: int = 5000,
        force: bool = False,
        useManifest: bool = True,
        timeoutSeconds: int = 60,
    ) -> Dict[str, Dict[str, Any]]:
        target_ids = nodeIds or ([nodeId] if nodeId else [])
        if not target_ids:
            raise FigmaError("ParamError", "nodeId 或 nodeIds 必填")
        if rootDocument is not None and len(target_ids) > 1:
            raise FigmaError("ParamError", "rootDocument 仅支持单个 nodeId 递归")

        if nodesJson is None and rootDocument is None:
            nodesJson = self.get_nodes(fileKey=fileKey, nodeIds=target_ids, timeoutSeconds=timeoutSeconds)
        node_map = nodesJson.get("nodes", {}) if nodesJson else {}

        downloaded: Dict[str, Dict[str, Any]] = {}
        id_to_name: Dict[str, str] = {}
        for root_id in target_ids:
            root_doc = rootDocument or node_map.get(root_id, {}).get("document")
            if not root_doc:
                raise FigmaError("DataError", "递归解析失败：nodesJson/rootDocument 缺少 document")

            candidates: List[Dict[str, Any]] = []
            for n in _iter_subtree(root_doc):
                if filters is None:
                    if _resolve_export_settings(n):
                        candidates.append(n)
                else:
                    if _filter_match(n, filters):
                        candidates.append(n)

            ids_by_format: Dict[str, List[str]] = {}
            for n in candidates:
                nid = n.get("id")
                if not nid:
                    continue
                name = n.get("name")
                if isinstance(name, str):
                    id_to_name[nid] = name
                fmt = format
                if not fmt:
                    settings = _resolve_export_settings(n)
                    fmt = str(settings[0].get("format", "")).lower() if settings else None
                if not fmt:
                    continue
                ids_by_format.setdefault(fmt, []).append(nid)

            for fmt, ids in ids_by_format.items():
                try:
                    downloaded.update(
                        get_nodeids_images(
                            file_key=fileKey,
                            output_dir=outputDir,
                            format=fmt,
                            scale=scale,
                            node_ids=ids,
                            batch_size=batchSize,
                            interval_ms=intervalMs,
                            force=force,
                            use_manifest=useManifest,
                            access_token=self.access_token,
                            timeout_seconds=timeoutSeconds,
                        )
                    )
                except FigmaError as err:
                    if err.error_type == "HttpError":
                        failed: List[Dict[str, Any]] = []
                        for nid in ids:
                            try:
                                get_nodeids_images(
                                    file_key=fileKey,
                                    output_dir=outputDir,
                                    format=fmt,
                                    scale=scale,
                                    node_ids=[nid],
                                    batch_size=1,
                                    interval_ms=0,
                                    force=force,
                                    use_manifest=useManifest,
                                    access_token=self.access_token,
                                    timeout_seconds=timeoutSeconds,
                                )
                            except FigmaError:
                                failed.append({"nodeId": nid, "name": id_to_name.get(nid)})
                        if failed:
                            os.makedirs(outputDir, exist_ok=True)
                            err_path = os.path.join(
                                outputDir,
                                f".figma-download-errors.{fileKey}.{fmt}.json",
                            )
                            with open(err_path, "w", encoding="utf-8") as f:
                                json.dump(
                                    {
                                        "format": fmt,
                                        "totalIds": len(ids),
                                        "failed": failed,
                                        "message": err.message,
                                    },
                                    f,
                                    ensure_ascii=False,
                                    indent=2,
                                )
                    raise

        if not downloaded:
            return {}

        return downloaded
