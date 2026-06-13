"""Pharos Atlantic Testnet config + read-only on-chain helpers, executed via Foundry.

Verified from docs.pharos.xyz/getting-started/network/atlantic-testnet (2026-06-10):
  RPC      : https://atlantic.dplabs-internal.com
  WSS      : wss://atlantic.dplabs-internal.com
  chainId  : 688689
  explorer : https://atlantic.pharosscan.xyz/
  symbol   : PHRS (testnet gas token)

EXECUTION MODEL: every on-chain read is performed by the Foundry `cast` CLI — the
same toolchain the rest of the Pharos Skill Engine uses — not a hand-rolled HTTP
client. Dedicated subcommands back the risk reads (`cast code` / `cast call` /
`cast storage` / `cast balance` / `cast nonce` / `cast chain-id`); `rpc()` is a
thin wrapper over `cast rpc <method>` for the tx/receipt lookups the x402 gate
needs. All reads are gasless and keyless — Sentinel never signs or sends a tx.
Requires `cast` (Foundry) on PATH; install per the Skill Engine Prerequisites.
"""
from __future__ import annotations
import concurrent.futures
import json
import os
import shutil
import subprocess
import threading
import time

RPC_URL = "https://atlantic.dplabs-internal.com"
WSS_URL = "wss://atlantic.dplabs-internal.com"
CHAIN_ID = 688689
EXPLORER = "https://atlantic.pharosscan.xyz"
SYMBOL = "PHRS"

CAST = shutil.which("cast") or "cast"

# stderr fragments that indicate a transient RPC hiccup worth retrying with backoff
_TRANSIENT = ("429", "502", "503", "504", "timed out", "timeout",
              "rate limit", "error sending request", "connection")


def _cast(args: list, *, timeout: int = 30) -> str:
    """Run a read-only `cast` subcommand against Atlantic and return stripped stdout.

    Raises RuntimeError on a cast error (e.g. `execution reverted` for a method the
    target doesn't expose) — callers that treat that as "signal absent" wrap it in
    try/except, exactly as before. Retries transient RPC throttling with backoff."""
    cmd = [CAST, *args, "--rpc-url", RPC_URL]
    last = ""
    for attempt in range(4):
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            last = f"cast {args[0]} timed out"
            if attempt < 3:
                time.sleep(0.4 * 2 ** attempt)
                continue
            raise RuntimeError(last)
        except FileNotFoundError:
            raise RuntimeError("Foundry `cast` not found on PATH — install Foundry "
                               "(see the Skill Engine Prerequisites)")
        if p.returncode == 0:
            return p.stdout.strip()
        last = (p.stderr or "").strip()
        if attempt < 3 and any(s in last.lower() for s in _TRANSIENT):
            time.sleep(0.4 * 2 ** attempt)
            continue
        raise RuntimeError(last or f"cast {args[0]} failed")


# --- Request-scoped read cache + concurrent prefetch ---------------------------
# A single risk_check otherwise re-fetches identical reads several times (the same
# bytecode ~4x). The cache dedupes them to one round-trip; warm() then primes every
# read concurrently so the sequential scoring code pays no further network cost.
# Cleared at the start of each risk_check, so live state changes are always re-read.
PREFETCH_WORKERS = int(os.environ.get("SENTINEL_PREFETCH_WORKERS", "12"))

_read_cache: dict = {}
_cache_lock = threading.Lock()


class _Entry:
    __slots__ = ("ok", "val", "err")

    def __init__(self, ok, val=None, err=None):
        self.ok, self.val, self.err = ok, val, err


def clear_cache() -> None:
    with _cache_lock:
        _read_cache.clear()


def _cached(args: list):
    """`_cast` with a request-scoped cache. Caches both values and errors — a revert
    is deterministic, and transient errors are already retried inside `_cast` — so a
    repeated or pre-warmed read costs zero extra round-trips."""
    key = tuple(args)
    with _cache_lock:
        hit = _read_cache.get(key)
    if hit is not None:
        if hit.ok:
            return hit.val
        raise hit.err
    try:
        val = _cast(args)
    except Exception as e:
        with _cache_lock:
            _read_cache[key] = _Entry(False, err=e)
        raise
    with _cache_lock:
        _read_cache[key] = _Entry(True, val=val)
    return val


