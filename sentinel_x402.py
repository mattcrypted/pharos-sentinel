"""Sentinel over x402 — a pay-per-query HTTP gate for the risk Skill.

Pharos names "pay-per-query supplier/supply-chain risk assessment" as a flagship
x402 use case — which is exactly what Sentinel does. This wraps `risk_check` in
the documented Pharos x402 flow:

    GET /risk_check?address=..&action=..      -> 402 + PAYMENT-REQUIRED
    (client pays a micro-transfer on Atlantic, then retries)
    GET /risk_check  (PAYMENT-SIGNATURE: ..)  -> 200 + verdict + PAYMENT-RESPONSE

Settlement follows Pharos's *native* model (docs.pharos.xyz/developer-guide/x402):
"the client sends a micro-token transfer to a specified address -> the server
verifies the transaction -> the resource is returned." Sentinel verifies that
payment through the **same Foundry `cast` toolchain it uses for risk** — so the
server stays read-only and keyless (the client, not the server, sends value).
For full @x402 SDK-client interop via the EIP-3009 "exact" scheme, see X402.md.

Run:
    python sentinel_x402.py            # serves on 127.0.0.1:4021
    python x402_demo.py                # drives the full 402 -> pay -> 200 loop
"""
from __future__ import annotations

import base64
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import pharos_atlantic as pharos
import sentinel_skill as sentinel

NETWORK = f"eip155:{pharos.CHAIN_ID}"          # eip155:688689 (Pharos Atlantic)
PRICE_WEI = int(os.environ.get("SENTINEL_PRICE_WEI", 10**15))  # 0.001 PHRS / query
# Receiving address only — the server never holds a key and never sends a tx.
PAY_TO = os.environ.get("SENTINEL_PAY_TO", "0xda5B57Aee260B5245776a913eAD6C3dd902e20f0")
RESOURCE = "/risk_check"

# In-memory replay guard: each settlement tx unlocks exactly one query.
_CONSUMED: set[str] = set()


def payment_required(resource: str = RESOURCE) -> dict:
    """The x402 PaymentRequired object advertised in the 402 response."""
    return {
        "x402Version": 1,
        "accepts": [{
            "scheme": "exact-native",       # native micro-transfer settlement
            "network": NETWORK,
            "payTo": PAY_TO,
            "maxAmountRequired": str(PRICE_WEI),
            "asset": "PHRS",
            "resource": resource,
            "description": "Sentinel on-chain risk assessment (pay-per-query)",
            "mimeType": "application/json",
        }],
    }


def encode_header(obj: dict) -> str:
    return base64.b64encode(json.dumps(obj, separators=(",", ":")).encode()).decode()


def decode_header(value: str) -> dict:
    return json.loads(base64.b64decode(value))


def verify_payment(payload: dict, requirements: dict, seen: set) -> tuple[bool, str, str | None]:
    """Verify an x402 settlement on-chain, read-only, via the same RPC layer
    Sentinel uses for risk. Returns (ok, reason, payer_address)."""
    accepts = requirements["accepts"][0]
    if payload.get("network") != accepts["network"]:
        return False, "network mismatch", None
    txh = payload.get("txHash")
    if not txh:
        return False, "missing settlement txHash", None
    if txh.lower() in seen:
        return False, "payment already used (replay)", None
    try:
        tx = pharos.rpc("eth_getTransactionByHash", [txh])
    except Exception as e:
        return False, f"could not read settlement tx: {e}", None
    if not tx:
        return False, "settlement tx not found on Atlantic", None
    if (tx.get("to") or "").lower() != accepts["payTo"].lower():
        return False, "payment was not sent to payTo", None
    if int(tx.get("value", "0x0"), 16) < int(accepts["maxAmountRequired"]):
        return False, "underpaid: value below maxAmountRequired", None
    try:
        rcpt = pharos.rpc("eth_getTransactionReceipt", [txh])
    except Exception as e:
        return False, f"could not read receipt: {e}", None
    if not rcpt or rcpt.get("status") != "0x1":
        return False, "settlement not yet confirmed", None
    seen.add(txh.lower())
    return True, "ok", tx.get("from")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):  # keep the server quiet for clean demos
        pass

    def _send(self, code: int, body: dict, extra_headers: dict | None = None):
        payload = json.dumps(body, indent=2).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != RESOURCE:
            self._send(404, {"error": f"no resource at {parsed.path}"})
            return

        q = parse_qs(parsed.query)
        address = (q.get("address") or [""])[0]
        action = (q.get("action") or ["transfer"])[0]
        amount = float((q.get("amount") or ["0"])[0] or 0)

        req = payment_required()
        sig = self.headers.get("PAYMENT-SIGNATURE")
        if not sig:
            # 402: advertise what the client must pay.
            self._send(402, {"error": "payment required", **req},
                       {"PAYMENT-REQUIRED": encode_header(req)})
            return

        try:
            payload = decode_header(sig)
        except Exception:
            self._send(402, {"error": "malformed PAYMENT-SIGNATURE", **req},
                       {"PAYMENT-REQUIRED": encode_header(req)})
            return

        ok, reason, payer = verify_payment(payload, req, _CONSUMED)
        if not ok:
            self._send(402, {"error": f"payment verification failed: {reason}", **req},
                       {"PAYMENT-REQUIRED": encode_header(req)})
            return

        # Paid and verified — do the work and return the verdict.
        verdict = sentinel.risk_check(address, action, amount)
        receipt = {"network": NETWORK, "transaction": payload.get("txHash"), "payer": payer}
        self._send(200, verdict, {"PAYMENT-RESPONSE": encode_header(receipt)})


def serve(host: str = "127.0.0.1", port: int = 4021) -> None:
    httpd = HTTPServer((host, port), Handler)
    print(f"Sentinel x402 gate on http://{host}:{port}{RESOURCE} "
          f"· {PRICE_WEI / 1e18:g} PHRS/query · payTo {PAY_TO}")
    httpd.serve_forever()


if __name__ == "__main__":
    serve()
