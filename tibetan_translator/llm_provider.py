import os
import time
import threading
from typing import Any, Dict, List, Optional, Tuple, Type

# Try provider-specific imports lazily and safely
try:
    from langchain_anthropic import ChatAnthropic  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    ChatAnthropic = None  # type: ignore

try:
    from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    ChatGoogleGenerativeAI = None  # type: ignore


class TokenBucket:
    """Simple thread-safe token bucket for rate limiting by (approx) tokens/minute."""

    def __init__(self, capacity_tokens: int, refill_tokens_per_minute: int) -> None:
        self.capacity = max(1, capacity_tokens)
        self.refill_rate_per_sec = max(1, refill_tokens_per_minute) / 60.0
        self._tokens = float(self.capacity)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        if elapsed <= 0:
            return
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate_per_sec)
        self._last_refill = now

    def consume(self, tokens: int) -> None:
        """Block until the requested tokens are available, then consume them."""
        need = max(1, tokens)
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= need:
                    self._tokens -= need
                    return
                # time until enough tokens accrue
                shortfall = need - self._tokens
                wait_seconds = shortfall / self.refill_rate_per_sec if self.refill_rate_per_sec > 0 else 1.0
            time.sleep(min(max(wait_seconds, 0.05), 2.0))


def approximate_token_count(messages_or_text: Any) -> int:
    """Very rough token estimate (~4 chars/token)."""
    try:
        if isinstance(messages_or_text, str):
            return max(1, len(messages_or_text) // 4)
        if isinstance(messages_or_text, list):
            total = 0
            for m in messages_or_text:
                if isinstance(m, str):
                    total += len(m)
                elif isinstance(m, dict):
                    # typical {'type': 'ai'|'human'|'system', 'content': '...'}
                    total += len(str(m.get('content', '')))
                else:
                    # LangChain BaseMessage has .content
                    content = getattr(m, 'content', '')
                    total += len(str(content))
            return max(1, total // 4)
        # Fallback
        return max(1, len(str(messages_or_text)) // 4)
    except Exception:
        return 100


class _StructuredWrapper:
    """Wrapper that mimics `.with_structured_output(schema).invoke(...)` with fallback across providers."""

    def __init__(self, parent: 'MultiProviderLLM', schema: Any) -> None:
        self._parent = parent
        self._schema = schema

    def invoke(self, input_data: Any) -> Any:  # noqa: D401
        return self._parent._invoke_with_fallback(input_data, structured_schema=self._schema)


class MultiProviderLLM:
    """Unified LLM client with provider fallback and token-bucket rate limiting.

    Supported providers (by name):
      - 'anthropic' (requires ANTHROPIC_API_KEY)
      - 'google' (Gemini, requires GOOGLE_API_KEY)
    """

    def __init__(
        self,
        provider_order: Optional[List[str]] = None,
        model_names: Optional[Dict[str, str]] = None,
        max_tokens: int = 4000,
        token_buckets_per_minute: Optional[Dict[str, int]] = None,
        temperature: float = 0.0,
        thinking_enabled: bool = False,
        thinking_budget_tokens: int = 0,
    ) -> None:
        self.provider_order = [p.strip().lower() for p in (provider_order or os.getenv('LLM_PROVIDER_ORDER', 'anthropic,google').split(',')) if p.strip()]
        self.model_names = model_names or {
            'anthropic': os.getenv('ANTHROPIC_MODEL_NAME', os.getenv('LLM_MODEL_NAME', 'claude-3-7-sonnet-latest')),
            'google': os.getenv('GOOGLE_MODEL_NAME', 'gemini-1.5-pro'),
        }
        self.max_tokens = int(os.getenv('MAX_TOKENS', str(max_tokens)))
        self.temperature = float(os.getenv('LLM_TEMPERATURE', str(temperature)))
        self.thinking_enabled = thinking_enabled
        self.thinking_budget_tokens = int(os.getenv('THINKING_BUDGET_TOKENS', str(thinking_budget_tokens or 2000)))

        # Setup token buckets (per provider)
        default_buckets = {
            'anthropic': int(os.getenv('TPM_ANTHROPIC', '50000')),
            'google': int(os.getenv('TPM_GOOGLE', '60000')),
        }
        self.bucket_limits = token_buckets_per_minute or default_buckets
        self._buckets: Dict[str, TokenBucket] = {}

    def _get_bucket(self, provider: str) -> TokenBucket:
        if provider not in self._buckets:
            limit = max(1000, int(self.bucket_limits.get(provider, 50000)))
            self._buckets[provider] = TokenBucket(capacity_tokens=limit, refill_tokens_per_minute=limit)
        return self._buckets[provider]

    def _build_client(self, provider: str, structured_schema: Any = None):
        p = provider.lower()
        if p == 'anthropic':
            if ChatAnthropic is None:
                raise RuntimeError("langchain-anthropic is not installed. Install it to use Anthropic provider.")
            kwargs: Dict[str, Any] = {
                'model': self.model_names.get('anthropic', 'claude-3-7-sonnet-latest'),
                'max_tokens': self.max_tokens,
                'temperature': self.temperature,
            }
            if self.thinking_enabled:
                # Only Anthropic supports 'thinking' kwarg; ignore for others
                kwargs['thinking'] = {"type": "enabled", "budget_tokens": self.thinking_budget_tokens}
            client = ChatAnthropic(**kwargs)
            return client.with_structured_output(structured_schema) if structured_schema is not None else client

        if p == 'google':
            if ChatGoogleGenerativeAI is None:
                raise RuntimeError("langchain-google-genai is not installed. Install it to use Gemini provider.")
            model_name = self.model_names.get('google', 'gemini-1.5-pro')
            client = ChatGoogleGenerativeAI(
                model=model_name,
                max_output_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            # ChatGoogleGenerativeAI supports structured output in LangChain
            return client.with_structured_output(structured_schema) if structured_schema is not None else client

        raise ValueError(f"Unsupported provider: {provider}")

    def _invoke_with_fallback(self, input_data: Any, structured_schema: Any = None) -> Any:
        last_err: Optional[Exception] = None
        # Rough input token estimate
        est_in_tokens = approximate_token_count(input_data)
        est_out_tokens = self.max_tokens // 2
        est_total = est_in_tokens + est_out_tokens

        for provider in self.provider_order:
            key_required = {
                'anthropic': 'ANTHROPIC_API_KEY',
                'google': 'GOOGLE_API_KEY',
            }.get(provider)

            if key_required and not os.getenv(key_required):
                last_err = RuntimeError(f"Skipping provider '{provider}': missing {key_required}")
                continue

            try:
                # Rate limit per provider
                self._get_bucket(provider).consume(est_total)
                client = self._build_client(provider, structured_schema=structured_schema)
                return client.invoke(input_data)
            except Exception as e:  # noqa: BLE001 - capture provider errors to fall back
                last_err = e
                continue

        # Exhausted all providers
        if last_err:
            raise last_err
        raise RuntimeError("No providers available for invocation.")

    # Public API matching LangChain's chat models
    def invoke(self, input_data: Any) -> Any:
        return self._invoke_with_fallback(input_data)

    def with_structured_output(self, schema: Any) -> _StructuredWrapper:
        return _StructuredWrapper(self, schema)


