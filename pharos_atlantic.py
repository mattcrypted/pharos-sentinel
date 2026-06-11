"""Pharos Atlantic Testnet config + lightweight on-chain read helpers.

Verified from docs.pharos.xyz/getting-started/network/atlantic-testnet (2026-06-10):
  RPC      : https://atlantic.dplabs-internal.com
  WSS      : wss://atlantic.dplabs-internal.com
  chainId  : 688689
  explorer : https://atlantic.pharosscan.xyz/
  faucet   : via Pharos Discord/website (not a public URL in docs)
  symbol   : PHRS (testnet gas token; confirm)

Only stdlib + web3 used. If web3 isn't installed, helpers fall back to raw JSON-RPC.
"""
from __future__ import annotations
import json
import urllib.request

RPC_URL = "https://atlantic.dplabs-internal.com"
WSS_URL = "wss://atlantic.dplabs-internal.com"
CHAIN_ID = 688689
EXPLORER = "https://atlantic.pharosscan.xyz"
SYMBOL = "PHRS"


def rpc(method: str, params: list):
    """Minimal JSON-RPC call (no deps)."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(RPC_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        out = json.loads(r.read().decode())
    if "error" in out:
        raise RuntimeError(out["error"])
    return out.get("result")


def is_contract(address: str) -> bool:
    code = rpc("eth_getCode", [address, "latest"])
    return bool(code) and code != "0x"


def code_size(address: str) -> int:
    code = rpc("eth_getCode", [address, "latest"])
    return 0 if not code or code == "0x" else (len(code) - 2) // 2


def balance_wei(address: str) -> int:
    return int(rpc("eth_getBalance", [address, "latest"]), 16)


def tx_count(address: str) -> int:
    return int(rpc("eth_getTransactionCount", [address, "latest"]), 16)


def chain_ok() -> bool:
    try:
        return int(rpc("eth_chainId", []), 16) == CHAIN_ID
    except Exception:
        return False


# --- Contract introspection (RPC-only: eth_call + eth_getStorageAt) ------------
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
    """Raw eth_call; returns hex string (possibly '0x')."""
    return rpc("eth_call", [{"to": to, "data": data}, "latest"]) or "0x"


def storage_at(address: str, slot: str) -> str:
    return rpc("eth_getStorageAt", [address, slot, "latest"]) or "0x"


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
        code = (rpc("eth_getCode", [address, "latest"]) or "0x").lower()
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
        code = rpc("eth_getCode", [address, "latest"]) or "0x"
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
