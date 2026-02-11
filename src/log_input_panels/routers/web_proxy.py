import re
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Query
from fastapi.responses import Response

router = APIRouter(tags=["proxy"])

STRIP_HEADERS = frozenset({
    "x-frame-options",
    "content-security-policy",
    "content-security-policy-report-only",
    "content-encoding",
    "transfer-encoding",
    "content-length",
})


@router.get("/proxy")
async def proxy_website(url: str = Query(..., description="Target URL to proxy")):
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        resp = await client.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )

    content_type = resp.headers.get("content-type", "")
    body = resp.content

    # For HTML responses, inject a <base> tag so relative URLs resolve correctly
    if "text/html" in content_type:
        text = resp.text
        parsed = urlparse(str(resp.url))  # use final URL after redirects
        base_href = f"{parsed.scheme}://{parsed.netloc}/"
        base_tag = f'<base href="{base_href}">'

        # Only inject if there's no existing <base> tag
        if not re.search(r"<base\s", text, re.IGNORECASE):
            head_match = re.search(r"<head[^>]*>", text, re.IGNORECASE)
            if head_match:
                idx = head_match.end()
                text = text[:idx] + base_tag + text[idx:]
            else:
                html_match = re.search(r"<html[^>]*>", text, re.IGNORECASE)
                if html_match:
                    idx = html_match.end()
                    text = text[:idx] + "<head>" + base_tag + "</head>" + text[idx:]

        body = text.encode("utf-8", errors="replace")

    # Forward response headers, stripping iframe-blocking ones
    headers = {}
    for key, value in resp.headers.items():
        if key.lower() not in STRIP_HEADERS:
            headers[key] = value

    media = content_type.split(";")[0].strip() if content_type else None
    return Response(
        content=body,
        status_code=resp.status_code,
        headers=headers,
        media_type=media,
    )
