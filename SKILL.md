---
name: sentinel
description: >
  Pre-action on-chain RISK GATE for Pharos. Read-only — call it BEFORE any
  value-moving action to get a safe/caution/dangerous verdict with reasons and a
  risk-bounded execution plan. Invoke whenever the user is about to transfer,
  swap, approve a token allowance, deploy, run an airdrop, or interact with an
  unknown address or contract on Pharos ("is this safe?", "risk check", "should I
  approve this?", "is this token a trap?"). Designed to run as the risk pre-check
  in front of the Pharos Skill Engine's write operations. Reads Pharos Atlantic
  over RPC; never signs or sends a transaction.
version: 0.1.0
requires:
  anyBins:
  - python3
  - python
---

# Sentinel — Pre-Action Risk Gate for Pharos

A read-only safety check an agent runs BEFORE it moves value on Pharos. Given a
target address and an intended action, Sentinel reads the chain over RPC and
returns a verdict (`safe` / `caution` / `dangerous`), the reasons behind it, and
a risk-gated plan. It never signs or sends a transaction — it only advises and
blocks.

## Prerequisites

1. **Python 3** (MANDATORY for the risk check):
   - The Agent runs the gate via `python sentinel_cli.py <address> <action>`.
   - Verify with `python --version` (or `python3 --version`). No other runtime is required to assess risk.
   - The risk check uses only the Python standard library plus a single hardcoded Pharos RPC endpoint. **No Foundry, no private key, and no API key are needed to assess risk.**
2. **(Optional) Foundry + `eth-account`** — only for the bundled on-chain *demos*
   (`demo.py`, `guarded_transfer.py`, `x402_demo.py`) that actually move value. The risk gate itself never needs them.

## Network Configuration

Network information is stored in `assets/networks.json`.

- **Default Network**: Atlantic testnet (`atlantic-testnet`), chainId `688689`. Used when the user does not specify a network.
- **Usage**: read the target network's `rpcUrl` from `assets/networks.json`. The field names match the Pharos Skill Engine, so Sentinel and the engine share one network config.

```bash
# Example: reading network configuration
RPC_URL=$(jq -r '.networks[] | select(.name=="atlantic-testnet") | .rpcUrl' assets/networks.json)
```

## Capability Index

Load `references/sentinel.md` for full command templates.

| User Need | Capability | Detailed Instructions |
|-----------|------------|----------------------|
| "Is this address / contract safe?" · "check risk before I send / approve / swap / deploy" · "is this token a trap?" | Sentinel risk gate (read-only RPC) — verdict + reasons | → `references/sentinel.md#risk-check-pre-action-gate` |
| "Is it safe to approve this spender?" · "will this drain me?" | Risk check with `action=approve` | → `references/sentinel.md#risk-check-pre-action-gate` |
| "How much should I send to X?" · "give me a safe plan" | Risk-gated execution plan (approve/block + bounded size) | → `references/sentinel.md#risk-gated-execution-plan` |
| "Add a safety pre-check before any transaction" | Sentinel as a Write-Operation pre-check (Step 0) | → `references/sentinel.md#use-as-a-write-operation-pre-check` |

## General Error Handling

| Error Scenario | Signature | Handling |
|---------------|-----------|----------|
| Invalid address format | verdict `unknown` — "not a valid 0x-prefixed 20-byte address" | Prompt to check the address (0x + 40 hex characters) |
| RPC unreachable | verdict `unknown` — "could not reach Pharos Atlantic RPC" | Retry; confirm `rpcUrl` in `assets/networks.json` |
| Dangerous verdict | exit code `2` | STOP the pending write; surface the `reasons` to the user |
| Caution verdict | score `>= 35` | Surface the `reasons`; reduce size or ask the user to confirm |

## Security Reminders

- **Read-only by design.** Sentinel performs only RPC *reads* (`eth_getCode`, `eth_call`, `eth_getStorageAt`, …). It holds no private key and NEVER signs or sends a transaction — the safest posture for a skill an agent trusts before moving money.
- **No secrets, no shell execution, no filesystem writes** in the risk path; all outbound traffic is the single declared Pharos RPC endpoint.
- It only ever *blocks* an action (exit `2`); it never executes one.

## Risk Pre-Check (run in front of the engine's Write Operation Pre-checks)

Sentinel is designed to run as **Step 0**, before the Pharos Skill Engine's write
pre-checks (private key → address → network → balance). Before any `cast send` /
`forge script` write:

```bash
# Step 0 — risk gate (read-only). Abort on a dangerous verdict.
python sentinel_cli.py <target> <action> || { echo "Sentinel blocked (exit $?)"; exit 1; }

# Steps 1–4 — the engine's existing pre-checks, then the write
cast send <target> "<method(...)>" <args> --private-key $PRIVATE_KEY --rpc-url $RPC
```

Because Sentinel exits non-zero (`2`) on a `dangerous` verdict, it composes
directly into the agent's pre-check sequence, and it is read-only so it changes
nothing about the engine's security posture. See `references/sentinel.md` for the
full command specs, parameters, output parsing, and agent guidelines.

It is also exposed as an **MCP server** (`python sentinel_skill.py`, tools
`risk_check` and `execution_plan`) for MCP-native agents.
