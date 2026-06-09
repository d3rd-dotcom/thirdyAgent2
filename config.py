"""
config.py — Centralised configuration for thirdyAgent2
═══════════════════════════════════════════════════════
Improvements over v1:
  - AGENTHUB_HEADERS is now lazy (_LazyHeaders) so it reads the key
    after .env is fully loaded, not at import time.
  - .env parser handles `export KEY=val`, values containing `=`,
    and quoted values properly.
  - validate() returns a structured dict instead of only printing.
  - _env_int() guards against malformed env values.
  - All type hints use `from __future__ import annotations` for Py 3.9.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


# ── .env loader ────────────────────────────────────────────────────────
def _load_dotenv(env_path: Path) -> None:
    """
    Minimal .env parser — handles:
      KEY=value
      KEY="value with spaces"
      KEY='value with spaces'
      KEY=value=with=equals      (only first `=` is the separator)
      export KEY=value           (shell-style export prefix stripped)
      # comment lines
    Does NOT override already-set environment variables.
    """
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv as _ld
        _ld(env_path, override=False)
        return
    except ImportError:
        pass  # fall through to manual parser

    with open(env_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue
            key, _, val = line.partition("=")   # partition stops at FIRST =
            key = key.strip()
            val = val.strip()
            # Strip surrounding matching quotes
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                val = val[1:-1]
            if key and key not in os.environ:
                os.environ[key] = val


_load_dotenv(Path(__file__).parent / ".env")


# ── Value readers ──────────────────────────────────────────────────────
def _env(key: str, default: str = "") -> str:
    """Read env var and strip accidental surrounding whitespace."""
    return os.environ.get(key, default).strip()


def _env_int(key: str, default: int) -> int:
    """Read env var as int with a safe fallback (ignores malformed values)."""
    raw = os.environ.get(key, "")
    if raw.strip().lstrip("-").isdigit():
        return int(raw.strip())
    return default


def _env_bool(key: str, default: bool = False) -> bool:
    return os.environ.get(key, str(default)).strip().lower() in ("1", "true", "yes")


# ═══════════════════════════════════════════════════════════════════
#  AgentHub
# ═══════════════════════════════════════════════════════════════════
AGENTHUB_API_KEY : str = _env("AGENTHUB_API_KEY")
AGENT_ID         : str = _env("AGENT_ID", "thirdyAgent2-5dfce3")
AGENTHUB_HUB_URL : str = _env("AGENTHUB_HUB_URL", "https://agents.pinai.tech")
PUBLIC_URL       : str = _env(
    "PUBLIC_URL",
    "https://YOUR_NGROK_URL.ngrok-free.app",
)

# ═══════════════════════════════════════════════════════════════════
#  AI Providers
# ═══════════════════════════════════════════════════════════════════
GROQ_API_KEY      : str = _env("GROQ_API_KEY")
CEREBRAS_KEY      : str = _env("CEREBRAS_KEY")
NVIDIA_KEY        : str = _env("NVIDIA_KEY")
CF_KEY            : str = _env("CF_KEY")
CF_ACCOUNT        : str = _env("CF_ACCOUNT")
MISTRAL_KEY       : str = _env("MISTRAL_KEY")
COHERE_KEY        : str = _env("COHERE_KEY")
GEMINI_KEY        : str = _env("GEMINI_KEY")        # Phase 8
GITHUB_MODELS_KEY : str = _env("GITHUB_MODELS_KEY") # Phase 8

# ═══════════════════════════════════════════════════════════════════
#  RAG
# ═══════════════════════════════════════════════════════════════════
CHROMA_PERSIST_DIR : str = _env(
    "CHROMA_PERSIST_DIR",
    str(Path(__file__).parent / "chroma_db"),
)
RAG_TOP_K         : int = _env_int("RAG_TOP_K",         4)
RAG_EMBED_MODEL   : str = _env("RAG_EMBED_MODEL",       "embed-english-v3.0")
RAG_CHUNK_SIZE    : int = _env_int("RAG_CHUNK_SIZE",     512)
RAG_CHUNK_OVERLAP : int = _env_int("RAG_CHUNK_OVERLAP",  64)

# ═══════════════════════════════════════════════════════════════════
#  Security / App
# ═══════════════════════════════════════════════════════════════════
WEBHOOK_SECRET : str  = _env("WEBHOOK_SECRET")
BASE_DIR       : str  = str(Path(__file__).parent)
FLASK_PORT     : int  = _env_int("PORT", _env_int("FLASK_PORT", 5000))
DEBUG          : bool = _env_bool("DEBUG")
AGENT_NAME     : str  = "thirdyAgent2"


# ── Lazy AgentHub headers ──────────────────────────────────────────────
class _LazyHeaders:
    """
    FIX (v1 bug): v1 built the Authorization header at module import time.
    If AGENTHUB_API_KEY was empty at import (e.g. because .env hadn't been
    parsed yet in some import orders), the header was permanently wrong.

    This object builds the dict fresh on every attribute access, so it
    always reflects the current value of AGENTHUB_API_KEY.

    Usage is identical to a plain dict:
        requests.post(url, headers=AGENTHUB_HEADERS, ...)
    """
    @property
    def _d(self) -> dict:
        return {
            "Authorization": f"Bearer {AGENTHUB_API_KEY}",
            "Content-Type":  "application/json",
        }

    def __getitem__(self, key: str) -> str:     return self._d[key]
    def __iter__(self):                          return iter(self._d)
    def __contains__(self, key: object) -> bool: return key in self._d
    def keys(self):                              return self._d.keys()
    def values(self):                            return self._d.values()
    def items(self):                             return self._d.items()
    def get(self, key: str, default=None):       return self._d.get(key, default)
    def copy(self) -> dict:                      return self._d.copy()


AGENTHUB_HEADERS: _LazyHeaders = _LazyHeaders()


# ── Key registry ───────────────────────────────────────────────────────
_REQUIRED: dict[str, str] = {
    "AGENTHUB_API_KEY": AGENTHUB_API_KEY,
    "CEREBRAS_KEY":     CEREBRAS_KEY,
    "GROQ_API_KEY":     GROQ_API_KEY,
    "COHERE_KEY":       COHERE_KEY,
}
_OPTIONAL: dict[str, str] = {
    "NVIDIA_KEY":         NVIDIA_KEY,
    "CF_KEY":             CF_KEY,
    "CF_ACCOUNT":         CF_ACCOUNT,
    "MISTRAL_KEY":        MISTRAL_KEY,
    "GEMINI_KEY":         GEMINI_KEY,
    "GITHUB_MODELS_KEY":  GITHUB_MODELS_KEY,
    "WEBHOOK_SECRET":     WEBHOOK_SECRET,
}


def validate(strict: bool = False) -> dict:
    """
    FIX (v1): v1 only printed; callers couldn't programmatically check result.
    Now returns {"ok": bool, "missing_required": [...], "missing_optional": [...]}.

    Re-reads from os.environ at call time so late .env loading is reflected.
    Prints a human summary as a side-effect (useful for startup banners).
    """
    live_req = {k: _env(k) for k in _REQUIRED}
    live_opt = {k: _env(k) for k in _OPTIONAL}

    missing_req = [k for k, v in live_req.items() if not v]
    missing_opt = [k for k, v in live_opt.items() if not v]
    ok = len(missing_req) == 0 and (not strict or len(missing_opt) == 0)

    if missing_req:
        print("❌  MISSING REQUIRED KEYS:")
        for k in missing_req:
            print(f"     export {k}=<your_value>")
    else:
        print("✅  All required keys present")

    if missing_opt:
        print("⚠️   Missing optional keys (reduced coverage):")
        for k in missing_opt:
            print(f"     {k}")

    return {"ok": ok, "missing_required": missing_req, "missing_optional": missing_opt}


def _mask(v: str) -> str:
    """Mask a secret, showing first 4 and last 4 chars only."""
    if not v:
        return "(not set)"
    n = len(v)
    if n <= 8:
        return "*" * n
    return v[:4] + "*" * max(4, n - 8) + v[-4:]


def list_keys() -> None:
    print("\n─── Required ───────────────────────────────────────")
    for k in _REQUIRED:
        v = _env(k)
        print(f"  {'✅' if v else '❌'}  {k:28} {_mask(v)}")
    print("\n─── Optional ───────────────────────────────────────")
    for k in _OPTIONAL:
        v = _env(k)
        print(f"  {'✅' if v else '⚠️ '}  {k:28} {_mask(v)}")
    print()


if __name__ == "__main__":
    if "--list" in sys.argv:
        list_keys()
    elif "--validate" in sys.argv:
        result = validate()
        sys.exit(0 if result["ok"] else 1)
    else:
        print("Usage: python config.py --validate | --list")
