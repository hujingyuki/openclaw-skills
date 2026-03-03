#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Figma 核心能力：请求、解析、下载。
语义函数：get_file / get_nodes / get_nodeids_images
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse, urlencode
from urllib.request import Request, urlopen


FIGMA_API_BASE = "https://api.figma.com/v1"
SUPPORTED_IMAGE_FORMATS = {"png", "jpg", "svg"}


@dataclass
class FigmaError(Exception):
    error_type: str
    message: str

    def __str__(self) -> str:
        return f"{self.error_type}: {self.message}"


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _load_dotenv(start_dir: str) -> Dict[str, str]:
    """向上查找 .env 并解析，返回键值。"""
    cur = os.path.abspath(start_dir)
    while True:
        candidate = os.path.join(cur, ".env")
        if os.path.isfile(candidate):
            env: Dict[str, str] = {}
            for line in _read_text(candidate).splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("\"").strip("'")
            return env
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return {}


def _get_access_token(access_token: Optional[str]) -> str:
    if access_token:
        return access_token
    env_token = os.environ.get("FIGMA_ACCESS_TOKEN")
    if env_token:
        return env_token
    dotenv = _load_dotenv(os.getcwd())
    if "FIGMA_ACCESS_TOKEN" in dotenv:
        return dotenv["FIGMA_ACCESS_TOKEN"]
    raise FigmaError("AuthError", "accessToken is required (FIGMA_ACCESS_TOKEN 未配置)")


def _request_json(url: str, access_token: str, timeout_seconds: int) -> Dict[str, Any]:
    req = Request(url, headers={"X-Figma-Token": access_token})
    try:
        with urlopen(req, timeout=timeout_seconds) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except Exception as exc:
        raise FigmaError("HttpError", str(exc)) from exc


def _request_binary(url: str, output_path: str, timeout_seconds: int) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    tmp_path = output_path + ".part"
    req = Request(url)
    try:
        with urlopen(req, timeout=timeout_seconds) as resp, open(tmp_path, "wb") as f:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
        os.replace(tmp_path, output_path)
    except Exception as exc:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        raise FigmaError("DownloadError", str(exc)) from exc


def parse_figma_url(figma_url: str) -> Tuple[str, Optional[str]]:
    """返回 (file_key, node_id?)"""
    if not figma_url:
        raise FigmaError("ParamError", "figmaUrl 不能为空")
    parsed = urlparse(figma_url)
    parts = [p for p in parsed.path.split("/") if p]
    file_key = None
    if "file" in parts:
        idx = parts.index("file")
        if idx + 1 < len(parts):
            file_key = parts[idx + 1]
    if "design" in parts and not file_key:
        idx = parts.index("design")
        if idx + 1 < len(parts):
            file_key = parts[idx + 1]
    if not file_key:
        raise FigmaError("ParamError", "无法从 URL 解析 fileKey")

    qs = parse_qs(parsed.query)
    node_id = None
    if "node-id" in qs and qs["node-id"]:
        node_id = qs["node-id"][0].replace("-", ":")
    return file_key, node_id


def get_file(figma_url: str, access_token: Optional[str] = None, timeout_seconds: int = 60) -> Dict[str, Any]:
    token = _get_access_token(access_token)
    file_key, _ = parse_figma_url(figma_url)
    url = f"{FIGMA_API_BASE}/files/{file_key}"
    return _request_json(url, token, timeout_seconds)


def get_nodes(
    figma_url: Optional[str] = None,
    file_key: Optional[str] = None,
    node_ids: Optional[List[str]] = None,
    access_token: Optional[str] = None,
    timeout_seconds: int = 60,
) -> Dict[str, Any]:
    """优先 figma_url。若无 url，则 file_key + node_ids 必填。"""
    if figma_url:
        file_key, node_id = parse_figma_url(figma_url)
        if not node_id:
            raise FigmaError("ParamError", "figmaUrl 缺少 node-id 参数")
        node_ids = [node_id]
    if not file_key or not node_ids:
        raise FigmaError("ParamError", "缺少 fileKey 或 nodeIds")
    ids = ",".join(node_ids)
    token = _get_access_token(access_token)
    encoded_ids = urlencode({"": ids})[1:]
    url = f"{FIGMA_API_BASE}/files/{file_key}/nodes?ids={encoded_ids}"
    return _request_json(url, token, timeout_seconds)


