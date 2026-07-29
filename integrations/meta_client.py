"""Single chokepoint for all Meta Graph API calls.

Every Meta request in Mastery OS routes through this module. Sub-agents call
these methods; they never see the token, never build URLs, never see raw JSON.

Read methods are open. Write methods raise NotImplementedError until the
approval gate exists.
"""

import os
import time
from typing import Any

import requests

GRAPH_VERSION = "v21.0"
BASE_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"

# Runaway detector, not a cost control. Meta's own limit is 200/hour/user.
# A run that needs more than this has a bug upstream.
MAX_CALLS_PER_RUN = 50

REQUEST_TIMEOUT = 15


class MetaError(RuntimeError):
    """Meta returned an error. Carries Meta's own code and message."""

    def __init__(self, code: int, subcode: int | None, message: str, http_status: int):
        self.code = code
        self.subcode = subcode
        self.message = message
        self.http_status = http_status
        super().__init__(f"Meta error {code}"
                         f"{f'/{subcode}' if subcode else ''}: {message}")


class CallCapExceeded(RuntimeError):
    """Hard stop. Halts rather than degrading silently."""


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Load it with: . $env:USERPROFILE\\load-env.ps1"
        )
    return value


class MetaClient:
    def __init__(self) -> None:
        self._token = _require_env("META_TOKEN")
        self.page_id = _require_env("META_PAGE_ID")
        self.ig_user_id = _require_env("META_IG_USER_ID")
        self._call_count = 0
        self._call_log: list[dict[str, Any]] = []
        self._page_token: str | None = None

    # ---------- internals ----------

    def _request(self, path: str, params: dict[str, Any] | None = None) -> dict:
        if self._call_count >= MAX_CALLS_PER_RUN:
            raise CallCapExceeded(
                f"Hit {MAX_CALLS_PER_RUN} Meta calls in one run. Halting."
            )

        params = dict(params or {})
        params.setdefault("access_token", self._token)

        started = time.time()
        self._call_count += 1

        try:
            resp = requests.get(
                f"{BASE_URL}/{path}", params=params, timeout=REQUEST_TIMEOUT
            )
        except requests.RequestException as exc:
            self._log(path, None, time.time() - started, str(exc))
            raise MetaError(0, None, f"Network failure: {exc}", 0) from exc

        self._log(path, resp.status_code, time.time() - started, None)

        if not resp.ok:
            # Meta puts the useful part in the body, not the status line.
            try:
                err = resp.json().get("error", {})
            except ValueError:
                raise MetaError(0, None, resp.text[:300], resp.status_code)
            raise MetaError(
                code=err.get("code", 0),
                subcode=err.get("error_subcode"),
                message=err.get("message", "unknown"),
                http_status=resp.status_code,
            )

        return resp.json()

    def _log(self, path, status, elapsed, error) -> None:
        self._call_log.append({
            "path": path,
            "status": status,
            "seconds": round(elapsed, 3),
            "error": error,
        })

    @property
    def calls_used(self) -> int:
        return self._call_count

    @property
    def call_log(self) -> list[dict[str, Any]]:
        return list(self._call_log)

    # ---------- read ----------

    def get_ig_account(self) -> dict:
        """Profile snapshot. One call."""
        return self._request(
            self.ig_user_id,
            {"fields": "username,followers_count,follows_count,media_count"},
        )

    def get_ig_media(self, limit: int = 10) -> list[dict]:
        """Recent posts, trimmed. Sub-agents get fields, not raw payloads."""
        limit = min(limit, 25)
        data = self._request(
            f"{self.ig_user_id}/media",
            {
                "fields": "id,caption,media_type,permalink,timestamp,"
                          "like_count,comments_count",
                "limit": limit,
            },
        )
        return data.get("data", [])

    def get_media_insights(self, media_id: str) -> dict:
        """Per-post metrics. Metric names vary by media_type — see note below."""
        data = self._request(
            f"{media_id}/insights",
            {"metric": "reach,saved,shares,total_interactions"},
        )
        return {m["name"]: m["values"][0]["value"] for m in data.get("data", [])}

    def _get_page_token(self) -> str:
        """Page Insights requires a Page token, not a system-user token.
        Cached — costs one call the first time only."""
        if self._page_token:
            return self._page_token
        data = self._request("me/accounts", {"fields": "id,access_token"})
        for page in data.get("data", []):
            if page["id"] == self.page_id:
                self._page_token = page["access_token"]
                return self._page_token
        raise MetaError(0, None, f"Page {self.page_id} not in /me/accounts", 0)

    def get_page_insights(self, period: str = "day") -> dict:
        """Page metrics. Meta deprecated most of these in Nov 2025 and Jun 2026 —
        surviving set is narrow. Verify before adding metrics here."""
        params = {
            "metric": "page_views_total,page_post_engagements",
            "period": period,
            "access_token": self._get_page_token(),
        }
        # _request injects the system-user token; override it here.
        data = self._request(f"{self.page_id}/insights", params)
        return {m["name"]: m.get("values", []) for m in data.get("data", [])}

    # ---------- write: gated ----------

    def publish_ig_post(self, *args, **kwargs):
        raise NotImplementedError(
            "Publishing is public output and requires the approval gate. "
            "Not implemented until that exists."
        )

    def publish_page_post(self, *args, **kwargs):
        raise NotImplementedError("See publish_ig_post.")

    def reply_to_comment(self, *args, **kwargs):
        raise NotImplementedError("See publish_ig_post.")

    def delete_comment(self, *args, **kwargs):
        raise NotImplementedError(
            "Comment deletion is unrecoverable. Gate required, and prefer hide()."
        )