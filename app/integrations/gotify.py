"""Push to Gotify (application token)."""

from __future__ import annotations

import httpx

from app.core.config import Settings


def send_gotify_message(
    settings: Settings,
    *,
    title: str,
    message: str,
    priority: int = 5,
) -> None:
    token = (settings.gotify_token or "").strip()
    if not token:
        raise RuntimeError("MYHELPER_GOTIFY_TOKEN is not set.")

    url = settings.gotify_url.rstrip("/") + "/message"
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            url,
            params={"token": token},
            data={
                "title": title,
                "message": message,
                "priority": str(priority),
            },
        )
    if resp.status_code < 200 or resp.status_code >= 300:
        raise RuntimeError(
            f"Gotify push failed: HTTP {resp.status_code} - {resp.text[:500]}"
        )
