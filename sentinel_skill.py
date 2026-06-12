"""Sentinel Skill — a Pharos AgentSkill (MCP server) for pre-action on-chain risk.

A reusable Skill any agent can call BEFORE moving value on Pharos: it returns a
risk verdict (safe / caution / dangerous) + reasons, and a risk-bounded
execution plan. Read-only — it never signs or sends a transaction.

Run (stdio MCP server):
    pip install -r requirements.txt
    python sentinel_skill.py

The two tools below are the Skill's public surface. Risk logic (v2) is RPC-only:
contract-vs-EOA, proxy detection (EIP-1167 minimal / EIP-1967+1822 upgradeable),
ERC-20 introspection (symbol/decimals/supply), bytecode opcode analysis
(SELFDESTRUCT / unguarded DELEGATECALL), ownership & upgrade-admin concentration
(owner() + EIP-1967 admin, EOA vs contract), pausable state (paused()),
tiny-bytecode stubs, and action/target mismatches. No external indexer or API.
"""
from __future__ import annotations

import re

from mcp.server.fastmcp import FastMCP

import pharos_atlantic as pharos

# log_level WARNING keeps the stdio transport quiet (no per-request INFO chatter)
# so a consuming agent's output stays clean.
mcp = FastMCP("sentinel", log_level="WARNING")

# Verdict bands over the additive risk score.
DANGEROUS_AT = 70
CAUTION_AT = 35

_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


def _verdict(score: int) -> str:
    if score >= DANGEROUS_AT:
        return "dangerous"
    if score >= CAUTION_AT:
        return "caution"
    return "safe"


def _score_contract(address: str, action: str, reasons: list, data: dict) -> int:
    """Risk signals for a contract target. Each probe is defensive: a failing RPC
    read degrades that one signal rather than sinking the whole verdict."""
    score = 0
    size = pharos.code_size(address)
    data["code_size"] = size

    minimal = pharos.is_minimal_proxy(address)
    impl = pharos.proxy_impl(address)
    if minimal:
        data["minimal_proxy"] = True
        score += 10
        reasons.append("EIP-1167 minimal proxy — the real logic lives in a fixed implementation; verify it")
    if impl:
        data["upgradeable_impl"] = impl
        score += 20
        reasons.append(f"upgradeable proxy (impl {impl}) — the owner can change the contract's logic after you interact")
    elif size < 100 and not minimal:
        score += 35
        reasons.append(f"tiny bytecode ({size} bytes) — likely a stub/trap rather than a working contract")

    token = pharos.erc20_info(address)
    if token["is_erc20"]:
        data["erc20"] = {k: token[k] for k in ("symbol", "name", "decimals", "total_supply")}
        if token["total_supply"] == 0:
            score += 30
            reasons.append("token reports zero total supply — non-functional or a trap")

    # bytecode opcode analysis (proper opcode walk, not a substring match)
    ops = pharos.dangerous_opcodes(address)
    if ops["selfdestruct"]:
        data["selfdestruct"] = True
        score += 25
        reasons.append("bytecode contains SELFDESTRUCT — the contract can be destroyed, taking its logic with it")
    if ops["delegatecall"] and not (minimal or impl):
        data["delegatecall"] = True
        score += 15
        reasons.append("bytecode uses DELEGATECALL outside a known proxy pattern — it can execute external code")

    # ownership / upgrade-admin concentration
    own = pharos.owner(address)
    if own:
        data["owner"] = own
        if pharos.is_contract(own):
            score += 5
            reasons.append(f"owned by a contract ({own}) — likely a multisig/timelock; verify it")
        else:
            score += 10
            reasons.append(f"single externally-owned owner ({own}) holds privileged control (can often pause/mint/blacklist)")
    adm = pharos.admin(address)
    if adm:
        data["proxy_admin"] = adm
        if not impl:
            score += 10
            reasons.append(f"has an EIP-1967 upgrade admin ({adm}) — contract logic can be changed")

    # pausable state
    if pharos.is_paused(address) is True:
        data["paused"] = True
        score += 20
        reasons.append("contract is currently PAUSED — interactions may fail or are gated by the owner")

    if action == "approve":
        # Soften approvals to plain, healthy tokens (a normal, expected action);
        # keep strong friction where allowance drains actually happen — non-tokens,
        # trap (zero-supply) tokens, and upgradeable proxies.
        if token["is_erc20"]:
            if (token["total_supply"] or 0) > 0 and not (minimal or impl):
                score += 10
                reasons.append("approve grants a spend allowance — set a finite cap and approve only trusted spenders")
            else:
                score += 35
                reasons.append("approve to a non-standard token (zero-supply or upgradeable) — verify before granting an allowance")
        else:
            score += 50
            reasons.append("approve target does not expose an ERC-20 interface — approvals are for tokens; "
                           "this is the #1 drain vector, verify the target")

    return score


