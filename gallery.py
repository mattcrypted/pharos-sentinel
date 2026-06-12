"""Live risk gallery — re-run Sentinel against the deployed Atlantic fixtures.

Read-only. Reads fixtures.json (public addresses), calls risk_check live for
each deployed contract, prints the verdict spectrum, and flags any drift from
the recorded expectation. End-to-end proof that the Skill classifies real
on-chain bytecode — not mocks — across the safe/caution/dangerous range.

    python gallery.py

Exits 0 if every exhibit matches its recorded verdict, 1 if any drifted.
"""
from __future__ import annotations

import json
import sys

import sentinel_skill as s

ICON = {"safe": "🟢", "caution": "🟡", "dangerous": "🔴", "unknown": "⚪"}


def main() -> int:
    cfg = json.load(open("fixtures.json"))
    print(f"Sentinel live risk gallery — {cfg['network']} (chainId {cfg['chainId']})")
    print(f"Reading real bytecode over RPC; no mocks.\n")

    drift = 0
    for ex in cfg["exhibits"]:
        r = s.risk_check(ex["address"], ex["action"])
        ok = r["verdict"] == ex["expect"]
        drift += not ok
        status = "ok" if ok else f"DRIFT (expected {ex['expect']})"
        icon = ICON.get(r["verdict"], "⚪")
        print(f"  {icon} {ex['name']:<16} {ex['action']:<9} "
              f"{r['verdict']:<9} score {r['score']:<3} [{status}]")
        print(f"       {ex['signal']}")
        print(f"       {cfg['explorer']}/address/{ex['address']}")

    print()
    if drift:
        print(f"✗ {drift} exhibit(s) drifted from their recorded verdict.")
        return 1
    print("✓ All exhibits match their recorded verdict.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
