import logging

from flask import g, has_request_context, request

# ==========================================================================================
# ==========================================================================================

# File:    logging_ext.py
# Date:    August 26, 2025
# Author:  Jonathan A. Webb
# Purpose: Logging filter to inject a request context into the log records
# ==========================================================================================


class RequestContextFilter(logging.Filter):
    """Injects Flask request context into LogRecord fields:
    - request_id: short correlation id you set in @app.before_request
    - user_id: your auth user id (set in before_request when authenticated)
    - remote_addr: client IP (first hop from X-Forwarded-For if present)
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if has_request_context():
            # correlation id & user id are expected to be set in before_request
            record.request_id = getattr(g, "request_id", "-")
            record.user_id = getattr(g, "user_id", "-")

            # Extract client IP; XFF can be a comma-separated list
            xff = request.headers.get("X-Forwarded-For")
            if xff:
                record.remote_addr = xff.split(",")[0].strip()
            else:
                record.remote_addr = request.remote_addr or "-"
        else:
            record.request_id = "-"
            record.user_id = "-"
            record.remote_addr = "-"

        return True


# ==========================================================================================
# ==========================================================================================


# Optional: if you ever move to JSON logging, this helper is handy.
def current_request_context() -> dict:
    """Return a safe, minimal context dict for structured logging."""
    if not has_request_context():
        return {"request_id": "-", "user_id": "-", "remote_addr": "-"}
    xff = request.headers.get("X-Forwarded-For")
    ip = xff.split(",")[0].strip() if xff else (request.remote_addr or "-")
    return {
        "request_id": getattr(g, "request_id", "-"),
        "user_id": getattr(g, "user_id", "-"),
        "remote_addr": ip,
    }


# ==========================================================================================
# ==========================================================================================
# eof
