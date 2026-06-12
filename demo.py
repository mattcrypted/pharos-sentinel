"""demo.py — live on-chain demo driver for Sentinel (Pharos Atlantic).

Run one feature in front of an audience. Each subcommand narrates what it does,
performs a REAL on-chain transaction, and prints an explorer link. Self-contained:
it deploys the in-repo `fixtures/` via Foundry and signs with the throwaway testnet
key in .wallet. The Skill itself stays read-only — only this demo consumer signs.

    python demo.py gallery     # read-only: the 6-exhibit risk spectrum (no tx)
    python demo.py deploy      # deploy a malicious contract -> Sentinel flags it
    python demo.py upgrade     # upgrade-rug: swap a proxy's logic -> verdict escalates
    python demo.py pause       # pause a contract -> verdict escalates
    python demo.py transfer    # execution_plan sends real PHRS only when safe
    python demo.py x402        # pay-per-query risk check over x402
    python demo.py all         # run all five on-chain proofs + a tx summary

Each tx-producing command needs a funded .wallet; `gallery` is read-only.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

from eth_abi import encode as abi_encode
from eth_account import Account
from eth_utils import keccak, to_hex

import pharos_atlantic as pharos
import sentinel_skill as sentinel
import sentinel_x402 as x402

HERE = pathlib.Path(__file__).resolve().parent
PROJ = str(HERE / "fixtures")          # in-repo Foundry project
RPC = pharos.RPC_URL
EXPL = pharos.EXPLORER


def load_key():
    try:
        w = json.loads((HERE / ".wallet").read_text())
        return w["private_key"], w["address"]
    except Exception:
        return None, None


def banner(text: str) -> None:
    print(f"\n{'=' * 70}\n {text}\n{'=' * 70}")


def tx_link(h: str) -> str:
    return f"{EXPL}/tx/{h}"


def forge_create(pk: str, name: str, *cargs):
    cmd = ["forge", "create", f"src/Fixtures.sol:{name}", "--rpc-url", RPC,
           "--private-key", pk, "--broadcast", "--legacy", "--json"]
    if cargs:
        cmd += ["--constructor-args", *cargs]
    out = subprocess.run(cmd, cwd=PROJ, capture_output=True, text=True)
    j = json.loads(out.stdout)
    return j["deployedTo"], j["transactionHash"]


def send(pk: str, frm: str, to: str, data: bytes = b"", value: int = 0, gas: int = 300000) -> str:
    nonce = int(pharos.rpc("eth_getTransactionCount", [frm, "pending"]), 16)
    gp = int(pharos.rpc("eth_gasPrice", []), 16)
    tx = {"nonce": nonce, "to": to, "value": value, "gas": gas, "gasPrice": gp,
          "chainId": pharos.CHAIN_ID, "data": data}
    signed = Account.sign_transaction(tx, pk)
    raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
    txh = pharos.rpc("eth_sendRawTransaction", [to_hex(raw)])
    for _ in range(60):
        if pharos.rpc("eth_getTransactionReceipt", [txh]):
            return txh
        time.sleep(0.5)
    return txh


def verdict(addr: str, action: str = "call"):
    r = sentinel.risk_check(addr, action)
    print(f"    Sentinel: {r['verdict'].upper()} (score {r['score']})")
    for why in r["reasons"]:
        print(f"       • {why}")
    return r


def _backdoor() -> str:
    return next(e["address"] for e in json.loads((HERE / "fixtures.json").read_text())["exhibits"]
                if e["name"] == "Backdoor")


# --- features -----------------------------------------------------------------
def feat_deploy(pk, owner):
    banner("DEPLOY + DETECT — Sentinel flags freshly-deployed malicious bytecode")
    addr, txh = forge_create(pk, "Backdoor", owner)
    print(f"  deployed a Backdoor contract -> {addr}")
    print(f"  deploy tx: {tx_link(txh)}")
    print("  Sentinel reads the brand-new contract:")
    verdict(addr)
    return ("deploy + detect", txh)


def feat_upgrade(pk, owner):
    banner("UPGRADE ATTACK — Sentinel detects a live implementation swap")
    benign, _ = forge_create(pk, "LogicBenign")
    evil, _ = forge_create(pk, "LogicV1")
    proxy, _ = forge_create(pk, "MutableProxy", benign, owner)
    print(f"  proxy {proxy}  ->  benign logic")
    print("  BEFORE:")
    verdict(proxy)
    init = keccak(text="initialize(address)")[:4] + abi_encode(["address"], [owner])
    data = keccak(text="upgradeToAndCall(address,bytes)")[:4] + abi_encode(["address", "bytes"], [evil, init])
    txh = send(pk, owner, proxy, data)
    print(f"  owner sends upgradeToAndCall -> hostile logic")
    print(f"  upgrade tx: {tx_link(txh)}")
    print("  AFTER (same address):")
    verdict(proxy)
    return ("upgrade attack", txh)


def feat_pause(pk, owner):
    banner("PAUSE FLIP — Sentinel tracks live operational state")
    addr, _ = forge_create(pk, "Destructible", owner)
    print(f"  contract {addr}")
    print("  BEFORE:")
    verdict(addr)
    data = keccak(text="setPaused(bool)")[:4] + abi_encode(["bool"], [True])
    txh = send(pk, owner, addr, data, gas=120000)
    print(f"  operator sends setPaused(true)")
    print(f"  pause tx: {tx_link(txh)}")
    print("  AFTER (same address):")
    verdict(addr)
    return ("pause flip", txh)


def feat_transfer(pk, owner):
    banner("VALUE GATE — execution_plan moves real PHRS only when safe")
    plan = sentinel.execution_plan(owner, "transfer", 0.0005, max_risk="caution")
    print(f"  vetted counterparty -> {plan['verdict'].upper()} approved={plan['approved']}")
    txh = send(pk, owner, owner, value=int(0.0005 * 1e18), gas=21000)
    print(f"  VALUE MOVED: 0.0005 PHRS -> {tx_link(txh)}")
    bplan = sentinel.execution_plan(_backdoor(), "approve", 100.0, max_risk="caution")
    print(f"  Backdoor approve -> {bplan['verdict'].upper()} approved={bplan['approved']} -> NO TX SENT")
    return ("value gate", txh)


def feat_x402(pk, owner):
    banner("x402 PAID QUERY — pay-per-query risk assessment")
    threading.Thread(target=x402.serve, kwargs={"port": 4021}, daemon=True).start()
    time.sleep(0.6)
    path = f"{x402.RESOURCE}?address={_backdoor()}&action=call"

    def get(headers=None):
        req = urllib.request.Request("http://127.0.0.1:4021" + path, headers=headers or {})
        try:
            r = urllib.request.urlopen(req, timeout=25)
            return r.status, dict(r.headers), json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), json.loads(e.read())

    _, h, _ = get()
    acc = x402.decode_header(h["PAYMENT-REQUIRED"])["accepts"][0]
    print(f"  [402] pay {int(acc['maxAmountRequired']) / 1e18:g} {acc['asset']} to {acc['payTo']}")
    txh = send(pk, owner, acc["payTo"], value=int(acc["maxAmountRequired"]), gas=21000)
    print(f"  payment tx: {tx_link(txh)}")
    proof = x402.encode_header({"scheme": "exact-native", "network": x402.NETWORK,
                                "txHash": txh, "from": owner})
    _, _, b = get({"PAYMENT-SIGNATURE": proof})
    print(f"  [200] verdict {b['verdict'].upper()} (score {b['score']})")
    code, _, b = get({"PAYMENT-SIGNATURE": proof})
    print(f"  replay same payment -> [{code}] {b['error']}")
    return ("x402 paid query", txh)


def feat_gallery(*_):
    banner("RISK GALLERY — read-only spectrum over 6 live contracts (no tx)")
    import gallery
    gallery.main()
    return None


FEATURES = {"deploy": feat_deploy, "upgrade": feat_upgrade, "pause": feat_pause,
            "transfer": feat_transfer, "x402": feat_x402}


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "gallery":
        feat_gallery()
        return

    pk, owner = load_key()
    if not pk:
        print("no .wallet found — fund a testnet key to run the on-chain demos")
        return

    if cmd in FEATURES:
        FEATURES[cmd](pk, owner)
    elif cmd == "all":
        results = []
        for name in ["deploy", "upgrade", "pause", "transfer", "x402"]:
            results.append(FEATURES[name](pk, owner))
            time.sleep(1.5)  # pace the public RPC between features
        banner("5 ON-CHAIN TRANSACTIONS — one per feature")
        for label, txh in results:
            print(f"  {label:<18} {tx_link(txh)}")
    else:
        print(f"unknown command '{cmd}'. use: gallery|deploy|upgrade|pause|transfer|x402|all")


if __name__ == "__main__":
    main()
