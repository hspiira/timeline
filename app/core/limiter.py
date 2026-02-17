"""Rate limiter instance for SlowAPI.

Shared so both main (app.state.limiter) and route modules (e.g. auth) can use
the same instance without circular imports. Central limit strings and decorators
keep rate limits DRY.
"""

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Single source of truth for rate limit strings and decorators.
LOGIN_LIMIT = "10/minute"
CREATE_TENANT_LIMIT = "5/minute"
WRITE_ENDPOINT_LIMIT = "120/minute"
UPLOAD_LIMIT = "30/minute"
AUTH_PER_TENANT_CODE_LIMIT = 20  # attempts per minute per tenant_code
AUTH_PER_TENANT_CODE_WINDOW_SEC = 60

limit_auth = limiter.limit(LOGIN_LIMIT)
limit_create_tenant = limiter.limit(CREATE_TENANT_LIMIT)
limit_writes = limiter.limit(WRITE_ENDPOINT_LIMIT)
limit_upload = limiter.limit(UPLOAD_LIMIT)

# In-memory sliding window for per-tenant_code auth rate limit (login/register).
_auth_per_tenant: defaultdict[str, list[float]] = defaultdict(list)
_auth_per_tenant_lock = Lock()


def check_auth_rate_per_tenant_code(tenant_code: str) -> None:
    """Raise 429 if too many auth attempts for this tenant_code in the last minute."""
    if not tenant_code:
        return
    now = time.monotonic()
    cutoff = now - AUTH_PER_TENANT_CODE_WINDOW_SEC
    key = tenant_code.strip().lower()
    with _auth_per_tenant_lock:
        _auth_per_tenant[key] = [t for t in _auth_per_tenant[key] if t > cutoff]
        if len(_auth_per_tenant[key]) >= AUTH_PER_TENANT_CODE_LIMIT:
            raise HTTPException(
                status_code=429,
                detail="Too many attempts for this tenant; try again later",
            )
        _auth_per_tenant[key].append(now)
