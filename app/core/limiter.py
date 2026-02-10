"""Rate limiter instance for SlowAPI.

Shared so both main (app.state.limiter) and route modules (e.g. auth) can use
the same instance without circular imports.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
