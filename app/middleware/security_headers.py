"""Security headers middleware.

Adds common security-related response headers (CSP, HSTS, X-Content-Type-Options, etc.).
Uses raw ASGI (no BaseHTTPMiddleware) for production-safe streaming and background tasks.
"""

from typing import Callable

DEFAULT_HEADERS = {
    "Content-Security-Policy": "default-src 'none'",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


def SecurityHeadersMiddleware(
    app: Callable, headers: dict[str, str] | None = None
) -> Callable:
    """Set security headers on all responses. Raw ASGI."""
    resolved = headers if headers is not None else DEFAULT_HEADERS.copy()
    header_list = [(k.encode(), v.encode()) for k, v in resolved.items()]

    async def asgi_app(scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await app(scope, receive, send)
            return

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                seen = {h[0].lower() for h in headers}
                for name_b, value_b in header_list:
                    if name_b.lower() not in seen:
                        headers.append((name_b, value_b))
                        seen.add(name_b.lower())
                message["headers"] = headers
            await send(message)

        await app(scope, receive, send_wrapper)

    return asgi_app
