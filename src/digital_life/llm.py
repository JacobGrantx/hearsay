"""Every runtime model call goes through here.

Why one module:
  * Reproducibility. Model outputs cannot be seeded, so every call's request and
    response are recorded in a replay cache (experiments/llm_cache/). A run whose
    calls are all cached replays exactly, with no API key: LLM_MODE=replay.
  * Cost control. Spend is priced from the usage the API returns and checked
    against a cap (LLM_BUDGET_USD, default 100) before each live call.
  * Evidence. Each call's usage, cost and stop reason go into the run's events
    log when a RunLog is passed, so EXPERIMENTS.md can quote real numbers.

Credentials (first match wins):
  ANTHROPIC_API_KEY                                    -> Anthropic()          (judges, first-party API)
  ANTHROPIC_FOUNDRY_API_KEY + ANTHROPIC_FOUNDRY_RESOURCE -> AnthropicFoundry()  (our development setup)
Read from the process environment, then from the repo's .env. Never logged.

Modes (LLM_MODE):
  auto    use the cached response when one exists, otherwise call live and record it (default)
  live    always call live and overwrite the cache entry
  replay  cache only; a miss raises CacheMiss (proves a run is fully reproducible offline)

Pass `tag` (for example f"{seed}:{step}:{agent_id}") whenever two identical prompts
should get independent samples; the tag is part of the cache key.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CACHE_DIR = Path(os.environ.get("LLM_CACHE_DIR", REPO / "experiments" / "llm_cache"))
SPEND_FILE = Path(os.environ.get("LLM_SPEND_FILE", REPO / ".llm_spend.json"))
DEFAULT_MODEL = "claude-opus-5-5"

# USD per million tokens: (input, output, cache read, cache write).
# Input/output and the Opus/Sonnet cache-read rates are published list prices.
# Cache writes are taken as 1.25x input and the Haiku cache read as 0.1x input.
# This is a budget guard, not an invoice: check the provider bill for real cost.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00, 0.20, 5.00),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20, 2.50),
    "claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125),
}


class CacheMiss(RuntimeError):
    pass


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class Completion:
    text: str
    model: str
    stop_reason: str | None
    usage: dict = field(default_factory=dict)
    cost_usd: float = 0.0
    cached: bool = False
    key: str = ""


def _env(name: str) -> str | None:
    if os.environ.get(name):
        return os.environ[name]
    env_file = REPO / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            k, _, v = line.strip().partition("=")
            if k == name and v and not line.lstrip().startswith("#"):
                return v.strip().strip("\"'")
    return None


def make_client():
    import anthropic

    if _env("ANTHROPIC_API_KEY"):
        return anthropic.Anthropic(api_key=_env("ANTHROPIC_API_KEY"))
    if _env("ANTHROPIC_FOUNDRY_API_KEY") and _env("ANTHROPIC_FOUNDRY_RESOURCE"):
        return anthropic.AnthropicFoundry(api_key=_env("ANTHROPIC_FOUNDRY_API_KEY"), resource=_env("ANTHROPIC_FOUNDRY_RESOURCE"))
    raise RuntimeError("No model credentials. Set ANTHROPIC_API_KEY in .env (see .env.example), or run with LLM_MODE=replay.")


def cost_usd(model: str, usage: dict) -> float:
    pin, pout, pread, pwrite = PRICES.get(model, PRICES[DEFAULT_MODEL])
    return (
        usage.get("input_tokens", 0) * pin
        + usage.get("output_tokens", 0) * pout
        + usage.get("cache_read_input_tokens", 0) * pread
        + usage.get("cache_creation_input_tokens", 0) * pwrite
    ) / 1_000_000


def spent_usd() -> float:
    if SPEND_FILE.exists():
        return json.loads(SPEND_FILE.read_text()).get("usd", 0.0)
    return 0.0


def _add_spend(usd: float) -> None:
    data = json.loads(SPEND_FILE.read_text()) if SPEND_FILE.exists() else {"usd": 0.0, "calls": 0}
    data["usd"] = data.get("usd", 0.0) + usd
    data["calls"] = data.get("calls", 0) + 1
    SPEND_FILE.write_text(json.dumps(data, indent=2) + "\n")


def _key(request: dict) -> str:
    return hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _cache_path(key: str) -> Path:
    return CACHE_DIR / key[:2] / f"{key}.json"


_client = None
_lock = threading.Lock()  # agents call in parallel; the ledger, cache and client are shared


def complete(
    messages: list[dict] | str,
    *,
    system: str | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 16000,
    effort: str = "medium",
    tag: str = "",
    schema: dict | None = None,
    thinking: dict | None = None,
    log=None,
    client=None,
) -> Completion:
    """One Messages API call with replay cache, budget check and usage logging.

    schema: a JSON Schema; the reply is then guaranteed to be JSON matching it (structured outputs).
    thinking: e.g. {"type": "disabled"} on Haiku 5.5 at effort <= high for fast, cheap agent turns.
    """
    global _client
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    request = {"model": model, "system": system, "messages": messages, "max_tokens": max_tokens, "effort": effort, "tag": tag}
    if schema is not None:
        request["schema"] = schema
    if thinking is not None:
        request["thinking"] = thinking
    key = _key(request)
    path = _cache_path(key)
    mode = os.environ.get("LLM_MODE", "auto")

    if mode in ("auto", "replay") and path.exists():
        rec = json.loads(path.read_text())
        out = Completion(**rec["response"], cached=True, key=key)
        out.cost_usd = 0.0
    elif mode == "replay":
        raise CacheMiss(f"no cached response for request {key[:12]} (LLM_MODE=replay)")
    else:
        budget = float(os.environ.get("LLM_BUDGET_USD", "100"))
        with _lock:
            if spent_usd() >= budget:
                raise BudgetExceeded(f"model spend ${spent_usd():.2f} has reached LLM_BUDGET_USD=${budget:.2f}")
            cl = client or _client or make_client()
            if client is None:
                _client = cl
        output_config = {"effort": effort}
        if schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": schema}
        kwargs = {"model": model, "max_tokens": max_tokens, "messages": messages, "output_config": output_config}
        if system:
            kwargs["system"] = system
        if thinking is not None:
            kwargs["thinking"] = thinking
        resp = cl.messages.create(**kwargs)
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        u = resp.usage
        usage = {k: int(getattr(u, k, 0) or 0) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")}
        out = Completion(text=text, model=resp.model, stop_reason=resp.stop_reason, usage=usage, cost_usd=cost_usd(model, usage), key=key)
        record = {"request": request, "response": {k: v for k, v in asdict(out).items() if k not in ("cached", "key", "cost_usd")}}
        with _lock:
            _add_spend(out.cost_usd)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")

    if log is not None:
        log.event("llm_call", key=key[:12], model=out.model, tag=tag, cached=out.cached, stop_reason=out.stop_reason, usage=out.usage, cost_usd=round(out.cost_usd, 6))
    return out
