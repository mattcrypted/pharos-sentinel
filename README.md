# Sentinel — a pre-action on-chain risk gate for Pharos agents

Sentinel is a reusable **Agent Skill** that an AI agent calls **before it moves value** on
Pharos. Given a target address and an intended action, it reads the chain over RPC and returns
a risk **verdict** (`safe` / `caution` / `dangerous`), the **reasons** behind it, and a
**risk-bounded execution plan** the agent can act on directly. It is read-only — it advises,
it never signs or sends a transaction.

A pre-action risk check is the most-called primitive in any on-chain agent stack: every
transfer, swap, or approval is a place an agent can lose funds. Sentinel makes that check a
single, composable call.

## What makes it different

- **Read-only by design.** Sentinel never holds keys and never sends a transaction — the safest
  possible posture for a Skill that agents trust before moving money.
- **RPC-only, zero external infra.** No indexer, no third-party API, no keys, no database — just
  JSON-RPC against a Pharos node. That makes it portable, cheap, and easy to audit.
- **Not just a verdict — a plan.** `execution_plan` returns approve/block plus bounded sizing
  within the caller's risk tolerance, so the agent gets a decision, not just a score.
- **Real EVM depth.** Bytecode opcode analysis and proxy/ownership introspection, not surface
  heuristics (details below).

## Two tools

| Tool | Purpose |
|------|---------|
| `risk_check(address, action, amount_phrs?)` | Returns `{verdict, score, reasons[], data{}}`. |
| `execution_plan(address, action, amount_phrs, max_risk)` | Risk-gated: approve/block + bounded sizing within tolerance. |

`action` is one of `transfer` \| `swap` \| `approve` \| `call`.

## Risk signals (v2 — RPC-only)

- **Contract vs EOA**, and action/target mismatches (e.g. `approve` to a non-token, or to a wallet).
- **Proxy detection:** EIP-1167 minimal proxies and EIP-1967/1822 **upgradeable** proxies
  (the owner can swap the logic after you interact — a real rug vector).
- **Bytecode opcode analysis:** a proper opcode walk (stepping over PUSH immediates) that flags
  **SELFDESTRUCT** and **DELEGATECALL** used outside a known proxy pattern.
- **Ownership & upgrade-admin concentration:** `owner()` + the EIP-1967 admin slot, distinguishing
  an **EOA owner** (higher centralization risk) from a contract owner (likely multisig/timelock).
- **ERC-20 introspection:** `symbol` / `decimals` / `totalSupply`, with a zero-supply-trap flag.
- **Pausable state** (`paused()`), **tiny-bytecode stubs**, and brand-new / zero-history
  counterparties (a typo & address-poisoning guard).

The score is additive, so signals stack; the verdict is a band over it
(`>=70` dangerous, `>=35` caution, else safe).

## Use it two ways

**As an MCP server** — for MCP-capable agents:
```bash
pip install -r requirements.txt
python sentinel_skill.py          # stdio MCP server exposing risk_check + execution_plan
```

**As a framework Skill (SKILL.md) / CLI** — for Claude Code / OpenClaw / Codex style agents:
```bash
python sentinel_cli.py <address> <action>                    # verdict (JSON)
python sentinel_cli.py <address> approve --plan --max-risk safe   # risk-gated plan
```
The CLI exits `0` for safe/caution (or an approved plan) and `2` for dangerous/blocked, so a
shell or agent can branch on the exit status alone. See `SKILL.md` for the skill definition.

## Quickstart

```bash
python -m unittest test_sentinel   # 24 deterministic offline tests (no network)
python feature_tour.py --synthetic # walk every signal instantly (no network)
python demo_agent.py               # an agent drives the Skill over MCP against live Atlantic
python -c "import pharos_atlantic as p; print('chain_ok:', p.chain_ok())"
```

## Sample output

```text
$ python sentinel_cli.py 0x24f3cd306c85903ca2ccd0ee8dc1c74111151b23 call
{
  "verdict": "caution",
  "score": 35,
  "reasons": ["tiny bytecode (1 bytes) — likely a stub/trap rather than a working contract"],
  "data": { "is_contract": true, "code_size": 1 }
}
```

## Live on Pharos Atlantic

Sentinel integrates with **Pharos Atlantic Testnet** over live JSON-RPC:

- RPC `https://atlantic.dplabs-internal.com` · chainId **688689** · explorer
  `https://atlantic.pharosscan.xyz` · gas token **PHRS**

As a deployment check, a throwaway contract was deployed from a testnet wallet and then analyzed
by Sentinel live — the loop runs end to end on-chain:

- Deploy tx: [`0x67080c06…50dbf`](https://atlantic.pharosscan.xyz/tx/0x67080c061dbb423bbf25f84a1ad05b092137765a877091ee26a93c4bf9950dbf)
- Contract: [`0x24f3cd30…1b23`](https://atlantic.pharosscan.xyz/address/0x24f3cd306c85903ca2ccd0ee8dc1c74111151b23)
  — Sentinel flags it `caution — tiny bytecode stub` (the sample output above).

## Security posture

The Skill module (`sentinel_skill.py` + `pharos_atlantic.py`) is intentionally minimal and
auditable: **no shell execution, no filesystem access, no secrets or environment reads**, and all
outbound traffic is a single hardcoded Pharos RPC endpoint (declared in `skill.json`). It is
read-only and never sends a transaction.

## Files

| File | Role |
|------|------|
| `sentinel_skill.py` | MCP server — tools `risk_check`, `execution_plan` |
| `pharos_atlantic.py` | Pharos Atlantic config + dependency-free JSON-RPC read/introspection helpers |
| `sentinel_cli.py` | Thin CLI wrapper for SKILL.md / framework agents |
| `SKILL.md` | Skill definition for Claude Code / OpenClaw / Codex |
| `demo_agent.py` | Demo agent driving the Skill over a real MCP connection against live Atlantic |
| `feature_tour.py` | Guided walkthrough of every risk signal |
| `test_sentinel.py` | 24 offline, deterministic tests |
| `skill.json` | Skill manifest |

## License

MIT-0 (MIT No Attribution) — free to use, modify, and redistribute. See `LICENSE`.
