from __future__ import annotations

import asyncio
import json
import mimetypes
import platform
import time
import uuid
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, BinaryIO, Callable, Iterable
from urllib.parse import quote

import httpx

from ..errors import KarotterAPIError, PaidPlanRequiredError, RateLimitError

PathLike = str | Path
FileInput = PathLike | BinaryIO


class Client:
    """
    Unofficial async Karotter API client inspired by twikit.
    """

    def __init__(
        self,
        locale: str = "ja-JP",
        base_url: str = "https://api.karotter.com",
        timeout: float = 15.0,
        *,
        client_type: str = "web",
        device_name: str | None = None,
        paid_plan: str = "free",
        entitlement_token: str | None = None,
        paid_headers: dict[str, str] | None = None,
        user_agent: str | None = None,
        browser_headers: dict[str, str] | None = None,
        auto_wait_on_rate_limit: bool = True,
        max_rate_limit_wait: float = 60.0,
        verify: bool = True,
    ) -> None:
        self.locale = locale
        self.base_url = self._normalize_base_url(base_url)
        self.timeout = timeout
        self.client_type = client_type
        self.device_id = str(uuid.uuid4())
        self.device_name = device_name or f"Web on {platform.system()}"

        self.access_token: str | None = None
        self.refresh_token: str | None = None
        self.csrf_token: str | None = None
        self.paid_plan = paid_plan
        self.entitlement_token = entitlement_token
        self.paid_headers = paid_headers or {}
        self.payment_retry_hook: Callable[[], Awaitable[bool]] | None = None
        self.user_agent = user_agent or self._default_user_agent()
        self.origin = "https://karotter.com"
        self.referer = f"{self.origin}/"
        self.browser_headers = browser_headers or {}
        self.auto_wait_on_rate_limit = auto_wait_on_rate_limit
        self.max_rate_limit_wait = max_rate_limit_wait

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            follow_redirects=True,
            verify=verify,
            headers=self._default_http_headers(),
        )

    async def __aenter__(self) -> "Client":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        url = base_url.rstrip("/")
        if not url.endswith("/api"):
            url = f"{url}/api"
        return url

    @staticmethod
    def _default_user_agent() -> str:
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        )

    def _default_http_headers(self) -> dict[str, str]:
        headers = {
            "Accept-Language": self.locale,
            "Accept": "application/json, text/plain, */*",
            "Origin": self.origin,
            "Referer": self.referer,
            "User-Agent": self.user_agent,
        }
        headers.update(self.browser_headers)
        return headers

    @staticmethod
    def _to_bool_str(value: bool) -> str:
        return "true" if value else "false"

    @staticmethod
    def _iso8601(value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _pick_error_message(payload: Any) -> tuple[str, str | None]:
        if isinstance(payload, dict):
            msg = payload.get("error") or payload.get("message") or "Request failed"
            code = payload.get("code")
            return str(msg), str(code) if code else None
        return "Request failed", None

    def _auth_headers(self) -> dict[str, str]:
        headers = {
            "x-client-type": self.client_type,
            "x-device-id": self.device_id,
        }
        if self.paid_plan and self.paid_plan.lower() != "free":
            headers["x-karotter-plan"] = self.paid_plan
        if self.entitlement_token:
            headers["x-karotter-entitlement"] = self.entitlement_token
        if self.paid_headers:
            headers.update(self.paid_headers)
        if self.csrf_token:
            headers["x-csrf-token"] = self.csrf_token
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    @staticmethod
    def _calculate_retry_seconds(response: httpx.Response) -> float | None:
        for key in ("retry-after", "ratelimit-reset", "x-ratelimit-reset"):
            raw_value = response.headers.get(key)
            if raw_value is None:
                continue
            try:
                value = float(raw_value)
            except ValueError:
                continue
            if key in {"ratelimit-reset", "x-ratelimit-reset"} and value > time.time() + 1:
                value = value - time.time()
            return max(value, 1.0)
        return None

    def set_browser_identity(
        self,
        *,
        user_agent: str | None = None,
        origin: str | None = None,
        referer: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        """
        Configure browser-like request headers for stable API interoperability.
        """
        if user_agent:
            self.user_agent = user_agent
        if origin:
            self.origin = origin.rstrip("/")
        if referer:
            self.referer = referer
        elif origin:
            self.referer = f"{self.origin}/"
        if extra_headers:
            self.browser_headers.update({str(k): str(v) for k, v in extra_headers.items()})
        self._client.headers.update(self._default_http_headers())

    def _cookie_header(self) -> str:
        return "; ".join(f"{name}={value}" for name, value in self._client.cookies.items())

    def build_realtime_headers(self) -> dict[str, str]:
        """
        Build headers suitable for Socket.IO realtime connection.
        """
        headers = {
            **self._default_http_headers(),
            **self._auth_headers(),
        }
        cookie_header = self._cookie_header()
        if cookie_header:
            headers["Cookie"] = cookie_header
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        retry_on_401: bool = True,
        retry_on_402: bool = True,
        **kwargs: Any,
    ) -> httpx.Response:
        headers = kwargs.pop("headers", {}) or {}
        merged_headers = {**self._auth_headers(), **headers}
        response = await self._client.request(method, path, headers=merged_headers, **kwargs)
        self._capture_csrf_token(response)

        if response.status_code == 401 and retry_on_401 and self.refresh_token:
            refreshed = await self.refresh_access_token(raise_on_error=False)
            if refreshed:
                merged_headers = {**self._auth_headers(), **headers}
                response = await self._client.request(method, path, headers=merged_headers, **kwargs)
                self._capture_csrf_token(response)

        if response.status_code == 402 and retry_on_402 and self.payment_retry_hook:
            recovered = await self.payment_retry_hook()
            if recovered:
                merged_headers = {**self._auth_headers(), **headers}
                response = await self._client.request(method, path, headers=merged_headers, **kwargs)
                self._capture_csrf_token(response)

        if response.status_code == 429 and self.auto_wait_on_rate_limit:
            retry_after = self._calculate_retry_seconds(response)
            if retry_after and retry_after <= self.max_rate_limit_wait:
                await asyncio.sleep(retry_after)
                merged_headers = {**self._auth_headers(), **headers}
                response = await self._client.request(method, path, headers=merged_headers, **kwargs)
                self._capture_csrf_token(response)

        if response.is_error:
            raise self._to_api_error(response)
        return response

    async def _request_json(self, method: str, path: str, **kwargs: Any) -> Any:
        response = await self._request(method, path, **kwargs)
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text

    def _capture_csrf_token(self, response: httpx.Response) -> None:
        try:
            payload = response.json()
        except ValueError:
            return
        if isinstance(payload, dict):
            token = payload.get("csrfToken")
            if isinstance(token, str) and token.strip():
                self.csrf_token = token.strip()

    def _to_api_error(self, response: httpx.Response) -> KarotterAPIError:
        payload: Any
        try:
            payload = response.json()
        except ValueError:
            payload = response.text
        message, code = self._pick_error_message(payload)
        error_cls: type[KarotterAPIError] = KarotterAPIError
        if response.status_code == 402:
            error_cls = PaidPlanRequiredError
        elif response.status_code == 429:
            error_cls = RateLimitError

        return error_cls(
            message,
            status_code=response.status_code,
            code=code,
            url=str(response.request.url),
            payload=payload,
        )

    def set_paid_plan(
        self,
        plan: str,
        *,
        entitlement_token: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        """
        Configure paid-plan headers so the client can keep working if Karotter
        introduces subscription-gated endpoints.
        """
        self.paid_plan = plan
        self.entitlement_token = entitlement_token
        self.paid_headers = extra_headers or {}

    def _set_tokens_from_payload(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        access_token = payload.get("accessToken")
        refresh_token = payload.get("refreshToken")
        if isinstance(access_token, str):
            self.access_token = access_token
        if isinstance(refresh_token, str):
            self.refresh_token = refresh_token

    def _build_multipart_fields(
        self,
        stack: ExitStack,
        *,
        fields: Iterable[tuple[str, str]],
        files: Iterable[tuple[str, FileInput]] | None = None,
    ) -> list[tuple[str, tuple[str | None, Any, str | None]]]:
        payload: list[tuple[str, tuple[str | None, Any, str | None]]] = []

        for key, value in fields:
            payload.append((key, (None, value, None)))

        if files:
            for field_name, file_input in files:
                if hasattr(file_input, "read"):
                    filename = getattr(file_input, "name", "upload.bin")
                    mime = mimetypes.guess_type(str(filename))[0] or "application/octet-stream"
                    payload.append((field_name, (Path(str(filename)).name, file_input, mime)))
                    continue

                path = Path(file_input)
                handle = stack.enter_context(path.open("rb"))
                mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                payload.append((field_name, (path.name, handle, mime)))

        return payload

    async def get_csrf_token(self, *, raise_on_error: bool = True) -> Any:
        try:
            return await self._request_json("GET", "/auth/csrf-token")
        except KarotterAPIError:
            if raise_on_error:
                raise
            return None

    async def refresh_access_token(self, *, raise_on_error: bool = True) -> bool:
        payload: dict[str, Any] = {
            "deviceId": self.device_id,
            "clientType": self.client_type,
            "deviceName": self.device_name,
        }
        if self.refresh_token:
            payload["refreshToken"] = self.refresh_token
        try:
            data = await self._request_json(
                "POST",
                "/auth/refresh-token",
                json=payload,
                retry_on_401=False,
            )
        except KarotterAPIError:
            if raise_on_error:
                raise
            return False
        self._set_tokens_from_payload(data)
        return True

    async def login(
        self,
        identifier: str | None = None,
        password: str | None = None,
        *,
        auth_info_1: str | None = None,
        auth_info_2: str | None = None,
        cookies_file: PathLike | None = None,
    ) -> Any:
        """
        twikit-style compatibility:
        - identifier: Karotter login ID
        - auth_info_1/auth_info_2: accepted for migration from twikit code
        """
        identifier = identifier or auth_info_2 or auth_info_1
        if not identifier or not password:
            raise ValueError("identifier and password are required.")

        await self.get_csrf_token(raise_on_error=False)
        data = await self._request_json(
            "POST",
            "/auth/login",
            json={
                "identifier": identifier,
                "password": password,
                "deviceId": self.device_id,
                "clientType": self.client_type,
                "deviceName": self.device_name,
            },
            retry_on_401=False,
        )
        self._set_tokens_from_payload(data)
        if cookies_file is not None:
            self.save_session(cookies_file)
        return data

    async def register(
        self,
        *,
        email: str,
        username: str,
        password: str,
        birthday: str | None = None,
        gender: str = "UNSPECIFIED",
        turnstile_token: str | None = None,
        accept_terms: bool = True,
        accept_privacy: bool = True,
    ) -> Any:
        await self.get_csrf_token(raise_on_error=False)
        data = await self._request_json(
            "POST",
            "/auth/register",
            json={
                "email": email,
                "username": username,
                "password": password,
                "birthday": birthday,
                "gender": gender,
                "acceptTerms": accept_terms,
                "acceptPrivacy": accept_privacy,
                "turnstileToken": turnstile_token,
            },
            retry_on_401=False,
        )
        self._set_tokens_from_payload(data)
        return data

    async def me(self) -> Any:
        return await self._request_json("GET", "/auth/me")

    async def logout(self) -> Any:
        try:
            data = await self._request_json(
                "POST",
                "/auth/logout",
                json={"deviceId": self.device_id},
                retry_on_401=False,
            )
        finally:
            self.access_token = None
            self.refresh_token = None
        return data

    async def switch_session(self, session_id: str, user_id: int | str) -> Any:
        data = await self._request_json(
            "POST",
            "/auth/switch-session",
            json={
                "sessionId": session_id,
                "userId": int(user_id),
                "deviceId": self.device_id,
                "clientType": self.client_type,
                "deviceName": self.device_name,
            },
        )
        self._set_tokens_from_payload(data)
        return data

    def export_session(self) -> dict[str, Any]:
        return {
            "base_url": self.base_url,
            "device_id": self.device_id,
            "client_type": self.client_type,
            "device_name": self.device_name,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "csrf_token": self.csrf_token,
            "paid_plan": self.paid_plan,
            "entitlement_token": self.entitlement_token,
            "paid_headers": self.paid_headers,
            "user_agent": self.user_agent,
            "origin": self.origin,
            "referer": self.referer,
            "browser_headers": self.browser_headers,
            "auto_wait_on_rate_limit": self.auto_wait_on_rate_limit,
            "max_rate_limit_wait": self.max_rate_limit_wait,
            "cookies": dict(self._client.cookies),
        }

    def import_session(self, session: dict[str, Any]) -> None:
        self.device_id = session.get("device_id", self.device_id)
        self.client_type = session.get("client_type", self.client_type)
        self.device_name = session.get("device_name", self.device_name)
        self.access_token = session.get("access_token")
        self.refresh_token = session.get("refresh_token")
        self.csrf_token = session.get("csrf_token")
        self.paid_plan = session.get("paid_plan", self.paid_plan)
        self.entitlement_token = session.get("entitlement_token", self.entitlement_token)
        self.user_agent = session.get("user_agent", self.user_agent)
        self.origin = session.get("origin", self.origin)
        self.referer = session.get("referer", self.referer)
        self.auto_wait_on_rate_limit = bool(session.get("auto_wait_on_rate_limit", self.auto_wait_on_rate_limit))
        self.max_rate_limit_wait = float(session.get("max_rate_limit_wait", self.max_rate_limit_wait))
        paid_headers = session.get("paid_headers")
        if isinstance(paid_headers, dict):
            self.paid_headers = {str(k): str(v) for k, v in paid_headers.items()}
        browser_headers = session.get("browser_headers")
        if isinstance(browser_headers, dict):
            self.browser_headers = {str(k): str(v) for k, v in browser_headers.items()}
        cookies = session.get("cookies")
        if isinstance(cookies, dict):
            self._client.cookies.update(cookies)
        self._client.headers.update(self._default_http_headers())

    def save_session(self, path: PathLike) -> None:
        Path(path).write_text(
            json.dumps(self.export_session(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_session(self, path: PathLike) -> None:
        self.import_session(json.loads(Path(path).read_text(encoding="utf-8")))

    def save_cookies(self, path: PathLike) -> None:
        self.save_session(path)

    def load_cookies(self, path: PathLike) -> None:
        self.load_session(path)

    async def get_timeline(self, *, page: int = 1, limit: int = 12, mode: str = "algorithm") -> Any:
        return await self._request_json(
            "GET",
            "/posts/timeline",
            params={"page": page, "limit": limit, "mode": mode},
        )

    async def get_recommended_posts(
        self,
        *,
        limit: int = 12,
        mode: str = "algorithm",
        page: int | None = None,
        cursor: str | None = None,
    ) -> Any:
        params: dict[str, Any] = {"limit": limit, "mode": mode}
        if cursor is not None:
            params["cursor"] = cursor
        elif page is not None:
            params["page"] = page
        return await self._request_json("GET", "/posts/recommended", params=params)

    async def get_post(self, post_id: int | str) -> Any:
        return await self._request_json("GET", f"/posts/{post_id}")

    async def get_post_replies(self, post_id: int | str, *, page: int = 1, limit: int = 20) -> Any:
        return await self._request_json(
            "GET",
            f"/posts/{post_id}/replies",
            params={"page": page, "limit": limit},
        )

    async def get_post_likes(self, post_id: int | str, *, page: int = 1, limit: int = 30) -> Any:
        return await self._request_json(
            "GET",
            f"/posts/{post_id}/likes",
            params={"page": page, "limit": limit},
        )

    async def get_post_quotes(self, post_id: int | str, *, page: int = 1, limit: int = 20) -> Any:
        return await self._request_json(
            "GET",
            f"/posts/{post_id}/quotes",
            params={"page": page, "limit": limit},
        )

    async def get_post_rekarots(self, post_id: int | str, *, page: int = 1, limit: int = 30) -> Any:
        return await self._request_json(
            "GET",
            f"/posts/{post_id}/rekarots",
            params={"page": page, "limit": limit},
        )

    async def get_post_conversation(self, post_id: int | str) -> Any:
        return await self._request_json("GET", f"/posts/{post_id}/conversation")

    async def leave_post_conversation(self, post_id: int | str) -> Any:
        return await self._request_json("POST", f"/posts/{post_id}/conversation/leave")

    async def get_post_analytics(self, post_id: int | str) -> Any:
        return await self._request_json("GET", f"/posts/{post_id}/analytics")

    async def delete_post(self, post_id: int | str) -> Any:
        return await self._request_json("DELETE", f"/posts/{post_id}")

    async def update_post(self, post_id: int | str, **fields: Any) -> Any:
        return await self._request_json("PUT", f"/posts/{post_id}", json=fields)

    async def create_post(
        self,
        *,
        content: str = "",
        media_files: list[FileInput] | None = None,
        parent_id: int | str | None = None,
        quoted_post_id: int | str | None = None,
        excluded_mentions: list[int] | None = None,
        poll_options: list[str] | None = None,
        poll_duration_hours: int = 24,
        visibility: str = "PUBLIC",
        viewer_circle_id: int | None = None,
        reply_restriction: str = "EVERYONE",
        reply_circle_id: int | None = None,
        scheduled_for: datetime | None = None,
        is_ai_generated: bool = False,
        is_promotional: bool = False,
        is_r18: bool = False,
        hide_from_minors: bool = False,
        media_alts: list[str] | None = None,
        media_spoiler_flags: list[bool] | None = None,
        media_r18_flags: list[bool] | None = None,
    ) -> Any:
        fields: list[tuple[str, str]] = []
        if content:
            fields.append(("content", content))
        if parent_id is not None:
            fields.append(("parentId", str(parent_id)))
        if excluded_mentions:
            fields.append(("excludedMentions", json.dumps(excluded_mentions)))
        if quoted_post_id is not None:
            fields.append(("quotedPostId", str(quoted_post_id)))
        if poll_options and len([x for x in poll_options if x.strip()]) >= 2:
            fields.append(("pollOptions", json.dumps([x.strip() for x in poll_options if x.strip()])))
            fields.append(("pollDurationHours", str(poll_duration_hours)))
        fields.extend(
            [
                ("isAiGenerated", self._to_bool_str(is_ai_generated)),
                ("isPromotional", self._to_bool_str(is_promotional)),
                ("isR18", self._to_bool_str(is_r18)),
                ("hideFromMinors", self._to_bool_str(hide_from_minors)),
                ("visibility", visibility),
                ("replyRestriction", reply_restriction),
            ]
        )
        if scheduled_for is not None:
            fields.append(("scheduledFor", self._iso8601(scheduled_for)))
        if visibility == "CIRCLE" and viewer_circle_id:
            fields.append(("viewerCircleId", str(viewer_circle_id)))
        if reply_restriction == "CIRCLE" and reply_circle_id:
            fields.append(("replyCircleId", str(reply_circle_id)))

        media_files = media_files or []
        for media_file in media_files:
            if isinstance(media_file, str) and media_file.strip():
                continue
            if isinstance(media_file, Path):
                continue
            if not hasattr(media_file, "read"):
                raise ValueError("media_files must contain file paths or binary file objects.")

        media_count = len(media_files)
        media_alts = (media_alts or [])[:media_count]
        media_spoiler_flags = (media_spoiler_flags or [])[:media_count]
        media_r18_flags = (media_r18_flags or [])[:media_count]
        if media_count:
            fields.append(("mediaAlts", json.dumps(media_alts + [""] * (media_count - len(media_alts)))))
            fields.append(
                ("mediaSpoilerFlags", json.dumps(media_spoiler_flags + [False] * (media_count - len(media_spoiler_flags))))
            )
            fields.append(("mediaR18Flags", json.dumps(media_r18_flags + [False] * (media_count - len(media_r18_flags)))))

        with ExitStack() as stack:
            multipart = self._build_multipart_fields(
                stack,
                fields=fields,
                files=[("media", file_obj) for file_obj in media_files],
            )
            return await self._request_json("POST", "/posts", files=multipart)

    async def create_tweet(
        self,
        text: str,
        *,
        media_ids: list[FileInput] | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        twikit-like alias.
        Note: Karotter does not expose a separate upload endpoint in the web app.
        `media_ids` is treated as list of file paths/file objects.
        """
        return await self.create_post(content=text, media_files=media_ids, **kwargs)

    async def create_karot(
        self,
        text: str,
        *,
        media_ids: list[FileInput] | None = None,
        **kwargs: Any,
    ) -> Any:
        return await self.create_post(content=text, media_files=media_ids, **kwargs)

    async def upload_media(self, media_path: PathLike) -> str:
        """
        twikit compatibility shim.
        Returns the path string for use as `media_ids` in create_tweet().
        """
        path = Path(media_path)
        if not path.exists():
            raise FileNotFoundError(path)
        return str(path)

    async def record_post_views(self, post_ids: list[int | str]) -> Any:
        if not post_ids:
            return {"recorded": 0}
        normalized_ids: list[int | str] = []
        for value in post_ids:
            try:
                normalized_ids.append(int(str(value)))
            except ValueError:
                normalized_ids.append(str(value))
        return await self._request_json("POST", "/posts/batch-views", json={"postIds": normalized_ids})

    async def get_my_bookmarks(
        self,
        *,
        page: int | None = 1,
        limit: int = 20,
        cursor: str | None = None,
    ) -> Any:
        params: dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        elif page is not None:
            params["page"] = page
        return await self._request_json("GET", "/posts/me/bookmarks", params=params)

    async def get_bookmarks(
        self,
        *,
        page: int | None = 1,
        limit: int = 20,
        cursor: str | None = None,
    ) -> Any:
        return await self.get_my_bookmarks(page=page, limit=limit, cursor=cursor)

    async def like_post(self, post_id: int | str) -> Any:
        return await self._request_json("POST", f"/posts/{post_id}/like")

    async def unlike_post(self, post_id: int | str) -> Any:
        return await self._request_json("DELETE", f"/posts/{post_id}/like")

    async def rekarot_post(self, post_id: int | str) -> Any:
        return await self._request_json("POST", f"/posts/{post_id}/rekarot")

    async def unrekarot_post(self, post_id: int | str) -> Any:
        return await self._request_json("DELETE", f"/posts/{post_id}/rekarot")

    async def bookmark_post(self, post_id: int | str) -> Any:
        return await self._request_json("POST", f"/posts/{post_id}/bookmark")

    async def unbookmark_post(self, post_id: int | str) -> Any:
        return await self._request_json("DELETE", f"/posts/{post_id}/bookmark")

    async def react_to_post(self, post_id: int | str, emoji: str) -> Any:
        return await self._request_json("POST", f"/posts/{post_id}/react", json={"emoji": emoji})

    async def unreact_post(self, post_id: int | str, emoji: str) -> Any:
        return await self._request_json("DELETE", f"/posts/{post_id}/react/{quote(emoji)}")

    async def vote_post_poll(self, post_id: int | str, option_id: int | str) -> Any:
        return await self._request_json("POST", f"/posts/{post_id}/poll/vote", json={"optionId": option_id})

    async def favorite_tweet(self, tweet_id: int | str) -> Any:
        return await self.like_post(tweet_id)

    async def unfavorite_tweet(self, tweet_id: int | str) -> Any:
        return await self.unlike_post(tweet_id)

    async def retweet(self, tweet_id: int | str) -> Any:
        return await self.rekarot_post(tweet_id)

    async def delete_retweet(self, tweet_id: int | str) -> Any:
        return await self.unrekarot_post(tweet_id)

    async def bookmark_tweet(self, tweet_id: int | str) -> Any:
        return await self.bookmark_post(tweet_id)

    async def delete_bookmark(self, tweet_id: int | str) -> Any:
        return await self.unbookmark_post(tweet_id)

    async def search_users(self, query: str, *, limit: int = 12, page: int = 1) -> Any:
        return await self._request_json(
            "GET",
            "/search/users",
            params={"q": query, "limit": limit, "page": page},
        )

    async def search_posts(
        self,
        query: str,
        *,
        sort: str = "latest",
        has_media: bool = False,
        limit: int = 12,
        page: int | None = None,
        cursor: str | None = None,
    ) -> Any:
        params: dict[str, Any] = {
            "q": query,
            "sort": sort,
            "limit": limit,
        }
        if has_media:
            params["hasMedia"] = True
        if cursor is not None:
            params["cursor"] = cursor
        elif page is not None:
            params["page"] = page
        return await self._request_json("GET", "/search/posts", params=params)

    async def search_hashtags(self, query: str, *, limit: int = 12, page: int = 1) -> Any:
        return await self._request_json(
            "GET",
            "/search/hashtags",
            params={"q": query, "limit": limit, "page": page},
        )

    async def search(self, query: str, tab: str = "all", *, limit: int = 12, page: int = 1) -> Any:
        tab = tab.lower()
        if tab == "all":
            return await self._request_json("GET", "/search", params={"q": query, "limit": limit, "page": page})
        if tab == "latest":
            return await self.search_posts(query, sort="latest", limit=limit, page=page)
        if tab == "topics":
            return await self.search_posts(query, sort="topics", limit=limit, page=page)
        if tab == "media":
            return await self.search_posts(query, sort="latest", has_media=True, limit=limit, page=page)
        if tab == "users":
            return await self.search_users(query, limit=limit, page=page)
        if tab == "hashtags":
            return await self.search_hashtags(query, limit=limit, page=page)
        raise ValueError(f"Unsupported tab: {tab}")

    async def search_tweet(self, query: str, product: str = "Latest", count: int = 20) -> list[dict[str, Any]]:
        product = product.lower()
        if product == "latest":
            data = await self.search_posts(query, sort="latest", limit=count, page=1)
        elif product in {"media", "photos"}:
            data = await self.search_posts(query, sort="latest", has_media=True, limit=count, page=1)
        else:
            data = await self.search_posts(query, sort="topics", limit=count, page=1)
        if isinstance(data, dict):
            posts = data.get("posts")
            if isinstance(posts, list):
                return posts
        return []

    async def search_karot(self, query: str, product: str = "Latest", count: int = 20) -> list[dict[str, Any]]:
        return await self.search_tweet(query, product, count)

    async def get_trends(self, category: str = "trending", *, limit: int = 20) -> Any:
        if category != "trending":
            raise ValueError("Karotter currently exposes only 'trending' topics endpoint.")
        return await self._request_json("GET", "/search/trending/topics", params={"limit": limit})

    async def get_user(self, user_identifier: str | int) -> Any:
        return await self._request_json("GET", f"/users/{user_identifier}")

    async def get_user_posts(
        self,
        user_id: int | str,
        kind: str = "posts",
        *,
        page: int = 1,
        limit: int = 20,
    ) -> Any:
        if kind not in {"posts", "replies", "likes", "media"}:
            raise ValueError("kind must be one of: posts, replies, likes, media")
        return await self._request_json(
            "GET",
            f"/users/{user_id}/{kind}",
            params={"page": page, "limit": limit},
        )

    async def get_followers(
        self,
        user_id: int | str,
        *,
        limit: int = 100,
        page: int | None = None,
        cursor: str | None = None,
    ) -> Any:
        params: dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        elif page is not None:
            params["page"] = page
        return await self._request_json("GET", f"/users/{user_id}/followers", params=params)

    async def get_following(
        self,
        user_id: int | str,
        *,
        limit: int = 100,
        page: int | None = None,
        cursor: str | None = None,
    ) -> Any:
        params: dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        elif page is not None:
            params["page"] = page
        return await self._request_json("GET", f"/users/{user_id}/following", params=params)

    async def get_user_tweets(
        self,
        user_id: int | str,
        tweet_type: str = "Tweets",
        *,
        page: int = 1,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        mapping = {
            "tweets": "posts",
            "posts": "posts",
            "replies": "replies",
            "likes": "likes",
            "media": "media",
        }
        kind = mapping.get(tweet_type.lower(), "posts")
        data = await self.get_user_posts(user_id, kind=kind, page=page, limit=limit)
        if isinstance(data, dict):
            posts = data.get("posts")
            if isinstance(posts, list):
                return posts
        return []

    async def get_user_karots(
        self,
        user_id: int | str,
        karot_type: str = "Karots",
        *,
        page: int = 1,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        mapping = {
            "karots": "Tweets",
            "karot": "Tweets",
            "replies": "Replies",
            "likes": "Likes",
            "media": "Media",
        }
        return await self.get_user_tweets(
            user_id,
            tweet_type=mapping.get(karot_type.lower(), "Tweets"),
            page=page,
            limit=limit,
        )

    async def follow_user(self, user_id: int | str) -> Any:
        return await self._request_json("POST", f"/follow/{user_id}")

    async def unfollow_user(self, user_id: int | str) -> Any:
        return await self._request_json("DELETE", f"/follow/{user_id}")

    async def follow(self, user_id: int | str) -> Any:
        return await self.follow_user(user_id)

    async def unfollow(self, user_id: int | str) -> Any:
        return await self.unfollow_user(user_id)

    async def remove_follower(self, user_id: int | str) -> Any:
        return await self._request_json("DELETE", f"/follow/follower/{user_id}")

    async def get_follow_requests(self) -> Any:
        return await self._request_json("GET", "/follow/requests/pending")

    async def accept_follow_request(self, request_id: int | str) -> Any:
        return await self._request_json("POST", f"/follow/requests/{request_id}/accept")

    async def reject_follow_request(self, request_id: int | str) -> Any:
        return await self._request_json("POST", f"/follow/requests/{request_id}/reject")

    async def block_user(self, user_id: int | str) -> Any:
        return await self._request_json("POST", f"/follow/block/{user_id}")

    async def unblock_user(self, user_id: int | str) -> Any:
        return await self._request_json("DELETE", f"/follow/block/{user_id}")

    async def get_blocked_users(self) -> Any:
        return await self._request_json("GET", "/follow/block")

    async def mute_user(self, user_id: int | str) -> Any:
        return await self._request_json("POST", f"/follow/mute/{user_id}")

    async def unmute_user(self, user_id: int | str) -> Any:
        return await self._request_json("DELETE", f"/follow/mute/{user_id}")

    async def get_muted_users(self) -> Any:
        return await self._request_json("GET", "/follow/mute")

    async def get_notifications(self, *, page: int = 1, limit: int = 15) -> Any:
        return await self._request_json(
            "GET",
            "/notifications",
            params={"page": page, "limit": limit},
        )

    async def get_unread_notification_count(self) -> Any:
        return await self._request_json("GET", "/notifications/unread/count")

    async def get_grouped_post_notifications(self, *, limit: int = 15) -> Any:
        return await self._request_json(
            "GET",
            "/notifications/grouped-posts",
            params={"limit": limit},
        )

    async def mark_notifications_read_all(self) -> Any:
        return await self._request_json("PATCH", "/notifications/read-all")

    async def delete_notification(self, notification_id: int | str) -> Any:
        return await self._request_json("DELETE", f"/notifications/{notification_id}")

    async def register_push_token(self, token: str, *, device_id: str | None = None) -> Any:
        return await self._request_json(
            "POST",
            "/notifications/push/register",
            json={"token": token, "deviceId": device_id or self.device_id},
        )

    async def unregister_push_token(self, token: str) -> Any:
        return await self._request_json(
            "POST",
            "/notifications/push/unregister",
            json={"token": token},
        )

    async def get_dm_groups(self, *, page: int = 1, limit: int = 30) -> Any:
        return await self._request_json("GET", "/dm/groups", params={"page": page, "limit": limit})

    async def create_dm_group(
        self,
        user_ids: list[int | str],
        *,
        name: str | None = None,
        is_group: bool = True,
    ) -> Any:
        return await self._request_json(
            "POST",
            "/dm/groups",
            json={
                "userIds": [int(x) for x in user_ids],
                "name": name,
                "isGroup": is_group,
            },
        )

    async def start_dm(self, target_user_id: int | str) -> Any:
        return await self._request_json("POST", "/dm/start", json={"targetUserId": int(target_user_id)})

    async def get_dm_messages(self, group_id: int | str, *, page: int = 1, limit: int = 30) -> Any:
        return await self._request_json(
            "GET",
            f"/dm/groups/{group_id}/messages",
            params={"page": page, "limit": limit},
        )

    async def send_dm_message(
        self,
        group_id: int | str,
        content: str,
        *,
        attachments: list[FileInput] | None = None,
        attachment_alts: list[str] | None = None,
        attachment_spoiler_flags: list[bool] | None = None,
        attachment_r18_flags: list[bool] | None = None,
        reply_to_id: int | str | None = None,
        poll_options: list[str] | None = None,
        poll_duration_hours: int | None = None,
    ) -> Any:
        fields: list[tuple[str, str]] = [("content", content)]
        if reply_to_id is not None:
            fields.append(("replyToId", str(reply_to_id)))
        if poll_options and len([x for x in poll_options if x.strip()]) >= 2:
            fields.append(("pollOptions", json.dumps([x.strip() for x in poll_options if x.strip()])))
            if poll_duration_hours is not None:
                fields.append(("pollDurationHours", str(poll_duration_hours)))
        attachments = attachments or []
        if attachment_alts:
            fields.append(("attachmentAlts", json.dumps(attachment_alts)))
        if attachment_spoiler_flags:
            fields.append(("attachmentSpoilerFlags", json.dumps(attachment_spoiler_flags)))
        if attachment_r18_flags:
            fields.append(("attachmentR18Flags", json.dumps(attachment_r18_flags)))

        file_parts = [("attachments", f) for f in attachments]
        with ExitStack() as stack:
            multipart = self._build_multipart_fields(stack, fields=fields, files=file_parts)
            return await self._request_json("POST", f"/dm/groups/{group_id}/messages", files=multipart)

    async def send_dm(self, user_id: int | str, text: str) -> Any:
        start_data = await self.start_dm(user_id)
        group_id: Any = None
        if isinstance(start_data, dict):
            group = start_data.get("group")
            if isinstance(group, dict):
                group_id = group.get("id")
        if group_id is None:
            raise KarotterAPIError("Could not resolve DM group id from /dm/start response.")
        return await self.send_dm_message(group_id, text)
