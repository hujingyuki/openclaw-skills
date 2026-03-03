#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书文档获取处理器 - Python 实现
直接调用飞书 Open API 获取文档内容，图片和流程图保存到本地（无 FDS 上传）

依赖: 仅 Python 标准库 (urllib, json, os, pathlib)
环境变量: FEISHU_APP_ID, FEISHU_APP_SECRET

命令行:
  python fetchFeishuDocHandler.py validate <feishu_url>
  python fetchFeishuDocHandler.py fetch <feishu_url> <save_path>
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ============ 常量 ============
FEISHU_BASE_URL = 'https://open.feishu.cn/open-apis'
TOKEN_URL = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
TOKEN_ERROR_CODES = {4001, 20006, 20013, 99991663, 99991668, 99991677, 99991669, 99991664, 99991665}
CACHE_TTL = 300  # 5 分钟
BLOCK_TYPE_IMAGE = (21, 27)
BLOCK_TYPE_WHITEBOARD = 43


# ============ 工具函数 ============
def validate_feishu_url(feishu_url: str) -> Dict[str, Any]:
    """
    验证飞书链接格式
    :return: { valid: bool, type?: str, error?: str }
    """
    if not feishu_url or not isinstance(feishu_url, str):
        return {'valid': False, 'error': '飞书链接不能为空'}
    trimmed = feishu_url.strip()
    if not re.match(r'^https?://[a-zA-Z0-9-]+\.feishu\.cn/', trimmed):
        return {'valid': False, 'error': '无效的飞书链接，请确保链接来自 feishu.cn 域名'}
    if re.search(r'/wiki/([a-zA-Z0-9_-]+)', trimmed):
        return {'valid': True, 'type': 'wiki'}
    if re.search(r'/docx/([a-zA-Z0-9_-]+)', trimmed):
        return {'valid': True, 'type': 'docx'}
    if re.search(r'/docs/([a-zA-Z0-9_-]+)', trimmed):
        return {'valid': True, 'type': 'docs'}
    return {'valid': False, 'error': '不支持的飞书文档类型，请提供 wiki、docx 或 docs 链接'}


def save_document(content: str, save_path: str) -> None:
    """保存文档内容到文件"""
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    Path(save_path).write_text(content, encoding='utf-8')
    print('[SUCCESS] 文档已保存到: ' + save_path)


def extract_document_id(input_str: str) -> Optional[str]:
    input_str = input_str.strip()
    for pattern in [
        r'/docx/([a-zA-Z0-9_-]+)',
        r'/docs/([a-zA-Z0-9_-]+)',
        r'/documents/([a-zA-Z0-9_-]+)',
        r'^([a-zA-Z0-9_-]{10,})$',
    ]:
        m = re.search(pattern, input_str, re.I)
        if m:
            return m.group(1)
    return None


def extract_wiki_token(input_str: str) -> Optional[str]:
    input_str = input_str.strip()
    m = re.search(r'/wiki/([a-zA-Z0-9_-]+)', input_str, re.I)
    if m:
        token = m.group(1)
    else:
        m = re.match(r'^([a-zA-Z0-9_-]{10,})$', input_str)
        token = m.group(1) if m else None
    if token and '?' in token:
        token = token.split('?')[0]
    return token


def process_document_id(input_str: str) -> str:
    doc_id = extract_document_id(input_str)
    if not doc_id:
        raise ValueError(f'无法从 "{input_str}" 提取有效的文档ID')
    return doc_id


def process_wiki_token(input_str: str) -> str:
    token = extract_wiki_token(input_str)
    if not token:
        raise ValueError(f'无法从 "{input_str}" 提取有效的Wiki Token')
    return token


def process_block_id(block_id: str) -> str:
    if not block_id:
        raise ValueError('块ID不能为空')
    if not re.match(r'^[a-zA-Z0-9_-]{5,}$', block_id):
        raise ValueError('块ID格式无效')
    return block_id


def _sanitize_filename(s: str, max_len: int = 80) -> str:
    """将字符串转为安全文件名，去除非法字符"""
    s = re.sub(r'[<>:"/\\|?*\s]+', '_', s)
    s = re.sub(r'_+', '_', s).strip('_')
    return s[:max_len] if s else 'doc'


