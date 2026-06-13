"""Offline, deterministic tests for the Sentinel Skill risk engine.

No network, no Foundry: we monkeypatch `pharos_atlantic._cast` (the Foundry `cast`
seam) for the risk engine and `pharos_atlantic.rpc` for the x402 tx/receipt reads,
so the tests pin the verdict logic exactly and run anywhere (incl. a clean CI).

Run:  python -m unittest -v test_sentinel
"""
from __future__ import annotations

import unittest

import pharos_atlantic as pharos
import sentinel_skill as s
import sentinel_x402 as x402


# --- fake-chain encoders -------------------------------------------------------
def abi_uint(n: int) -> str:
    return "0x" + format(n, "064x")


def abi_string(text: str) -> str:
    b = text.encode()
    length = format(len(b), "064x")
    body = b.hex()
    body = body.ljust(((len(body) + 63) // 64) * 64, "0") if body else ""
    return "0x" + format(32, "064x") + length + body


def word_addr(addr: str) -> str:
    return "0x" + addr[2:].rjust(64, "0")


ZERO_WORD = "0x" + "0" * 64

# A made-up but well-formed address per fixture (content doesn't matter offline).
A_EOA_FRESH   = "0x1111111111111111111111111111111111111111"
A_EOA_USED    = "0x2222222222222222222222222222222222222222"
A_TOKEN       = "0x3333333333333333333333333333333333333333"
A_TOKEN_ZERO  = "0x4444444444444444444444444444444444444444"
A_PROXY_TOKEN = "0x5555555555555555555555555555555555555555"
A_MINIMAL     = "0x6666666666666666666666666666666666666666"
A_STUB        = "0x7777777777777777777777777777777777777777"
A_ROUTER      = "0x8888888888888888888888888888888888888888"
A_IMPL        = "0x9999999999999999999999999999999999999999"
A_SELFDEST    = "0x" + "a" * 40
A_DELEGATE    = "0x" + "b" * 40
A_OWNED       = "0x" + "c" * 40
A_PAUSED      = "0x" + "d" * 40

BIG_CODE = "0x60806040" + "ab" * 400  # ~800 bytes, looks like a real contract
MINIMAL_CODE = "0x363d3d373d3d3d363d73" + A_IMPL[2:] + "5af43d82803e903d91602b57fd5bf3"
STUB_CODE = "0x6001"  # 2 bytes
SELFDEST_CODE = "0x60016000ff" + "ab" * 100  # PUSH1 PUSH1 SELFDESTRUCT + padding (~105 bytes)
DELEGATE_CODE = "0x60016000f4" + "ab" * 100  # PUSH1 PUSH1 DELEGATECALL + padding (~105 bytes)

# token call-tables
_TOKEN_CALLS = {
    pharos.SEL_TOTAL_SUPPLY: abi_uint(1_000_000 * 10**18),
    pharos.SEL_DECIMALS: abi_uint(18),
    pharos.SEL_SYMBOL: abi_string("USDC"),
    pharos.SEL_NAME: abi_string("USD Coin"),
}
_TOKEN_ZERO_CALLS = dict(_TOKEN_CALLS, **{pharos.SEL_TOTAL_SUPPLY: abi_uint(0)})

CHAIN = {
    A_EOA_FRESH: {"code": "0x", "nonce": 0, "balance": 0},
    A_EOA_USED: {"code": "0x", "nonce": 7, "balance": 5 * 10**18},
    A_TOKEN: {"code": BIG_CODE, "calls": _TOKEN_CALLS},
    A_TOKEN_ZERO: {"code": BIG_CODE, "calls": _TOKEN_ZERO_CALLS},
    A_PROXY_TOKEN: {"code": BIG_CODE, "calls": _TOKEN_CALLS,
                    "storage": {pharos.EIP1967_IMPL_SLOT.lower(): word_addr(A_IMPL)}},
    A_MINIMAL: {"code": MINIMAL_CODE},
    A_STUB: {"code": STUB_CODE},
    A_ROUTER: {"code": BIG_CODE},  # real contract, but answers no token calls
    A_SELFDEST: {"code": SELFDEST_CODE},
    A_DELEGATE: {"code": DELEGATE_CODE},
    A_OWNED: {"code": BIG_CODE,
              "calls": dict(_TOKEN_CALLS, **{pharos.SEL_OWNER: word_addr(A_EOA_USED)})},
    A_PAUSED: {"code": BIG_CODE, "calls": {pharos.SEL_PAUSED: abi_uint(1)}},
}


def fake_cast(args: list):
    """Stand-in for `pharos._cast`: answers Foundry `cast` subcommands from the
    fake chain. cast prints chain-id / nonce / balance in DECIMAL, code / call /
    storage as 0x-hex — matched here so the parsers exercise real formats."""
    cmd = args[0]
    if cmd == "chain-id":
        return str(pharos.CHAIN_ID)
    if cmd == "call":
        to, data = args[1], args[2]
        return CHAIN.get(to, {}).get("calls", {}).get(data, "0x")
    addr = args[1]
    spec = CHAIN.get(addr, {})
    if cmd == "code":
        return spec.get("code", "0x")
    if cmd == "nonce":
        return str(spec.get("nonce", 0))
    if cmd == "balance":
        return str(spec.get("balance", 0))
    if cmd == "storage":
        return spec.get("storage", {}).get(args[2].lower(), ZERO_WORD)
    raise AssertionError(f"unexpected cast {args}")


class RiskCheckTests(unittest.TestCase):
    def setUp(self):
        self._orig = pharos._cast
        pharos._cast = fake_cast

    def tearDown(self):
        pharos._cast = self._orig

    def verdict(self, *a, **k):
        return s.risk_check(*a, **k)["verdict"]

    # --- input / connectivity ---
    def test_invalid_address(self):
        r = s.risk_check("not-an-address")
        self.assertEqual(r["verdict"], "unknown")
        self.assertEqual(r["score"], -1)

    def test_rpc_unreachable(self):
        def boom(args):
            if args[0] == "chain-id":
                raise RuntimeError("down")
            return fake_cast(args)
        pharos._cast = boom
        self.assertEqual(self.verdict(A_TOKEN), "unknown")

    # --- EOAs ---
    def test_fresh_eoa_transfer_is_caution(self):
        self.assertEqual(self.verdict(A_EOA_FRESH, "transfer"), "caution")

    def test_used_eoa_transfer_is_safe(self):
        self.assertEqual(self.verdict(A_EOA_USED, "transfer"), "safe")

    def test_approve_to_eoa_is_caution(self):
        self.assertEqual(self.verdict(A_EOA_USED, "approve"), "caution")

    # --- tokens ---
    def test_token_transfer_is_safe_with_metadata(self):
        r = s.risk_check(A_TOKEN, "transfer")
        self.assertEqual(r["verdict"], "safe")
        self.assertEqual(r["data"]["erc20"]["symbol"], "USDC")
        self.assertEqual(r["data"]["erc20"]["decimals"], 18)

    def test_known_token_approve_is_safe(self):
        # softened: approving a plain, healthy, non-proxy token is a normal action
        r = s.risk_check(A_TOKEN, "approve")
        self.assertEqual(r["verdict"], "safe")
        self.assertTrue(any("finite cap" in why for why in r["reasons"]))

    def test_non_token_approve_is_caution(self):
        # approving something that is not a healthy token keeps strong friction
        self.assertEqual(self.verdict(A_ROUTER, "approve"), "caution")

    def test_zero_supply_token_approve_is_caution(self):
        self.assertEqual(self.verdict(A_TOKEN_ZERO, "approve"), "caution")

    # --- proxies ---
    def test_upgradeable_proxy_approve_is_caution(self):
        r = s.risk_check(A_PROXY_TOKEN, "approve")
        self.assertEqual(r["verdict"], "caution")
        self.assertEqual(r["data"]["upgradeable_impl"].lower(), A_IMPL.lower())

    def test_upgradeable_zero_supply_approve_is_dangerous(self):
        # combine upgradeable token + zero supply + approve
        CHAIN[A_PROXY_TOKEN]["calls"] = _TOKEN_ZERO_CALLS
        try:
            self.assertEqual(self.verdict(A_PROXY_TOKEN, "approve"), "dangerous")
        finally:
            CHAIN[A_PROXY_TOKEN]["calls"] = _TOKEN_CALLS

    def test_minimal_proxy_flagged_but_safe_for_call(self):
        r = s.risk_check(A_MINIMAL, "call")
        self.assertTrue(r["data"].get("minimal_proxy"))
        self.assertEqual(r["verdict"], "safe")  # 10 < caution band

    # --- stubs / routers ---
    def test_tiny_stub_call_is_caution(self):
        self.assertEqual(self.verdict(A_STUB, "call"), "caution")

    def test_tiny_stub_approve_is_dangerous(self):
        self.assertEqual(self.verdict(A_STUB, "approve"), "dangerous")

    def test_router_swap_is_safe(self):
        self.assertEqual(self.verdict(A_ROUTER, "swap"), "safe")

    def test_router_approve_is_caution(self):
        self.assertEqual(self.verdict(A_ROUTER, "approve"), "caution")

    # --- v2 signals: opcode analysis / ownership / pausable ---
    def test_selfdestruct_approve_is_dangerous(self):
        r = s.risk_check(A_SELFDEST, "approve")
        self.assertTrue(r["data"].get("selfdestruct"))
        self.assertEqual(r["verdict"], "dangerous")

    def test_delegatecall_flagged_when_not_proxy(self):
        r = s.risk_check(A_DELEGATE, "call")
        self.assertTrue(r["data"].get("delegatecall"))

    def test_minimal_proxy_delegatecall_not_double_flagged(self):
        # a minimal proxy legitimately uses DELEGATECALL — don't double-penalize it
        r = s.risk_check(A_MINIMAL, "call")
        self.assertTrue(r["data"].get("minimal_proxy"))
        self.assertNotIn("delegatecall", r["data"])

    def test_owner_eoa_flagged_but_transfer_safe(self):
        r = s.risk_check(A_OWNED, "transfer")
        self.assertEqual(r["data"].get("owner"), A_EOA_USED)
        self.assertEqual(r["verdict"], "safe")  # +10 alone stays under the caution band

    def test_paused_contract_flagged(self):
        r = s.risk_check(A_PAUSED, "transfer")
        self.assertTrue(r["data"].get("paused"))


class ExecutionPlanTests(unittest.TestCase):
    def setUp(self):
        self._orig = pharos._cast
        pharos._cast = fake_cast

    def tearDown(self):
        pharos._cast = self._orig

    def test_safe_action_approved_full_size(self):
        p = s.execution_plan(A_TOKEN, "transfer", 10.0, max_risk="caution")
        self.assertTrue(p["approved"])
        self.assertEqual(p["suggested"]["amount_phrs"], 10.0)

    def test_caution_action_approved_half_size(self):
        p = s.execution_plan(A_ROUTER, "approve", 10.0, max_risk="caution")
        self.assertTrue(p["approved"])
        self.assertEqual(p["suggested"]["amount_phrs"], 5.0)

    def test_dangerous_action_blocked(self):
        p = s.execution_plan(A_STUB, "approve", 10.0, max_risk="caution")
        self.assertFalse(p["approved"])
        self.assertEqual(p["suggested"]["action"], "BLOCK")

    def test_caution_blocked_when_tolerance_safe(self):
        p = s.execution_plan(A_ROUTER, "approve", 10.0, max_risk="safe")
        self.assertFalse(p["approved"])


class X402Tests(unittest.TestCase):
    """The x402 paid-call gate: envelope encoding + on-chain payment verification.
    Verification is mocked at the RPC layer, exactly as the risk engine is."""

    def setUp(self):
        self._orig = pharos.rpc

    def tearDown(self):
        pharos.rpc = self._orig

    @staticmethod
    def _chain_with_tx(to, value, *, found=True, mined=True, status="0x1"):
        def rpc(method, params):
            if method == "eth_getTransactionByHash":
                return {"to": to, "from": "0xpayer", "value": hex(value)} if found else None
            if method == "eth_getTransactionReceipt":
                return {"status": status} if mined else None
            raise AssertionError(f"unexpected rpc {method}")
        return rpc

    def _proof(self, txh="0xabc", network=None):
        return {"network": network or x402.NETWORK, "txHash": txh}

    def test_header_roundtrip(self):
        obj = {"x402Version": 1, "accepts": [{"scheme": "exact-native"}]}
        self.assertEqual(x402.decode_header(x402.encode_header(obj)), obj)

    def test_payment_required_shape(self):
        acc = x402.payment_required()["accepts"][0]
        self.assertEqual(acc["network"], f"eip155:{pharos.CHAIN_ID}")
        self.assertEqual(acc["payTo"], x402.PAY_TO)
        self.assertEqual(int(acc["maxAmountRequired"]), x402.PRICE_WEI)

    def test_verify_ok(self):
        pharos.rpc = self._chain_with_tx(x402.PAY_TO, x402.PRICE_WEI)
        ok, _, payer = x402.verify_payment(self._proof(), x402.payment_required(), set())
        self.assertTrue(ok)
        self.assertEqual(payer, "0xpayer")

    def test_verify_underpaid(self):
        pharos.rpc = self._chain_with_tx(x402.PAY_TO, x402.PRICE_WEI - 1)
        ok, reason, _ = x402.verify_payment(self._proof(), x402.payment_required(), set())
        self.assertFalse(ok)
        self.assertIn("underpaid", reason)

    def test_verify_wrong_recipient(self):
        pharos.rpc = self._chain_with_tx("0xdeadbeef", x402.PRICE_WEI)
        ok, reason, _ = x402.verify_payment(self._proof(), x402.payment_required(), set())
        self.assertFalse(ok)
        self.assertIn("payTo", reason)

    def test_verify_network_mismatch(self):
        ok, reason, _ = x402.verify_payment(
            self._proof(network="eip155:1"), x402.payment_required(), set())
        self.assertFalse(ok)
        self.assertIn("network", reason)

    def test_verify_tx_not_found(self):
        pharos.rpc = self._chain_with_tx(x402.PAY_TO, x402.PRICE_WEI, found=False)
        ok, reason, _ = x402.verify_payment(self._proof(), x402.payment_required(), set())
        self.assertFalse(ok)
        self.assertIn("not found", reason)

    def test_verify_unconfirmed(self):
        pharos.rpc = self._chain_with_tx(x402.PAY_TO, x402.PRICE_WEI, mined=False)
        ok, reason, _ = x402.verify_payment(self._proof(), x402.payment_required(), set())
        self.assertFalse(ok)
        self.assertIn("confirmed", reason)

    def test_verify_replay_rejected(self):
        pharos.rpc = self._chain_with_tx(x402.PAY_TO, x402.PRICE_WEI)
        seen = set()
        ok1, _, _ = x402.verify_payment(self._proof("0xAbC"), x402.payment_required(), seen)
        ok2, reason, _ = x402.verify_payment(self._proof("0xAbC"), x402.payment_required(), seen)
        self.assertTrue(ok1)
        self.assertFalse(ok2)
        self.assertIn("replay", reason)


if __name__ == "__main__":
    unittest.main()
