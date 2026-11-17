"""附件上传：对应 C# 的 WorkHub/Services/FileService.cs。

浏览器把文件读成 base64 交给宿主，宿主落进附件根并回站内相对地址。
"""

from __future__ import annotations

import base64
import binascii

from app.common.exceptions import WorkHubError

__all__ = ["FileService", "MAX_BYTES"]

MAX_BYTES = 16 * 1024 * 1024


class FileService:
    def __init__(self, storage):
        self._storage = storage

    def upload(self, file_name: str, base64_text: str) -> str:
        if not (base64_text or "").strip():
            raise WorkHubError("没读到文件内容。")

        # 先按 base64 长度掐一道，避免 20MB 的字符串先解码再拒绝
        if len(base64_text) > MAX_BYTES // 3 * 4 + 4096:
            raise WorkHubError("文件超过 16MB，请压缩后再上传。")

        try:
            data = base64.b64decode(base64_text, validate=True)
        except (binascii.Error, ValueError):
            raise WorkHubError("文件内容不是有效的 base64，可能上传中断了。") from None

        if len(data) > MAX_BYTES:
            raise WorkHubError("文件超过 16MB，请压缩后再上传。")

        return self._storage.save(file_name, data)
