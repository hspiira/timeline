"""Rate limiter instance for SlowAPI.

Shared so both main (app.state.limiter) and route modules (e.g. auth) can use
the same instance without circular imports. Central limit strings and decorators
keep rate limits DRY.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Single source of truth for rate limit strings and decorators.
LOGIN_LIMIT = "10/minute"
CREATE_TENANT_LIMIT = "5/minute"
WRITE_ENDPOINT_LIMIT = "120/minute"

limit_auth = limiter.limit(LOGIN_LIMIT)
limit_create_tenant = limiter.limit(CREATE_TENANT_LIMIT)
limit_writes = limiter.limit(WRITE_ENDPOINT_LIMIT)
