"""LLM layer.

Three concerns are deliberately separated:

- `catalog.py`    : which models exist, what they cost, what they support
- `client.py`     : the interface every provider implements
- `opencode_go.py`: the real HTTP client (OpenAI-compatible)
- `mock.py`       : deterministic client for tests and offline development
- `factory.py`    : picks a client from the settings
- `telemetry.py`  : persists one row per call (tokens, cost, latency, error)

Business code never imports httpx directly: it asks the factory for a client
and calls `complete()`.
"""

from .client import LLMClient, LLMMessage, LLMResult
from .errors import LLMError, LLMNotConfigured, LLMTimeout, LLMUpstreamError
from .factory import get_llm_client

__all__ = [
    "LLMClient",
    "LLMMessage",
    "LLMResult",
    "LLMError",
    "LLMNotConfigured",
    "LLMTimeout",
    "LLMUpstreamError",
    "get_llm_client",
]
