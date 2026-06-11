---
name: sentinel
description: Pre-action on-chain risk gate for Pharos. Use BEFORE any transfer, swap, approve, or contract call on Pharos Atlantic to get a safe/caution/dangerous verdict with reasons, plus a risk-bounded execution plan. Trigger whenever an agent is about to move value, grant a token allowance, or interact with an unknown address or contract on Pharos.
license: MIT-0
---

# Sentinel — pre-action on-chain risk gate (Pharos)

Sentinel is a read-only safety check an agent runs **before** it moves value on
Pharos Atlantic. Given a target address and an intended action, it reads the
chain over RPC and returns a verdict, the reasons behind it, and a risk-gated
plan. It never sends a transaction itself — it only advises.

## When to use this skill

Invoke Sentinel before executing any of these on Pharos:
- `transfer` — sending PHRS or tokens to an address
- `swap` — routing a trade through a contract
- `approve` — granting a token spend allowance (the #1 drain vector)
- `call` — calling an unknown/just-discovered contract

If the verdict is `caution`, reduce size or seek confirmation. If `dangerous`,
do not proceed. Use `execution_plan` to get a ready-to-act decision.

## How to run it

```bash
# verdict only
python sentinel_cli.py <address> <action>

# risk-gated plan (approve/block + bounded sizing) within a tolerance
python sentinel_cli.py <address> <action> --plan --amount <PHRS> --max-risk <safe|caution>
```

Exit code is `0` for safe/caution (or an approved plan) and `2` for a dangerous
verdict or a blocked plan — so you can branch on the exit status alone.

It is also exposed as an MCP server (`python sentinel_skill.py`, tools
`risk_check` and `execution_plan`) for MCP-capable agents.

## Inputs

- `address` — target contract or counterparty (`0x` + 40 hex)
- `action` — `transfer` | `swap` | `approve` | `call` (default `transfer`)
- `--amount` — size in PHRS (exposure context, optional)
- `--max-risk` — caller tolerance for `--plan`: `safe` or `caution`

## Output

`risk_check` returns:
```json
{
  "verdict": "safe | caution | dangerous | unknown",
  "score": 0,
  "reasons": ["human-readable explanation", "..."],
  "data": { "is_contract": true, "code_size": 1, "...": "raw evidence" }
}
```
`execution_plan` returns `{ "approved": bool, "verdict": "...", "suggested": {...} }`.

## How to act on the verdict

- `safe` → proceed.
- `caution` → proceed with reduced size, or surface the `reasons` for confirmation.
- `dangerous` → do not proceed.
- `unknown` → could not validate the address or reach the chain; treat as blocking.

## What it checks (RPC-only, no external indexer or API)

Contract-vs-EOA; EIP-1167 minimal and EIP-1967/1822 upgradeable-proxy detection;
ERC-20 introspection (symbol/decimals/supply, zero-supply trap); bytecode opcode
analysis (SELFDESTRUCT / unguarded DELEGATECALL); ownership and upgrade-admin
concentration (`owner()` + EIP-1967 admin, EOA vs contract); pausable state;
tiny-bytecode stubs; and action/target mismatches (e.g. `approve` to a non-token
or to a wallet).

## Example

```bash
$ python sentinel_cli.py 0xcA11bde05977b3631167028862bE2a173976CA11 approve
# -> verdict "caution": approving a non-token contract; verify the target
```

Network: Pharos Atlantic Testnet (chainId 688689). Read-only; never signs or
sends a transaction.
