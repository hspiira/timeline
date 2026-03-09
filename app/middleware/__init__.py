"""HTTP middleware: timeout, request size limit, request ID, correlation ID, security headers.

Applied in main app; order matters (first added = outermost).
Import and use from app.main.
Audit logging is performed by the ensure_audit_logged dependency on write endpoints (same transaction).
"""

from app.middleware.correlation_id import CorrelationIDMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.request_size_limit import RequestSizeLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.tenant_context import TenantContextMiddleware
from app.middleware.timeout import TimeoutMiddleware

__all__ = [
    "CorrelationIDMiddleware",
    "RequestIDMiddleware",
    "RequestSizeLimitMiddleware",
    "SecurityHeadersMiddleware",
    "TenantContextMiddleware",
    "TimeoutMiddleware",
]
