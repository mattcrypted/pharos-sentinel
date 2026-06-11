"""Thin CLI for the Sentinel risk Skill.

Lets a framework agent (Claude Code / OpenClaw / Codex — see SKILL.md) call the
risk check over the shell, in addition to the MCP server in sentinel_skill.py.

Usage:
    python sentinel_cli.py <address> [action] [--amount N] [--plan] [--max-risk safe|caution]

Examples:
    python sentinel_cli.py 0xcA11bde05977b3631167028862bE2a173976CA11 approve
    python sentinel_cli.py 0xAbc...123 swap --plan --amount 5 --max-risk safe

Prints a JSON object to stdout. Exit code is 0 for safe/caution (or an approved
plan), 2 for a dangerous verdict or a blocked plan — so shells/agents can branch
on the exit status without parsing JSON.
"""
from __future__ import annotations

import argparse
import json
import sys

import sentinel_skill as s

ACTIONS = ["transfer", "swap", "approve", "call"]


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Sentinel — pre-action on-chain risk check for Pharos Atlantic.")
    ap.add_argument("address", help="target contract or counterparty (0x + 40 hex)")
    ap.add_argument("action", nargs="?", default="transfer", choices=ACTIONS,
                    help="intended action (default: transfer)")
    ap.add_argument("--amount", type=float, default=0.0,
                    help="amount in PHRS (exposure context)")
    ap.add_argument("--plan", action="store_true",
                    help="return a risk-gated execution_plan instead of just the verdict")
    ap.add_argument("--max-risk", default="caution", choices=["safe", "caution"],
                    help="caller's risk tolerance for --plan (default: caution)")
    args = ap.parse_args()

    if args.plan:
        out = s.execution_plan(args.address, args.action, args.amount, max_risk=args.max_risk)
        blocked = out.get("approved") is False
    else:
        out = s.risk_check(args.address, args.action, args.amount)
        blocked = out.get("verdict") == "dangerous"

    print(json.dumps(out, indent=2))
    sys.exit(2 if blocked else 0)


if __name__ == "__main__":
    main()
