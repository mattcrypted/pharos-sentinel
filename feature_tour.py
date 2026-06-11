"""Feature tour — exercise EVERY Sentinel risk signal, v1 through v2.

Run:
    .venv/bin/python feature_tour.py            # full tour (synthetic + live)
    .venv/bin/python feature_tour.py --synthetic # instant, no network
    .venv/bin/python feature_tour.py --live      # only the real-chain proof

Section A (synthetic) fabricates exact on-chain conditions via the same fake-RPC
used by the tests, so each signal fires deterministically — instant, no network.
Section B (live) runs the identical engine against real Pharos Atlantic addresses.

Each line shows: [version] signal -> verdict (score) and the reasons/ data keys.
Tweak the CASES lists, or call risk_check on your own addresses, to probe more.
"""
from __future__ import annotations

import sys

import pharos_atlantic as pharos
import sentinel_skill as s
import test_sentinel as fx   # reuse the deterministic fake chain + fixtures


def show(version, signal, address, action, max_risk=None):
    r = s.risk_check(address, action)
    keys = ", ".join(k for k in r["data"] if k not in ("is_contract",)) or "—"
    print(f"\n[{version}] {signal}")
    print(f"    risk_check({address[:10]}…, {action!r}) -> {r['verdict'].upper()} (score {r['score']})")
    for reason in r["reasons"]:
        print(f"       • {reason}")
    print(f"    data signals: {keys}")
    if max_risk:
        p = s.execution_plan(address, action, 100.0, max_risk=max_risk)
        gate = "APPROVED" if p["approved"] else "BLOCKED"
        print(f"    execution_plan(max_risk={max_risk!r}) -> {gate}: {p['suggested']}")


def banner(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


# (version, signal, address, action) — synthetic cases hit the fake chain.
SYNTHETIC = [
    ("v1", "input validation: malformed address", "not-an-address", "transfer"),
    ("v1", "EOA with history — clean", fx.A_EOA_USED, "transfer"),
    ("v1", "EOA brand-new / zero history (typo & poisoning guard)", fx.A_EOA_FRESH, "transfer"),
    ("v1", "action/target mismatch: approve to an EOA", fx.A_EOA_USED, "approve"),
    ("v1", "ERC-20 introspection: known token, transfer", fx.A_TOKEN, "transfer"),
    ("v1", "approval scrutiny: approve a real token", fx.A_TOKEN, "approve"),
    ("v1", "zero-supply token trap", fx.A_TOKEN_ZERO, "approve"),
    ("v1", "non-token contract (router), swap", fx.A_ROUTER, "swap"),
    ("v1", "tiny-bytecode stub", fx.A_STUB, "call"),
    ("v1", "EIP-1167 minimal proxy", fx.A_MINIMAL, "call"),
    ("v1", "EIP-1967 upgradeable proxy", fx.A_PROXY_TOKEN, "approve"),
    ("v2", "bytecode opcode analysis: SELFDESTRUCT", fx.A_SELFDEST, "approve"),
    ("v2", "bytecode opcode analysis: DELEGATECALL (non-proxy)", fx.A_DELEGATE, "call"),
    ("v2", "ownership: single EOA owner (centralization)", fx.A_OWNED, "transfer"),
    ("v2", "pausable: contract currently paused", fx.A_PAUSED, "transfer"),
]


def funded_wallet():
    try:
        import json
        return json.load(open(".wallet"))["address"]
    except Exception:
        return "0xda5B57Aee260B5245776a913eAD6C3dd902e20f0"


def run_synthetic():
    banner("SECTION A — every signal, deterministic (fake chain, no network)")
    orig = pharos.rpc
    pharos.rpc = fx.fake_rpc
    try:
        for version, signal, addr, action in SYNTHETIC:
            show(version, signal, addr, action)
    finally:
        pharos.rpc = orig


def run_live():
    banner("SECTION B — the SAME engine against real Pharos Atlantic (live RPC, slower)")
    if not pharos.chain_ok():
        print("  ! Atlantic RPC unreachable — skipping live section.")
        return
    from eth_account import Account
    cases = [
        ("v1", "real EOA: faucet-funded wallet", funded_wallet(), "transfer"),
        ("v1", "real EOA: a fresh, never-used address", Account.create().address, "transfer"),
        ("v1", "real contract (Multicall3), swap", "0xcA11bde05977b3631167028862bE2a173976CA11", "swap"),
        ("v1", "real contract (Multicall3), approve — gated", "0xcA11bde05977b3631167028862bE2a173976CA11", "approve"),
        ("v2", "real contract owned by a contract", "0x76c9cf548b4179f8901cda1f8623568b58215e62", "swap"),
    ]
    for version, signal, addr, action in cases:
        show(version, signal, addr, action, max_risk="safe" if action == "approve" else None)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "--all"
    if arg in ("--all", "--synthetic"):
        run_synthetic()
    if arg in ("--all", "--live"):
        run_live()
    banner("Tour complete. Edit the CASES lists or call s.risk_check(addr, action) to probe your own.")
