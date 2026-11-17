"""翻译与术语表：对应 C# 的 WorkHub/Services/TranslateService.cs。

百度通用翻译 API：签名 = md5(appid + q + salt + secret)。
密钥走 SecretProtector 加密，没配就明确降级。
"""

from __future__ import annotations

import hashlib
import json
import secrets as _secrets
from urllib.parse import quote

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import WorkHubError
from app.common.secrets import get_secret
from app.models.glossary import WhGlossary
from app.schemas.translate import GlossaryIn, TranslateOutcome
from app.services.crud import LOCAL, now

__all__ = ["TranslateService"]

_ENDPOINT = "https://fanyi-api.baidu.com/api/trans/vip/translate"
_MAX_BYTES = 6000

_ERROR_HINTS = {
    "54003": "AppID 不正确或未授权",
    "54004": "账户额度不足，去百度翻译开放平台充值或换个自然月再看",
    "54005": "百度翻译服务器繁忙，稍后再试",
    "54009": "访问过于频繁，稍等几秒",
    "54010": "签名错误：AppID 与密钥不配对",
    "58001": "翻译语言不支持，检查语言码",
    "58002": "请求参数缺失或格式不对",
    "52003": "百度翻译系统内部错误",
    "52004": "百度翻译接口调用异常（多为文本含非法字符）",
}


class TranslateService:
    def __init__(self, session: Session, config, protector):
        self._db = session
        self._config = config
        self._protector = protector
        self._http = httpx.Client(timeout=15.0)

    def is_ready(self) -> bool:
        return bool(get_secret(self._config, self._protector, "baidu.appid")) and bool(
            get_secret(self._config, self._protector, "baidu.secret")
        )

    def translate(self, text: str, from_: str, to: str, force_glossary: bool) -> tuple[str, TranslateOutcome]:
        input_text = (text or "").strip()
        if not input_text:
            raise WorkHubError("请输入待翻译内容。")
        if not to:
            to = "en"

        glossary = self.glossary()
        exact = next((item for item in glossary if item.Lang == to and item.Term.lower() == input_text.lower()), None)
        if exact is not None:
            return "术语表命中", TranslateOutcome(Text=exact.Translation, From=from_, To=to, ExactHit=True)

        appid = get_secret(self._config, self._protector, "baidu.appid")
        secret = get_secret(self._config, self._protector, "baidu.secret")
        if not appid or not secret:
            raise WorkHubError("未配置百度翻译密钥（或密文解不开）：到「设置 · 外部服务密钥」录入 AppID 与密钥即可，术语表仍可离线查。")

        outcome = TranslateOutcome(To=to, From=from_)

        # 送译前把领域词换成约定译法
        if force_glossary:
            for item in glossary:
                if item.Lang == to and (item.Translation or "").strip():
                    if item.Term.lower() in input_text.lower():
                        input_text = _ireplace(input_text, item.Term, item.Translation)
                        outcome.Forced.append(item.Term)

        byte_count = len(input_text.encode("utf-8"))
        if byte_count > _MAX_BYTES:
            raise WorkHubError(f"单次最多 {_MAX_BYTES} 字节（约 {_MAX_BYTES // 3} 个汉字），当前 {byte_count} 字节，请分段。")

        salt = str(_secrets.randbelow(900000) + 100000)
        sign = hashlib.md5((appid + input_text + salt + secret).encode("utf-8")).hexdigest()
        query = "&".join(
            f"{key}={quote(value, safe='')}"
            for key, value in (("q", input_text), ("from", from_), ("appid", appid), ("salt", salt), ("to", to), ("sign", sign))
        )

        try:
            resp = self._http.get(f"{_ENDPOINT}?{query}")
            body = resp.text
        except httpx.TimeoutException:
            raise WorkHubError("百度翻译请求超时（15 秒）：检查网络或稍后再试。") from None
        except httpx.HTTPError as exc:
            raise WorkHubError(f"连不上百度翻译接口：{exc}") from exc

        if resp.status_code >= 400:
            raise WorkHubError(f"百度翻译 HTTP {resp.status_code}：{_truncate(body)}")
        try:
            root = json.loads(body or "{}")
        except json.JSONDecodeError:
            raise WorkHubError("百度翻译返回的不是 JSON，可能被网关拦了。") from None

        if "error_code" in root:
            code = str(root["error_code"])
            hint = _ERROR_HINTS.get(code, "调用失败")
            msg = root.get("error_msg", "")
            raise WorkHubError(f"百度翻译 {code} · {hint}" + (f"（{msg}）" if msg else ""))

        arr = root.get("trans_result")
        if arr is None:
            raise WorkHubError(f"百度翻译返回内容不认识：{_truncate(json.dumps(root, ensure_ascii=False))}")

        lines = [item.get("dst", "") for item in arr]
        outcome.Text = "\n".join(lines)
        outcome.From = root.get("from", from_)
        return "翻译完成", outcome

    def glossary(self) -> list[WhGlossary]:
        rows = list(self._db.execute(select(WhGlossary)).scalars().all())
        return sorted(rows, key=lambda item: (item.Lang or "", item.Term or ""))

    def save_glossary(self, item: GlossaryIn) -> str:
        if item is None or not (item.Term or "").strip() or not (item.Translation or "").strip():
            raise WorkHubError("源词与约定译法都要填。")
        term = item.Term.strip()
        translation = item.Translation.strip()
        lang = item.Lang if (item.Lang or "").strip() else "en"

        dup = next((item2 for item2 in self.glossary() if item2.Term == term and item2.Lang == lang), None)
        if dup is not None and dup.Id != item.Id:
            raise WorkHubError(f"{lang}里「{term}」已经有一条了，改那条就行。")

        old = self._db.get(WhGlossary, item.Id) if item.Id else None
        if old is None:
            old = WhGlossary(Term=term, Translation=translation, Lang=lang, Note=item.Note,
                             CreateBy=LOCAL, CreateTime=now())
            self._db.add(old)
        else:
            old.Term = term
            old.Translation = translation
            old.Lang = lang
            old.Note = item.Note
            old.ModifyBy = LOCAL
            old.ModifyTime = now()
        self._db.add(old)
        self._db.commit()
        return "术语已保存"

    def delete_glossary(self, glossary_id: str) -> None:
        item = self._db.get(WhGlossary, glossary_id)
        if item is not None:
            self._db.delete(item)
            self._db.commit()


def _ireplace(text: str, old: str, new: str) -> str:
    """大小写不敏感的替换。"""
    import re

    return re.sub(re.escape(old), lambda _: new, text, flags=re.IGNORECASE)


def _truncate(text: str) -> str:
    if not text:
        return ""
    return text if len(text) <= 200 else text[:200] + "…"