def _sanitize_token(token: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", token)


def _image_name_from_url(image_url: str, fmt: str) -> str:
    try:
        parsed = urlparse(image_url)
        tail = parsed.path.split("/")[-1] if parsed.path else ""
        raw_token = re.sub(r"\.[a-zA-Z0-9]+$", "", tail)
        compact_token = raw_token.replace("-", "")
        safe_token = _sanitize_token(compact_token)
        if not safe_token:
            raise ValueError("empty token")
        return f"{safe_token}.{fmt}"
    except Exception:
        raise FigmaError("NameError", f"图片命名失败：无法从 URL 提取文件名 token ({image_url})")


def _manifest_path(output_dir: str, file_key: str, fmt: str, scale: int) -> str:
    safe_key = _sanitize_token(file_key)
    return os.path.join(output_dir, f".figma-download-manifest.{safe_key}.{fmt}.json")


def _load_manifest(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"items": {}}
    try:
        return json.loads(_read_text(path))
    except Exception:
        return {"items": {}}


def _save_manifest(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _manifest_item_key(node_id: str, fmt: str, scale: int) -> str:
    safe_node = node_id.replace(":", "-")
    return f"{safe_node}:{fmt}:{float(scale)}"


def get_nodeids_images(
    file_key: str,
    output_dir: str,
    format: Optional[str] = "png",
    scale: int = 1,
    node_id: Optional[str] = None,
    node_ids: Optional[List[str]] = None,
    batch_size: int = 50,
    interval_ms: int = 5000,
    force: bool = False,
    use_manifest: bool = True,
    access_token: Optional[str] = None,
    timeout_seconds: int = 60,
) -> Dict[str, Dict[str, Any]]:
    if not output_dir:
        output_dir = os.path.abspath(".temp")
    if not os.path.isabs(output_dir):
        raise FigmaError("ParamError", "outputDir 必须是绝对路径")
    if not file_key:
        raise FigmaError("ParamError", "fileKey 必填")
    if format and format not in SUPPORTED_IMAGE_FORMATS:
        raise FigmaError("ParamError", f"不支持的 format: {format}")

    token = _get_access_token(access_token)

    target_ids = node_ids or ([node_id] if node_id else [])
    if not target_ids:
        raise FigmaError("ParamError", "nodeId 或 nodeIds 必填")

    fmt = format or "png"
    return _download_images(
        file_key,
        target_ids,
        output_dir,
        fmt,
        scale,
        token,
        timeout_seconds,
        batch_size,
        interval_ms,
        force,
        use_manifest,
    )
def _download_images(
    file_key: str,
    node_ids: List[str],
    output_dir: str,
    fmt: str,
    scale: int,
    token: str,
    timeout_seconds: int,
    batch_size: int,
    interval_ms: int,
    force: bool,
    use_manifest: bool,
) -> Dict[str, Dict[str, Any]]:
    results: Dict[str, Dict[str, Any]] = {}
    manifest_path = _manifest_path(output_dir, file_key, fmt, scale) if use_manifest else None
    manifest = _load_manifest(manifest_path) if manifest_path else {"items": {}}
    items: Dict[str, Dict[str, Any]] = manifest.get("items", {}) or {}
    for i in range(0, len(node_ids), batch_size):
        batch = node_ids[i : i + batch_size]
        ids = ",".join(batch)
        url = f"{FIGMA_API_BASE}/images/{file_key}?ids={ids}&format={fmt}&scale={scale}"
        data = _request_json(url, token, timeout_seconds)
        images = data.get("images", {}) or {}
        for node_id, img_url in images.items():
            if not img_url:
                continue
            item_key = _manifest_item_key(node_id, fmt, scale)
            if not force and item_key in items:
                existing = items[item_key].get("filePath")
                existing_name = items[item_key].get("fileName")
                if existing and os.path.exists(existing):
                    results[item_key] = {
                        "filePath": existing,
                        "fileName": existing_name or os.path.basename(existing),
                    }
                    continue
            filename = _image_name_from_url(img_url, fmt)
            out_path = os.path.join(output_dir, filename)
            if os.path.exists(out_path) and not force:
                item_key = _manifest_item_key(node_id, fmt, scale)
                results[item_key] = {
                    "filePath": out_path,
                    "fileName": filename,
                }
                continue
            _request_binary(img_url, out_path, timeout_seconds)
            item_key = _manifest_item_key(node_id, fmt, scale)
            results[item_key] = {
                "filePath": out_path,
                "fileName": filename,
            }
            if manifest_path:
                items[item_key] = {
                    "nodeId": node_id,
                    "format": fmt,
                    "scale": float(scale),
                    "filePath": out_path,
                    "fileName": filename,
                    "url": img_url,
                }
                manifest["items"] = items
                _save_manifest(manifest_path, manifest)
        if i + batch_size < len(node_ids):
            time.sleep(interval_ms / 1000.0)
    return results