def _is_mermaid_line(line: str) -> bool:
    """判断是否为 mermaid 语法行（含空行，用于块内换行）"""
    s = line.strip()
    if not s:
        return True
    return bool(re.match(r'(flowchart|sequenceDiagram|graph|stateDiagram|classDiagram|erDiagram|gantt|pie|journey)\s', s, re.I) or
                '-->' in s or '->>' in s or '->' in s or 'participant' in s or
                s.startswith(('alt', 'par', 'end', 'opt', 'loop')) or
                re.match(r'^\s*[A-Z]\s', s) or re.match(r'^\s*[A-Za-z0-9_]+\[', s))


def _is_block_end(line: str, block_type: str) -> bool:
    """判断是否为代码块结束（遇到下一节标题等）"""
    s = line.strip()
    if not s:
        return False
    #  strip Markdown 标题前缀后再判断
    s_plain = re.sub(r'^#+\s*', '', s)
    if block_type == 'mermaid':
        return bool(re.match(r'^\d+\.\d+\s', s_plain) or re.match(r'^\d+\.\d+\.\d+\s', s_plain) or
                    re.match(r'^(关键业务规则|页面支持|序号|涉及系统|异常场景)', s_plain))
    if block_type == 'gherkin':
        return bool(re.match(r'^[一二三四五六七八九十]+[、.]', s_plain))
    return False


def _wrap_code_blocks(content: str) -> str:
    """将 flowchart、sequenceDiagram、Feature 等代码块用 ``` 包裹"""
    lines = content.split('\n')
    result: List[str] = []
    i = 0
    mermaid_start = re.compile(r'^\s*(flowchart\s|sequenceDiagram\s*|graph\s|stateDiagram\s|classDiagram\s|erDiagram\s|gantt\s|pie\s|journey\s)', re.I)
    gherkin_start = re.compile(r'^\s*(Feature|Scenario|Background|Examples):', re.I)
    gherkin_lang_start = re.compile(r'^\s*#\s*language\s*:\s*zh-CN\s*$', re.I)

    while i < len(lines):
        line = lines[i]
        if mermaid_start.search(line):
            block_lines = [line]
            i += 1
            while i < len(lines):
                next_line = lines[i]
                if _is_block_end(next_line, 'mermaid'):
                    break
                block_lines.append(next_line)
                i += 1
            result.append('```mermaid')
            result.extend(block_lines)
            result.append('```')
            result.append('')
        elif gherkin_lang_start.search(line):
            block_lines = [line]
            i += 1
            while i < len(lines):
                next_line = lines[i]
                if _is_block_end(next_line, 'gherkin'):
                    break
                if not next_line.strip() and block_lines and block_lines[-1].strip():
                    block_lines.append(next_line)
                    i += 1
                    continue
                if not next_line.strip() and i + 1 < len(lines):
                    peek = lines[i + 1].strip()
                    if not re.match(r'^\s*(Given|When|Then|And|But|Scenario|Background|Examples|Feature|#)', peek, re.I):
                        break
                block_lines.append(next_line)
                i += 1
            result.append('```gherkin')
            result.extend(block_lines)
            result.append('```')
            result.append('')
        elif gherkin_start.search(line):
            block_lines = [line]
            i += 1
            while i < len(lines):
                next_line = lines[i]
                if _is_block_end(next_line, 'gherkin'):
                    break
                if not next_line.strip() and block_lines and block_lines[-1].strip():
                    block_lines.append(next_line)
                    i += 1
                    continue
                if not next_line.strip() and i + 1 < len(lines):
                    peek = lines[i + 1].strip()
                    if not re.match(r'^\s*(Given|When|Then|And|But|Scenario|Background|Examples)', peek, re.I):
                        break
                block_lines.append(next_line)
                i += 1
            result.append('```gherkin')
            result.extend(block_lines)
            result.append('```')
            result.append('')
        else:
            result.append(line)
            i += 1
    return '\n'.join(result)


