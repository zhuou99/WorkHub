"""SQLAlchemy 模型汇总。create_all 需要所有表都已注册到 metadata。"""

from app.db import Base
from app.models.base import EntityBaseMixin
from app.models.content import WhArticle, WhBookmark, WhNote, WhPublishLog, WhSnippet
from app.models.crm import WhClient, WhCommLog, WhMilestone, WhProject, WhTask
from app.models.finance import WhExpense, WhInvoice, WhPayment, WhPaymentPlan
from app.models.glossary import WhGlossary
from app.models.repo import WhReleasePlan, WhRepo, WhRepoSnapshot
from app.models.rss import WhRssFeed, WhRssItem
from app.models.sysconfig import SysConfig
from app.models.system import WhAuditLog, WhError, WhToolPref
from app.models.types import BoolAsInteger, DecimalAsFloat, TextDateTime
from app.models.user import WhUser

__all__ = [
    "Base",
    "EntityBaseMixin",
    "DecimalAsFloat",
    "BoolAsInteger",
    "TextDateTime",
    "SysConfig",
    "WhUser",
    "WhClient",
    "WhCommLog",
    "WhProject",
    "WhTask",
    "WhMilestone",
    "WhInvoice",
    "WhPayment",
    "WhExpense",
    "WhPaymentPlan",
    "WhAuditLog",
    "WhError",
    "WhToolPref",
    "WhNote",
    "WhArticle",
    "WhBookmark",
    "WhSnippet",
    "WhPublishLog",
    "WhRssFeed",
    "WhRssItem",
    "WhRepo",
    "WhRepoSnapshot",
    "WhReleasePlan",
    "WhGlossary",
]