def rpc(method: str, params: list):
    """Generic JSON-RPC call executed through Foundry (`cast rpc <method> ...`).

    Returns the decoded `result` (same shape a raw JSON-RPC client would give, with
    hex fields preserved). Used for the tx/receipt lookups the x402 gate verifies."""
    args = ["rpc", method]
    for p in params:
        args.append(p if isinstance(p, str) else json.dumps(p))
    out = _cast(args)
    if out == "":
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return out


def get_code(address: str) -> str:
    return _cached(["code", address]) or "0x"


def is_contract(address: str) -> bool:
    code = get_code(address)
    return bool(code) and code != "0x"


def code_size(address: str) -> int:
    code = get_code(address)
    return 0 if not code or code == "0x" else (len(code) - 2) // 2


def balance_wei(address: str) -> int:
    return int(_cached(["balance", address]))         # cast prints wei in decimal


def tx_count(address: str) -> int:
    return int(_cached(["nonce", address]))           # cast prints nonce in decimal


def chain_ok() -> bool:
    try:
        return int(_cached(["chain-id"])) == CHAIN_ID  # cast prints chain id in decimal
    except Exception:
        return False


# --- Contract introspection (read-only `cast call` / `cast storage`) -----------
# Function selectors (first 4 bytes of keccak256(signature)).
SEL_TOTAL_SUPPLY = "0x18160ddd"   # totalSupply()
SEL_DECIMALS     = "0x313ce567"   # decimals()
SEL_SYMBOL       = "0x95d89b41"   # symbol()
SEL_NAME         = "0x06fdde03"   # name()
SEL_OWNER        = "0x8da5cb5b"   # owner()  (Ownable)
SEL_PAUSED       = "0x5c975abb"   # paused() (Pausable)

# Standard upgradeable-proxy storage slots (implementation / admin addresses live here).
EIP1967_IMPL_SLOT  = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
EIP1822_IMPL_SLOT  = "0xc5f16f0fcc639fa48a6947836d9850f504798523bf8c9a3a87d5876cf622bcf7"
EIP1967_ADMIN_SLOT = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"

# EVM opcodes worth flagging in runtime bytecode.
_OP_DELEGATECALL = 0xF4
_OP_SELFDESTRUCT = 0xFF


def eth_call(to: str, data: str) -> str:
    """Read-only contract call via `cast call`; returns raw return hex (possibly '0x').
    Raises (via _cached/_cast) if the method reverts — callers treat that as "not exposed"."""
    return _cached(["call", to, data]) or "0x"


def storage_at(address: str, slot: str) -> str:
    return _cached(["storage", address, slot]) or "0x"


def _addr_from_word(word: str):
    """Last 20 bytes of a 32-byte storage word as an address, or None if zero."""
    if not word or word == "0x":
        return None
    h = word[2:].rjust(64, "0")
    addr = "0x" + h[-40:]
    return None if int(addr, 16) == 0 else addr


def _uint(hexstr: str):
    if not hexstr or hexstr == "0x":
        return None
    return int(hexstr, 16)


def _string(hexstr: str):
    """Best-effort decode of an ABI-encoded string or a bytes32-packed symbol."""
    if not hexstr or hexstr == "0x":
        return None
    try:
        raw = bytes.fromhex(hexstr[2:])
    except ValueError:
        return None
    # dynamic string: [offset(32)][length(32)][data...]
    if len(raw) >= 64 and int.from_bytes(raw[0:32], "big") == 32:
        length = int.from_bytes(raw[32:64], "big")
        data = raw[64:64 + length]
        s = data.decode("utf-8", "ignore").strip("\x00").strip()
        if s:
            return s
    # bytes32 fixed-string fallback
    s = raw.rstrip(b"\x00").decode("utf-8", "ignore").strip()
    return s or None


def proxy_impl(address: str):
    """Implementation address if `address` is an EIP-1967/1822 upgradeable proxy, else None.

    Upgradeable proxies let an owner swap the contract's logic AFTER you interact —
    a genuine, common rug/exploit vector worth flagging.
    """
    for slot in (EIP1967_IMPL_SLOT, EIP1822_IMPL_SLOT):
        try:
            impl = _addr_from_word(storage_at(address, slot))
        except Exception:
            impl = None
        if impl:
            return impl
    return None


def is_minimal_proxy(address: str) -> bool:
    """Detect an EIP-1167 minimal proxy by its bytecode signature.

    Minimal proxies delegatecall to a single fixed implementation; the real logic
    is elsewhere, so the target alone tells you little.
    """
    try:
        code = get_code(address).lower()
    except Exception:
        return False
    return code.startswith("0x363d3d373d3d3d363d73") or "5af43d82803e903d91602b57fd5bf3" in code


