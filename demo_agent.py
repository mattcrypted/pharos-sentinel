"""Demo agent — drives the Sentinel Skill over a REAL MCP connection.

This is the end-to-end proof for the submission: it launches `sentinel_skill.py`
as a stdio MCP server (exactly how a Pharos agent would consume the Skill),
discovers its tools, then plays a trading/ops agent that calls Sentinel BEFORE
each value-moving action and obeys the verdict — proceed, shrink, or block.

Every address below is read live from Pharos Atlantic Testnet; no mocking.

Run:
    pip install -r requirements.txt
    python demo_agent.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

from eth_account import Account

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# --- live Pharos Atlantic addresses the demo reasons about --------------------
MULTICALL3 = "0xcA11bde05977b3631167028862bE2a173976CA11"  # canonical, deployed on Atlantic


def funded_wallet() -> str:
    """The throwaway demo wallet (faucet-funded), if present; else a placeholder."""
    try:
        with open(".wallet") as f:
            return json.load(f)["address"]
    except Exception:
        return "0xda5B57Aee260B5245776a913eAD6C3dd902e20f0"


def _unwrap(result) -> dict:
    """Tool results come back as a JSON TextContent; parse it to a dict."""
    for block in result.content:
        text = getattr(block, "text", None)
        if text:
            return json.loads(text)
    return result.structuredContent or {}


def banner(text: str) -> None:
    print(f"\n{'=' * 68}\n{text}\n{'=' * 68}")


async def call(session: ClientSession, tool: str, **args) -> dict:
    return _unwrap(await session.call_tool(tool, args))


async def guarded_action(session, title, address, action, amount, max_risk="caution"):
    """How a real agent would use Sentinel: risk_check for context, then
    execution_plan as the gate, then act on the plan."""
    print(f"\n>>> AGENT INTENT: {title}")
    print(f"    target={address}  action={action}  amount={amount} PHRS  tolerance={max_risk}")

    rc = await call(session, "risk_check", address=address, action=action, amount_phrs=amount)
    print(f"    Sentinel verdict: {rc['verdict'].upper()} (score {rc['score']})")
    for reason in rc["reasons"]:
        print(f"       • {reason}")

    plan = await call(session, "execution_plan", address=address, action=action,
                      amount_phrs=amount, max_risk=max_risk)
    if plan["approved"]:
        sug = plan["suggested"]
        print(f"    DECISION: PROCEED with {sug['amount_phrs']} PHRS ({sug['note']}).")
    else:
        print(f"    DECISION: BLOCKED — {plan['suggested']['note']}. Agent halts this action.")


async def main() -> None:
    server = StdioServerParameters(command=sys.executable, args=["sentinel_skill.py"],
                                   cwd=os.getcwd())
    banner("Sentinel Skill — live MCP demo (Pharos Atlantic Testnet)")
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = (await session.list_tools()).tools
            print("Connected to Sentinel over MCP. Tools exposed:")
            for t in tools:
                print(f"   - {t.name}: {(t.description or '').splitlines()[0]}")

            banner("Agent runs its pre-flight risk checks before moving value")
            wallet = funded_wallet()
            fresh = Account.create().address  # a brand-new, never-used address

            # 1) paying a known, funded counterparty -> should clear
            await guarded_action(session, "Pay a known counterparty",
                                 wallet, "transfer", 5.0)

            # 2) paying a brand-new address (typo / address-poisoning risk) -> caution
            await guarded_action(session, "Pay a never-seen address",
                                 fresh, "transfer", 5.0)

            # 3) approving a non-token contract -> caution (approvals are the #1 drain vector)
            await guarded_action(session, "Approve a contract to spend tokens",
                                 MULTICALL3, "approve", 100.0)

            # 4) approving the same contract under a strict (safe-only) tolerance -> blocked
            await guarded_action(session, "Approve under strict safe-only policy",
                                 MULTICALL3, "approve", 100.0, max_risk="safe")

            # 5) routing a swap through a known contract -> clears
            await guarded_action(session, "Swap through a known router",
                                 MULTICALL3, "swap", 5.0)

    banner("Demo complete — every action was gated by Sentinel over MCP.")


if __name__ == "__main__":
    asyncio.run(main())