def _replace_image_placeholders(content: str, image_paths: List[str]) -> str:
    """将文档中的 image.png 占位符替换为实际图片路径（Markdown 图片语法）"""
    for rel_path in image_paths:
        content = content.replace('image.png', f'![image]({rel_path})', 1)
    return content


def _escape_table_cell(s: str) -> str:
    """转义表格单元格中的 | 字符"""
    return s.replace('|', '\\|').replace('\n', ' ')


def _convert_tables_to_markdown(content: str) -> str:
    """
    将飞书 raw_content 中的表格数据（每行一单元格）转为 Markdown 表格格式。
    飞书表格在 raw_content 中通常为：表头1\\n表头2\\n单元格1\\n单元格2\\n...（两两成对）
    仅当连续可配对行数 >= 3 行（即至少 6 行）时才转换，避免误伤正文。
    """
    lines = content.split('\n')
    result: List[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith('|') and stripped.endswith('|'):
            result.append(line)
            i += 1
            continue

        if stripped.startswith('```'):
            result.append(line)
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                result.append(lines[i])
                i += 1
            if i < len(lines):
                result.append(lines[i])
                i += 1
            continue

        if stripped and not stripped.startswith(('#', '```', '|', 'flowchart', 'sequenceDiagram', 'Feature', 'Scenario')):
            collected: List[tuple] = []
            j = i
            while j < len(lines):
                s = lines[j].strip()
                if not s:
                    j += 1
                    continue
                if s.startswith(('#', '```', 'flowchart', 'sequenceDiagram', 'Feature', 'Scenario')):
                    break
                if re.match(r'^\d+\.\d+\s', s) or re.match(r'^\d+\.\s', s):
                    break
                if re.match(r'^(一|二|三|四|五|六|七|八|九|十|十一|十二)[、.]', s):
                    break
                collected.append((j, s))
                j += 1
            n = len(collected)
            if any('-->' in c[1] or '->>' in c[1] or 'participant' in c[1] for c in collected):
                for idx, _ in collected:
                    result.append(lines[idx])
                i = collected[-1][0] + 1 if collected else j
                continue
            best_rows: Optional[List[List[str]]] = None
            best_cols = 0
            best_end = i
            for n_cols in (2, 3, 4):
                if n < n_cols * 3:
                    continue
                if n % n_cols != 0:
                    continue
                rows = []
                for k in range(0, n, n_cols):
                    row = [_escape_table_cell(collected[k + c][1]) for c in range(n_cols)]
                    rows.append(row)
                if len(rows) >= 3 and (best_rows is None or len(rows) > len(best_rows or [])):
                    best_rows = rows
                    best_cols = n_cols
                    best_end = collected[n - 1][0] + 1 if collected else j
            if best_rows and best_cols:
                result.append('| ' + ' | '.join(best_rows[0]) + ' |')
                result.append('| ' + ' | '.join(['---'] * best_cols) + ' |')
                for row in best_rows[1:]:
                    result.append('| ' + ' | '.join(row) + ' |')
                result.append('')
                i = best_end
                continue

        result.append(line)
        i += 1
    return '\n'.join(result)


def _enhance_markdown_format(content: str) -> str:
    """
    增强 Markdown 格式，保留项目标号、标题等结构。
    - 文档首行（非空）-> # 文档标题
    - 一、二、三、... 十、 -> # 一级标题
    - 1. 2. 3. (独立成行的节标题) -> ## 二级标题
    - 1.1 2.1 2.2 -> ### 三级标题
    - 1.1.1 2.1.1 -> #### 四级标题
    - 表格、列表、代码块等保持原样
    """
    lines = content.split('\n')
    result: List[str] = []
    in_code_block = False
    in_table = False
    prev_line_blank = True
    first_content_line = True

    for i, line in enumerate(lines):
        stripped = line.strip()
        orig_line = line

        # 跳过已有 Markdown 标题
        if stripped.startswith('#'):
            result.append(line)
            prev_line_blank = False
            in_table = False
            first_content_line = False
            continue

        # 追踪代码块状态
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            result.append(line)
            prev_line_blank = False
            in_table = False
            first_content_line = False
            continue

        if in_code_block:
            result.append(line)
            prev_line_blank = not stripped
            first_content_line = False
            continue

        # 表格：包含 | 且非标题模式，保持原样
        if '|' in stripped and not re.match(r'^#+\s', stripped):
            in_table = True
            result.append(line)
            prev_line_blank = False
            first_content_line = False
            continue

        # 表格后的空行或分隔行
        if in_table and (not stripped or re.match(r'^[\s\-:|]+$', stripped)):
            result.append(line)
            prev_line_blank = not stripped
            if not stripped:
                in_table = False
            continue

        in_table = False

        # 空行保持
        if not stripped:
            result.append(line)
            prev_line_blank = True
            continue

        # 文档首行作为标题（非表格、非代码、非已有#）
        if first_content_line and len(stripped) > 2 and '|' not in stripped:
            result.append('# ' + stripped)
            first_content_line = False
            prev_line_blank = False
            continue

        first_content_line = False

        # 一级标题：一、二、三、... 十一、 或 第X章
        if re.match(r'^(一|二|三|四|五|六|七|八|九|十|十一|十二)[、.]\s*.+', stripped):
            result.append('# ' + stripped)
            prev_line_blank = False
            continue

        # 四级标题：1.1.1 2.1.1 等
        if re.match(r'^\d+\.\d+\.\d+\s+.+', stripped) and len(stripped) > 6:
            result.append('#### ' + stripped)
            prev_line_blank = False
            continue

        # 三级标题：1.1 2.1 2.2 等（需避免误伤表格、列表）
        if re.match(r'^\d+\.\d+\s+.+', stripped) and '|' not in stripped:
            result.append('### ' + stripped)
            prev_line_blank = False
            continue

        # 二级标题：1. 2. 3. 等（独立成行且上一行为空，避免误伤列表项）
        if prev_line_blank and re.match(r'^\d+[\.、]\s+.+', stripped) and len(stripped) > 3:
            if not re.match(r'^(\d+)[\.、]\s*$', stripped):  # 排除纯序号
                result.append('## ' + stripped)
                prev_line_blank = False
                continue

        result.append(line)
        prev_line_blank = False

    return '\n'.join(result)


def process_whiteboard_id(whiteboard_id: str) -> str:
    if not whiteboard_id:
        raise ValueError('画板ID不能为空')
    normalized = whiteboard_id
    if 'feishu.cn/board/' in whiteboard_id:
        m = re.search(r'board/([^/?]+)', whiteboard_id)
        if m:
            normalized = m.group(1)
        else:
            raise ValueError('无法从URL中提取画板ID')
    if not re.match(r'^[a-zA-Z0-9_-]{5,}$', normalized):
        raise ValueError('画板ID格式无效')
    return normalized


# ============ 内存缓存 ============
class MemoryCache:
    def __init__(self, ttl: int = CACHE_TTL):
        self._cache: Dict[str, tuple] = {}
        self._ttl = ttl

    def set(self, key: str, data: Any, ttl_sec: Optional[int] = None) -> None:
        ttl = ttl_sec or self._ttl
        self._cache[key] = (data, time.time() + ttl)

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        data, expires_at = self._cache[key]
        if time.time() > expires_at:
            del self._cache[key]
            return None
        return data

    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False


wiki_cache = MemoryCache()
tenant_token_cache: Dict[str, tuple] = {}


# ============ 飞书 API 服务 ============
class FeishuApiService:
    def __init__(self, user_key: str, app_id: str, app_secret: str):
        self.user_key = user_key
        self.app_id = app_id
        self.app_secret = app_secret

    def _get_access_token(self) -> str:
        cached = tenant_token_cache.get(self.user_key)
        if cached and cached[1] > time.time():
            return cached[0]

        resp = self._http_post(TOKEN_URL, {
            'app_id': self.app_id,
            'app_secret': self.app_secret,
        })
        if resp.get('code') != 0:
            raise RuntimeError(f"获取租户访问令牌失败：{resp.get('msg', '未知错误')}")

        token = resp['tenant_access_token']
        expires_at = time.time() + resp.get('expire', 7200)
        tenant_token_cache[self.user_key] = (token, expires_at)
        return token

    def _http_request(
        self,
        url: str,
        method: str = 'GET',
        data: Optional[dict] = None,
        headers: Optional[dict] = None,
        binary: bool = False,
    ) -> Any:
        h = dict(headers or {})
        if method == 'POST':
            h.setdefault('Content-Type', 'application/json')
        body = None
        if data is not None and method == 'POST':
            body = json.dumps(data).encode('utf-8')

        req = Request(url, data=body, headers=h, method=method)
        try:
            with urlopen(req, timeout=30) as r:
                raw = r.read()
                if binary:
                    return raw
                resp = json.loads(raw.decode('utf-8'))
                code = resp.get('code')
                if code is not None and code != 0:
                    raise RuntimeError(resp.get('msg', 'API错误'))
                # 部分接口（如 token）无 data 包装，直接返回整包
                return resp.get('data', resp)
        except HTTPError as e:
            raw = ''
            try:
                if e.fp:
                    raw = e.read().decode('utf-8')
            except Exception:
                pass
            try:
                err_data = json.loads(raw)
                code = err_data.get('code')
                if code in TOKEN_ERROR_CODES:
                    if self.user_key in tenant_token_cache:
                        del tenant_token_cache[self.user_key]
                    return self._http_request(url, method, data, headers, binary)
            except Exception:
                pass
            raise RuntimeError(f'API请求失败: {e.code} {raw or str(e)}')
        except URLError as e:
            raise RuntimeError(f'请求失败: {e.reason}')

    def _http_post(self, url: str, data: dict) -> dict:
        return self._http_request(url, 'POST', data)

    def _get(self, endpoint: str, params: Optional[dict] = None,
             binary: bool = False) -> Any:
        url = f'{FEISHU_BASE_URL}{endpoint}'
        if params:
            url = f'{url}?{urlencode(params)}'
        token = self._get_access_token()
        headers = {'Authorization': f'Bearer {token}'}
        return self._http_request(url, 'GET', headers=headers, binary=binary)

    def convert_wiki_to_document_id(self, wiki_url: str) -> str:
        token = process_wiki_token(wiki_url)
        cached = wiki_cache.get(f'wiki:{token}')
        if cached:
            return cached

        resp = self._get('/wiki/v2/spaces/get_node', {'token': token, 'obj_type': 'wiki'})
        node = resp.get('node') if isinstance(resp, dict) else None
        if not node or not node.get('obj_token'):
            raise RuntimeError(f'无法从Wiki节点获取文档ID: {token}')

        doc_id = node['obj_token']
        wiki_cache.set(f'wiki:{token}', doc_id)
        return doc_id

    def get_document_content(self, document_id: str, lang: int = 0) -> str:
        doc_id = process_document_id(document_id)
        resp = self._get(f'/docx/v1/documents/{doc_id}/raw_content', {'lang': lang})
        return resp.get('content', '') if isinstance(resp, dict) else ''

    def get_document_blocks(self, document_id: str, page_size: int = 500) -> List[dict]:
        doc_id = process_document_id(document_id)
        all_blocks = []
        page_token = ''

        while True:
            params = {'page_size': page_size, 'document_revision_id': -1}
            if page_token:
                params['page_token'] = page_token

            resp = self._get(f'/docx/v1/documents/{doc_id}/blocks', params)
            items = resp.get('items', []) if isinstance(resp, dict) else []
            all_blocks.extend(items)
            page_token = resp.get('page_token', '') if isinstance(resp, dict) else ''
            if not page_token:
                break

        return all_blocks

    def get_block_content(self, document_id: str, block_id: str) -> dict:
        doc_id = process_document_id(document_id)
        safe_block_id = process_block_id(block_id)
        return self._get(
            f'/docx/v1/documents/{doc_id}/blocks/{safe_block_id}',
            {'document_revision_id': -1}
        )

    def get_image_resource(self, media_id: str) -> bytes:
        if not media_id:
            raise ValueError('媒体ID不能为空')
        return self._get(f'/drive/v1/medias/{media_id}/download', binary=True)

    def get_whiteboard_thumbnail(self, whiteboard_id: str) -> bytes:
        wid = process_whiteboard_id(whiteboard_id)
        return self._get(
            f'/board/v1/whiteboards/{wid}/download_as_image',
            {},
            binary=True
        )

    def extract_and_save_resources(
        self,
        document_id: str,
        blocks: List[dict],
        output_dir: str,
        doc_base_name: str,
    ) -> tuple:
        """提取图片和画板，保存到本地，返回 (images, attachments, whiteboards)。
        images 中 filePath 为绝对路径，relPath 为相对路径（用于文档内链接）"""
        images: List[dict] = []
        attachments: List[dict] = []
        whiteboards: List[dict] = []
        img_idx = 0
        wb_idx = 0

        block_map = {b['block_id']: b for b in blocks if b.get('block_id')}
        images_dir = Path(output_dir) / 'images'
        images_dir.mkdir(parents=True, exist_ok=True)
        processed_block_ids: set = set()
        processed_image_tokens: Dict[str, str] = {}  # token -> rel_path，避免同一图片重复保存

        def process_block_sync(block: dict) -> None:
            nonlocal img_idx, wb_idx
            block_type = block.get('block_type')
            block_id = block.get('block_id', '')
            if block_id in processed_block_ids:
                return
            processed_block_ids.add(block_id)

            if block_type in BLOCK_TYPE_IMAGE and block.get('image', {}).get('token'):
                try:
                    token = block['image']['token']
                    if token in processed_image_tokens:
                        images.append({
                            'blockId': block_id,
                            'filePath': str((Path(output_dir) / processed_image_tokens[token]).resolve()),
                            'relPath': processed_image_tokens[token],
                            'token': token,
                        })
                        return
                    image_data = self.get_image_resource(token)
                    if image_data:
                        img_idx += 1
                        fname = f'{doc_base_name}_image_{img_idx}.png'
                        path = images_dir / fname
                        path.write_bytes(image_data)
                        rel_path = f'images/{fname}'
                        processed_image_tokens[token] = rel_path
                        images.append({
                            'blockId': block_id,
                            'filePath': str(path.resolve()),
                            'relPath': rel_path,
                            'token': token,
                        })
                except Exception as e:
                    print(f'[WARN] 获取图片失败 (block_id={block_id}): {e}')

            if block_type == BLOCK_TYPE_WHITEBOARD and block.get('board', {}).get('token'):
                try:
                    whiteboard_id = block['board']['token']
                    thumb_data = self.get_whiteboard_thumbnail(whiteboard_id)
                    if thumb_data:
                        wb_idx += 1
                        fname = f'{doc_base_name}_whiteboard_{wb_idx}.png'
                        path = images_dir / fname
                        path.write_bytes(thumb_data)
                        rel_path = f'images/{fname}'
                        whiteboards.append({
                            'blockId': block_id,
                            'filePath': str(path.resolve()),
                            'relPath': rel_path,
                            'whiteboardId': whiteboard_id,
                        })
                except Exception as e:
                    print(f'[WARN] 获取画板缩略图失败 (block_id={block_id}): {e}')

            for child_id in block.get('children', []):
                child = block_map.get(child_id)
                if not child:
                    try:
                        child = self.get_block_content(document_id, child_id)
                        if child:
                            block_map[child_id] = child
                    except Exception:
                        continue
                if child:
                    process_block_sync(child)

        for block in blocks:
            process_block_sync(block)

        return images, attachments, whiteboards


# ============ 主入口 ============
def fetch_feishu_doc(
    file_url: str,
    save_path: str,
    app_id: Optional[str] = None,
    app_secret: Optional[str] = None,
    machine_id: Optional[str] = None,
) -> dict:
    """
    获取飞书文档内容及资源，保存文档到 save_path，图片和画板均保存到同目录下 images/
    :param file_url: 飞书文档链接 (wiki/docx/docs)
    :param save_path: 文档保存路径（如 ./docs/output.md）
    :param app_id: 飞书应用 ID (默认从 FEISHU_APP_ID 读取)
    :param app_secret: 飞书应用密钥 (默认从 FEISHU_APP_SECRET 读取)
    :param machine_id: 机器标识，用于缓存
    :return: { documentId, documentContent, images, attachments, whiteboards, summary }
    """
    if not file_url:
        raise ValueError('fileUrl 参数必填')
    if not save_path:
        raise ValueError('save_path 参数必填')

    app_id = app_id or os.environ.get('FEISHU_APP_ID', '')
    app_secret = app_secret or os.environ.get('FEISHU_APP_SECRET', '')
    if not app_id or not app_secret:
        raise ValueError('请配置 FEISHU_APP_ID 和 FEISHU_APP_SECRET')

    output_dir = str(Path(save_path).parent)
    user_key = machine_id or ''
    service = FeishuApiService(user_key, app_id, app_secret)

    if '/wiki/' in file_url:
        document_id = service.convert_wiki_to_document_id(file_url)
    else:
        document_id = process_document_id(file_url)

    document_content = service.get_document_content(document_id)
    blocks = service.get_document_blocks(document_id)

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    doc_base_name = _sanitize_filename(Path(save_path).stem)
    images, attachments, whiteboards = service.extract_and_save_resources(
        document_id, blocks, output_dir, doc_base_name
    )

    summary = {
        'totalBlocks': len(blocks),
        'imageCount': len(images),
        'attachmentCount': len(attachments),
        'whiteboardCount': len(whiteboards),
    }

    content = document_content or ''
    content = _wrap_code_blocks(content)
    content = _convert_tables_to_markdown(content)
    content = _enhance_markdown_format(content)
    image_rel_paths = [img.get('relPath', '') for img in images if img.get('relPath')]
    content = _replace_image_placeholders(content, image_rel_paths)

    save_document(content, save_path)

    return {
        'documentId': document_id,
        'documentContent': document_content,
        'images': images,
        'attachments': attachments,
        'whiteboards': whiteboards,
        'summary': summary,
    }


def _cli_main() -> None:
    args = sys.argv[1:]
    cmd = args[0] if args else None
    feishu_url = args[1] if len(args) > 1 else None
    save_path = args[2] if len(args) > 2 else None

    if not cmd:
        print('用法:')
        print('  python fetchFeishuDocHandler.py validate <feishu_url>')
        print('  python fetchFeishuDocHandler.py fetch <feishu_url> <save_path>')
        print('')
        print('环境变量: FEISHU_APP_ID, FEISHU_APP_SECRET')
        sys.exit(1)

    if cmd == 'validate':
        if not feishu_url:
            print('[ERROR] 请提供飞书链接', file=sys.stderr)
            sys.exit(1)
        r = validate_feishu_url(feishu_url)
        if r['valid']:
            print('[SUCCESS] 飞书链接格式正确')
            print('[INFO] 文档类型: ' + str(r.get('type', '')))
            sys.exit(0)
        print('[ERROR] ' + r['error'], file=sys.stderr)
        sys.exit(1)

    if cmd == 'fetch':
        if not feishu_url:
            print('[ERROR] 请提供飞书链接', file=sys.stderr)
            sys.exit(1)
        if not save_path:
            print('[ERROR] 请提供保存路径', file=sys.stderr)
            sys.exit(1)
        try:
            result = fetch_feishu_doc(feishu_url, save_path)
            print('[INFO] 文档 ID: ' + str(result['documentId']))
            s = result.get('summary', {})
            print('[INFO] 文档块数: ' + str(s.get('totalBlocks', 0)))
            print('[INFO] 图片数: ' + str(s.get('imageCount', 0)))
            print('[INFO] 画板数: ' + str(s.get('whiteboardCount', 0)))
            imgs = result.get('images') or []
            if imgs:
                print('\n[INFO] 文档包含以下图片:')
                for i, img in enumerate(imgs):
                    print('  %d. %s' % (i + 1, img.get('filePath', img.get('token', ''))))
            print('\n[SUCCESS] 飞书文档获取完成!')
            sys.exit(0)
        except Exception as e:
            print('[ERROR] ' + str(e), file=sys.stderr)
            if os.environ.get('DEBUG'):
                import traceback
                traceback.print_exc()
            sys.exit(1)

    print('[ERROR] 未知命令: ' + cmd, file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
    _cli_main()
