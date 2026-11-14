"""LLM error types, mapped to explicit HTTP responses.

The distinction matters for the caller:

- 503 : configuration problem, fix `.env`
- 502 : provider answered with an error
- 504 : provider did not answer in time
"""

from __future__ import annotations


class LLMError(Exception):
    status_code = 502
    name = "LLM Error"

    def __init__(self, message: str, *, upstream_status: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.upstream_status = upstream_status


class LLMNotConfigured(LLMError):
    status_code = 503
    name = "LLM Not Configured"


class LLMUpstreamError(LLMError):
    status_code = 502
    name = "LLM Upstream Error"


class LLMTimeout(LLMError):
    status_code = 504
    name = "LLM Timeout"