def erc20_info(address: str) -> dict:
    """Best-effort ERC-20 introspection. Returns {is_erc20, total_supply, decimals, symbol, name}.

    `is_erc20` is True only if the contract actually answers totalSupply() — a cheap
    way to tell "this is a token" from "this is some other contract / an EOA".
    """
    info = {"is_erc20": False, "total_supply": None, "decimals": None,
            "symbol": None, "name": None}
    try:
        ts = _uint(eth_call(address, SEL_TOTAL_SUPPLY))
    except Exception:
        ts = None
    if ts is None:
        return info
    info["is_erc20"] = True
    info["total_supply"] = ts
    for key, sel, dec in (("decimals", SEL_DECIMALS, _uint),
                          ("symbol", SEL_SYMBOL, _string),
                          ("name", SEL_NAME, _string)):
        try:
            info[key] = dec(eth_call(address, sel))
        except Exception:
            pass
    return info


def _bool(hexstr):
    if not hexstr or hexstr == "0x":
        return None
    try:
        return bool(int(hexstr, 16) & 1)
    except ValueError:
        return None


def _strict_addr_from_word(word):
    """Decode a 32-byte word as an address ONLY if it's a clean left-padded address
    (upper 12 bytes zero) — avoids misreading a non-address eth_call return as an owner."""
    if not word or word == "0x":
        return None
    h = word[2:].rjust(64, "0")
    if h[:24] != "0" * 24:
        return None
    addr = "0x" + h[24:]
    return None if int(addr, 16) == 0 else addr


def owner(address):
    """Ownable owner() if the contract exposes one, else None. A privileged owner can
    often pause / mint / blacklist. Zero address (renounced) and non-Ownable both → None."""
    try:
        return _strict_addr_from_word(eth_call(address, SEL_OWNER))
    except Exception:
        return None


def admin(address):
    """EIP-1967 proxy upgrade admin (who may swap the logic), or None."""
    try:
        return _addr_from_word(storage_at(address, EIP1967_ADMIN_SLOT))
    except Exception:
        return None


def is_paused(address):
    """True/False if the contract exposes Pausable paused(); None if it doesn't."""
    try:
        return _bool(eth_call(address, SEL_PAUSED))
    except Exception:
        return None


def dangerous_opcodes(address):
    """Walk runtime bytecode (skipping PUSH immediates) and flag DELEGATECALL /
    SELFDESTRUCT — opcodes that let a contract run external code or destroy itself.
    Proper opcode-aware scan, no disassembler dependency."""
    flags = {"delegatecall": False, "selfdestruct": False}
    try:
        code = get_code(address)
        raw = bytes.fromhex(code[2:]) if code != "0x" else b""
    except Exception:
        return flags
    i, n = 0, len(raw)
    while i < n:
        op = raw[i]
        if 0x60 <= op <= 0x7f:           # PUSH1..PUSH32 — skip the pushed immediate
            i += 1 + (op - 0x5f)
            continue
        if op == _OP_DELEGATECALL:
            flags["delegatecall"] = True
        elif op == _OP_SELFDESTRUCT:
            flags["selfdestruct"] = True
        i += 1
    return flags


def warm(address: str, *, workers: int = PREFETCH_WORKERS) -> None:
    """Concurrently pre-fetch every read a single risk_check might need, so the
    sequential scoring code then runs against a warm cache (turning ~12 serial
    round-trips into a few concurrent waves). Bounded by `workers` (env
    SENTINEL_PREFETCH_WORKERS) to stay under the RPC rate limit. Errors are
    swallowed + cached here, so a reverting probe (e.g. owner() on a non-Ownable)
    costs no second round-trip during scoring. Call clear_cache() first."""
    jobs = [
        ["code", address],
        ["storage", address, EIP1967_IMPL_SLOT],
        ["storage", address, EIP1822_IMPL_SLOT],
        ["storage", address, EIP1967_ADMIN_SLOT],
        ["call", address, SEL_TOTAL_SUPPLY],
        ["call", address, SEL_DECIMALS],
        ["call", address, SEL_SYMBOL],
        ["call", address, SEL_NAME],
        ["call", address, SEL_OWNER],
        ["call", address, SEL_PAUSED],
        ["nonce", address],
        ["balance", address],
    ]

    def _safe(job):
        try:
            _cached(job)
        except Exception:
            pass

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(_safe, jobs))
