"""x402 demo — drive Sentinel's pay-per-query gate end to end on Atlantic.

Launches the x402 server (sentinel_x402.py) in a thread, then plays the client:
  1. request a risk check unpaid           -> 402 + PAYMENT-REQUIRED
  2. pay the advertised micro-transfer on Pharos Atlantic
  3. retry with PAYMENT-SIGNATURE           -> 200 + verdict + PAYMENT-RESPONSE
  4. replay the same payment                -> 402 (replay guard)

The server is read-only (it verifies the payment over RPC). Only this client
signs and sends value, using the throwaway testnet key in .wallet.

Run:
    python x402_demo.py
"""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request

from eth_account import Account
from eth_utils import to_hex

import pharos_atlantic as pharos
import sentinel_x402 as x402

BASE = "http://127.0.0.1:4021"


def http_get(path: str, headers: dict | None = None):
    req = urllib.request.Request(BASE + path, headers=headers or {})
    try:
        r = urllib.request.urlopen(req, timeout=25)
        return r.status, dict(r.headers), json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), json.loads(e.read())


def wait_for_server():
    for _ in range(80):
        try:
            urllib.request.urlopen(BASE + x402.RESOURCE, timeout=5)
            return
        except urllib.error.HTTPError:
            return  # 402/404 means it's up
        except urllib.error.URLError:
            time.sleep(0.1)


def load_wallet():
    try:
        w = json.loads(open(".wallet").read())
        return w["private_key"], w["address"]
    except Exception:
        return None, None


def pay(pk: str, frm: str, to: str, value_wei: int) -> str:
    """Send a native PHRS micro-transfer and wait for its receipt. Returns txHash."""
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


def banner(text: str) -> None:
    print(f"\n{'=' * 68}\n{text}\n{'=' * 68}")


def main() -> None:
    threading.Thread(target=x402.serve, kwargs={"port": 4021}, daemon=True).start()
    wait_for_server()
    banner("Sentinel x402 gate — pay-per-query risk assessment (Pharos Atlantic)")

    # A genuinely risky target from the live gallery (the Backdoor fixture).
    target = "0x75fb8b091A7A88bAF14F23Eac2F33962A4Cdd35D"
    path = f"{x402.RESOURCE}?address={target}&action=call"

    print("\n[1] Request a risk check WITHOUT paying:")
    code, headers, body = http_get(path)
    req = x402.decode_header(headers["PAYMENT-REQUIRED"])
    accepts = req["accepts"][0]
    print(f"    <- HTTP {code} {body['error']}")
    print(f"       PAYMENT-REQUIRED: pay {int(accepts['maxAmountRequired'])/1e18:g} "
          f"{accepts['asset']} to {accepts['payTo']} on {accepts['network']}")

    pk, frm = load_wallet()
    if not pk:
        print("\n    (no .wallet found — stopping here; fund a testnet key to complete the paid call)")
        return

    print(f"\n[2] Pay the micro-transfer from {frm}:")
    txh = pay(pk, frm, accepts["payTo"], int(accepts["maxAmountRequired"]))
    print(f"    -> settled on Atlantic, tx {txh}")

    print("\n[3] Retry WITH the payment proof (PAYMENT-SIGNATURE):")
    proof = x402.encode_header({"scheme": "exact-native", "network": x402.NETWORK,
                                "txHash": txh, "from": frm})
    code, headers, body = http_get(path, {"PAYMENT-SIGNATURE": proof})
    receipt = x402.decode_header(headers["PAYMENT-RESPONSE"])
    print(f"    <- HTTP {code}: verdict {body['verdict'].upper()} (score {body['score']})")
    for reason in body["reasons"]:
        print(f"         • {reason}")
    print(f"       PAYMENT-RESPONSE: settled tx {receipt['transaction']}")

    print("\n[4] Replay the SAME payment (should be rejected):")
    code, headers, body = http_get(path, {"PAYMENT-SIGNATURE": proof})
    print(f"    <- HTTP {code}: {body['error']}")

    banner("Demo complete — one on-chain micro-payment, one verified risk verdict.")


if __name__ == "__main__":
    main()