def _score_eoa(address: str, action: str, reasons: list, data: dict) -> int:
    """Risk signals for an externally-owned account (no code)."""
    score = 0
    hist = pharos.tx_count(address)
    bal = pharos.balance_wei(address) / 1e18
    data["counterparty_tx_count"] = hist
    data["counterparty_balance_phrs"] = round(bal, 6)

    if action in ("approve", "swap", "call"):
        score += 35
        reasons.append(f"'{action}' target is an externally-owned account, not a contract — it cannot honor this action; likely a mistake")
    if hist == 0 and bal == 0:
        score += 35
        reasons.append("counterparty has no transaction history and zero balance — brand-new/unused address")
    elif hist == 0:
        score += 10
        reasons.append("counterparty has received funds but never sent a transaction — limited history")

    return score


@mcp.tool()
def risk_check(address: str, action: str = "transfer", amount_phrs: float = 0.0) -> dict:
    """Assess the risk of interacting with `address` on Pharos Atlantic.

    Args:
        address: target contract or counterparty (0x + 40 hex chars).
        action: one of transfer | swap | approve | call.
        amount_phrs: size of the action in PHRS (optional, for exposure context).
    Returns a dict: {verdict, score, reasons[], data{}}.

    Signals (RPC-only, v2): contract vs EOA; EIP-1167 minimal and EIP-1967/1822
    upgradeable-proxy detection; ERC-20 introspection (symbol/decimals/supply,
    zero-supply trap); bytecode opcode analysis (SELFDESTRUCT / unguarded
    DELEGATECALL); ownership & upgrade-admin concentration (owner() + EIP-1967
    admin, EOA vs contract); pausable state; tiny-bytecode stubs; and
    action/target mismatches (e.g. approve to a non-token or an EOA).
    """
    if not _ADDRESS_RE.match(address or ""):
        return {"verdict": "unknown", "score": -1,
                "reasons": [f"'{address}' is not a valid 0x-prefixed 20-byte address"], "data": {}}
    if not pharos.chain_ok():
        return {"verdict": "unknown", "score": -1,
                "reasons": ["could not reach Pharos Atlantic RPC"], "data": {}}

    action = (action or "transfer").lower()
    reasons, data = [], {}
    contract = pharos.is_contract(address)
    data["is_contract"] = contract

    score = (_score_contract if contract else _score_eoa)(address, action, reasons, data)

    if amount_phrs and amount_phrs > 0:
        data["amount_phrs"] = amount_phrs  # exposure context for the caller's own limits

    if not reasons:
        reasons.append("no elevated risk signals from on-chain checks (RPC heuristics v2)")

    return {"verdict": _verdict(score), "score": score, "reasons": reasons, "data": data}


@mcp.tool()
def execution_plan(address: str, action: str, amount_phrs: float,
                   max_risk: str = "caution") -> dict:
    """Return a risk-gated execution plan: approve/block + bounded params.

    Args:
        address: target contract/counterparty.
        action: transfer | swap | approve | call.
        amount_phrs: requested size.
        max_risk: caller's tolerance — safe | caution (block anything riskier).
    """
    rc = risk_check(address, action, amount_phrs)
    order = {"safe": 0, "caution": 1, "dangerous": 2, "unknown": 3}
    allowed = order.get(rc["verdict"], 3) <= order.get(max_risk, 1)

    plan = {
        "approved": allowed,
        "verdict": rc["verdict"],
        "reasons": rc["reasons"],
        "suggested": {},
    }
    if allowed:
        # de-risk sizing slightly when verdict == caution
        factor = 0.5 if rc["verdict"] == "caution" else 1.0
        plan["suggested"] = {
            "amount_phrs": round(amount_phrs * factor, 6),
            "max_slippage_bps": 50 if action == "swap" else None,
            "note": "size reduced for caution verdict" if factor < 1 else "full size",
        }
    else:
        plan["suggested"] = {"action": "BLOCK", "note": f"verdict exceeds max_risk={max_risk}"}
    return plan


if __name__ == "__main__":
    mcp.run()
