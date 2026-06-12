"""Guarded transfer — Sentinel's execution_plan governs REAL value movement.

Unlike demo_agent.py (which narrates the gate), this actually SENDS a PHRS
transfer when Sentinel approves, and withholds it when Sentinel blocks. The
Skill itself stays read-only — only this consumer signs and sends, using the
throwaway testnet key in .wallet.

Run:
    python guarded_transfer.py
"""
from __future__ import annotations

import json
import time

from eth_account import Account
from eth_utils import to_hex

import pharos_atlantic as pharos
import sentinel_skill as sentinel


def load_wallet():
    try:
        w = json.loads(open(".wallet").read())
        return w["private_key"], w["address"]
    except Exception:
        return None, None


def send_phrs(pk: str, frm: str, to: str, value_wei: int) -> str:
    nonce = int(pharos.rpc("eth_getTransactionCount", [frm, "pending"]), 16)
    gas_price = int(pharos.rpc("eth_gasPrice", []), 16)
    tx = {"nonce": nonce, "to": to, "value": value_wei, "gas": 21000,
          "gasPrice": gas_price, "chainId": pharos.CHAIN_ID, "data": b""}
    signed = Account.sign_transaction(tx, pk)
    raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
    txh = pharos.rpc("eth_sendRawTransaction", [to_hex(raw)])
    for _ in range(60):
        if pharos.rpc("eth_getTransactionReceipt", [txh]):
            return txh
        time.sleep(0.5)
    return txh


def guarded(pk: str, frm: str, title: str, target: str, action: str,
            amount: float, max_risk: str = "caution") -> None:
    print(f"\n>>> {title}")
    print(f"    target={target}  action={action}  amount={amount} PHRS  tolerance={max_risk}")
    plan = sentinel.execution_plan(target, action, amount, max_risk=max_risk)
    print(f"    Sentinel: {plan['verdict'].upper()} -> approved={plan['approved']}")
    if plan["approved"]:
        amt = plan["suggested"]["amount_phrs"]
        txh = send_phrs(pk, frm, target, int(amt * 1e18))
        print(f"    VALUE MOVED: sent {amt} PHRS  ->  tx {txh}")
    else:
        print(f"    NO TX SENT: {plan['suggested']['note']}")


def main() -> None:
    pk, frm = load_wallet()
    if not pk:
        print("no .wallet found — fund a testnet key to run the value-moving demo")
        return

    backdoor = next(e["address"] for e in json.load(open("fixtures.json"))["exhibits"]
                    if e["name"] == "Backdoor")

    print("=" * 68)
    print("Sentinel execution_plan governs real value (Pharos Atlantic)")
    print("=" * 68)

    # SAFE: a vetted counterparty (the treasury itself) -> approved -> tx is sent.
    guarded(pk, frm, "Pay a vetted counterparty", frm, "transfer", 0.0005)
    # DANGEROUS: the live Backdoor fixture -> blocked -> no value leaves the wallet.
    guarded(pk, frm, "Approve the Backdoor contract", backdoor, "approve", 100.0)

    print("\n" + "=" * 68)
    print("Only the approved action moved value; the dangerous one was blocked.")
    print("=" * 68)


if __name__ == "__main__":
    main()
