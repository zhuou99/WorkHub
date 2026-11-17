"""登录认证与失败锁定：对应 C# 的 WorkHub/Services/LocalAuthService.cs。

关键顺序（不能改）：
1. 空账号/空口令 → 直接拒，不动计数器、不写审计。
2. **锁定期检查在前**——锁定期内即使口令正确也不放行。
3. 口令校验。
4. 连续失败 5 次 → 计数归零并锁 15 分钟。
5. 成功 → 计数清零、刷新最近登录时间、签发会话。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.common.hasher import hash_password, verify_password
from app.common.permission_policy import OWNER_ROLE
from app.models.user import WhUser
from app.schemas.auth import AuthGuardState, UserInfo
from app.services.audit_service import AuditService
from app.services.config_service import ConfigStore, pick
from app.services.crud import LOCAL, now
from app.services.user_service import UserService

__all__ = ["AuthService", "GUARD_KEY", "MAX_FAILURES", "CREDENTIAL_KEY", "DEFAULT_PASSWORD"]

GUARD_KEY = "workhub.auth.guard"
CREDENTIAL_KEY = "workhub.credential"
MAX_FAILURES = 5
LOCK_MINUTES = 15
DEFAULT_PASSWORD = "admin123"
DEFAULT_USER_NAME = "admin"


class AuthService:
    def __init__(self, session: Session, config: ConfigStore, users: UserService, audit: AuditService):
        self._session = session
        self._config = config
        self._users = users
        self._audit = audit

    # ---------- 登录 ----------

    def login(self, user_name: str | None, password: str | None) -> UserInfo | None:
        """登录。成功返回 UserInfo，失败返回 None（原因由调用方写审计）。"""
        if not (user_name or "").strip() or not password:
            return None

        name = user_name.strip()
        guard = self.read_guard(name)

        # 锁定期内即使口令正确也不放行，避免暴力试错在本地工具上失守。
        if guard["LockedUntil"] is not None and guard["LockedUntil"] > now():
            until = guard["LockedUntil"]
            self._audit.write(
                "login",
                "login-locked",
                False,
                f"账号处于锁定期，解锁时间 {until:%Y-%m-%d %H:%M:%S}",
                name,
            )
            return None

        account = self._users.authenticate(name, password)
        if account is None:
            self.record_failure(name, guard)
            return None

        if guard["Failures"] > 0 or guard["LockedUntil"] is not None:
            guard["Failures"] = 0
            guard["LockedUntil"] = None
            self.save_guard(name, guard)

        moment = now()
        self._users.touch_login(account.Id, moment)

        user = UserInfo(
            Id=account.Id,
            UserName=account.UserName,
            Name=account.DisplayName if (account.DisplayName or "").strip() else account.UserName,
            Role=account.Role,
            AppId="WorkHub",
            Token=account.Id,
            Enabled=True,
            LastLoginTime=moment,
        )
        self._audit.write("login", "login-success", True, f"登录成功（角色 {user.Role}）", user.UserName)
        return user

    def logout(self, user_name: str | None) -> None:
        self._audit.write("login", "logout", True, "已退出登录", user_name)

    def record_failure(self, user_name: str, guard: dict | None = None) -> None:
        """记一次失败。达到上限就锁 15 分钟，并把计数归零。"""
        state = guard if guard is not None else self.read_guard(user_name)
        state["Failures"] += 1
        if state["Failures"] >= MAX_FAILURES:
            state["Failures"] = 0
            state["LockedUntil"] = now() + timedelta(minutes=LOCK_MINUTES)
            self.save_guard(user_name, state)
            self._audit.write(
                "login",
                "login-fail-locked",
                False,
                f"连续错误 {MAX_FAILURES} 次，已锁定到 {state['LockedUntil']:%Y-%m-%d %H:%M:%S}",
                user_name,
            )
            return
        self.save_guard(user_name, state)
        self._audit.write("login", "login-fail", False, f"口令错误，连续失败 {state['Failures']}/{MAX_FAILURES} 次", user_name)

    # ---------- 失败计数 ----------

    @staticmethod
    def guard_key_for(user_name: str) -> str:
        """按账号隔离的失败计数；多账号后一个人被锁不影响其他人。"""
        return f"{GUARD_KEY}.{(user_name or '').strip().lower()}"

    def read_guard(self, user_name: str) -> dict:
        """读失败计数。读不出来就当作没有失败，不能因此把人挡在门外。"""
        raw = self._config.get(self.guard_key_for(user_name))
        if not raw and (user_name or "").strip().lower() == DEFAULT_USER_NAME:
            raw = self._config.get(GUARD_KEY)  # 迁移前的全局计数给 admin 继续用
        state = {"Failures": 0, "LockedUntil": None}
        if not raw:
            return state
        import json

        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return state
        if not isinstance(data, dict):
            return state
        failures = pick(data, "Failures", "failures", default=0)
        locked = pick(data, "LockedUntil", "lockedUntil", default=None)
        try:
            state["Failures"] = int(failures or 0)
        except (TypeError, ValueError):
            state["Failures"] = 0
        if isinstance(locked, str) and locked:
            try:
                state["LockedUntil"] = datetime.fromisoformat(locked)
            except ValueError:
                state["LockedUntil"] = None
        return state

    def save_guard(self, user_name: str, guard: dict) -> None:
        """写失败计数。写失败只影响锁定能力，登录流程本身继续。

        除了按账号存的键，还顺手把同一份内容写到旧的全局键上——
        登录页的「还剩几次」是匿名接口，读不到具体账号，只能看这个镜像。
        （C# 那边只写按账号的键，全局键从不更新，登录页的计数因此一直是 5。）
        """
        try:
            locked = guard.get("LockedUntil")
            payload = {
                "Failures": int(guard.get("Failures") or 0),
                "LockedUntil": locked.isoformat(sep=" ", timespec="microseconds") if locked else None,
            }
            self._config.set_json(self.guard_key_for(user_name), payload)
            self._config.set_json(GUARD_KEY, payload)
        except Exception:
            pass

    # ---------- 登录页状态 ----------

    def guard_state(self) -> AuthGuardState:
        """登录保护状态。

        这是匿名接口，登录前还不知道是哪个账号，所以读全局键——
        那个键现在是每次失败时顺手写的镜像（C# 那边从不写，计数因此一直显示 5）。
        """
        state = AuthGuardState(RemainingTries=MAX_FAILURES)
        try:
            raw = self._config.get(GUARD_KEY)
            data = _loads(raw)
            if data is not None:
                state.Failures = int(pick(data, "Failures", "failures", default=0) or 0)
                state.RemainingTries = max(0, MAX_FAILURES - state.Failures)
                locked = pick(data, "LockedUntil", "lockedUntil", default=None)
                moment = _parse_dt(locked)
                if moment is not None and moment > now():
                    state.Locked = True
                    state.RemainingSeconds = int((moment - now()).total_seconds())
        except Exception:
            # 读不到保护状态时按「未锁定、未被限制」处理，不阻塞登录页。
            pass

        try:
            cred = _loads(self._config.get(CREDENTIAL_KEY))
            if cred is not None:
                state.DefaultPassword = verify_password(DEFAULT_PASSWORD, pick(cred, "PasswordHash", "passwordHash", default=""))
        except Exception:
            # 凭据读不出来就不提示改密，避免误报。
            pass
        return state

    # ---------- 种子 ----------

    def seed(self) -> None:
        """首次运行落一份默认口令，并把旧的单条凭据迁成 wh_user 的 Owner 账号。"""
        if not self._config.exists(CREDENTIAL_KEY):
            self._config.set_json(
                CREDENTIAL_KEY,
                {
                    "UserName": DEFAULT_USER_NAME,
                    "DisplayName": "主人",
                    "PasswordHash": hash_password(DEFAULT_PASSWORD),
                    "SetTime": now().isoformat(sep=" ", timespec="microseconds"),
                },
            )

        if self._users.all():
            return

        legacy = _loads(self._config.get(CREDENTIAL_KEY))
        legacy_name = pick(legacy or {}, "UserName", "userName", default="")
        legacy_display = pick(legacy or {}, "DisplayName", "displayName", default="")
        legacy_hash = pick(legacy or {}, "PasswordHash", "passwordHash", default="")
        legacy_set = _parse_dt(pick(legacy or {}, "SetTime", "setTime", default=None))

        user = WhUser(
            UserName=legacy_name if (legacy_name or "").strip() else DEFAULT_USER_NAME,
            DisplayName=legacy_display if (legacy_display or "").strip() else "主人",
            PasswordHash=legacy_hash if (legacy_hash or "").strip() else hash_password(DEFAULT_PASSWORD),
            Role=OWNER_ROLE,
            Enabled=True,
            SetTime=legacy_set or now(),
            CreateBy=LOCAL,
            CreateTime=now(),
        )
        self._session.add(user)
        self._session.commit()


def _loads(raw: str | None):
    if not raw:
        return None
    import json

    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def _parse_dt(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
