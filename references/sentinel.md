# Sentinel Risk Gate — Operation Instructions

This file teaches the AI agent how to run **Sentinel**, a read-only on-chain risk
gate, BEFORE any value-moving operation on Pharos. Sentinel reads the chain over
RPC and returns a verdict (`safe` / `caution` / `dangerous`) with reasons, plus a
risk-gated execution plan. It never signs or sends a transaction.

> **Network Configuration**: the `<rpc>` Sentinel uses is read from the matching
> network's `rpc` field in `assets/networks.json` (default: Atlantic testnet,
> chainId `688689`).
>
> **Private Key**: NOT required. Sentinel is read-only — it performs no writes,
> so no `--private-key` is ever passed.

> **Pre-check extension**: This skill adds a fifth check to the SKILL.md
> "Write Operation Pre-Check Sequence". Run the Risk Check below before every
> `transfer`, `approve`, `swap`, contract `deploy`, or `airdrop`. If the verdict
> is `dangerous`, STOP and do not run the write command.

---

## Risk Check (pre-action gate)

### Overview
Assess the risk of interacting with a target address for a given action. The
verdict, score, and reasons are drawn entirely from on-chain signals:
contract-vs-EOA, EIP-1167/1967/1822 proxy detection, bytecode opcode analysis
(SELFDESTRUCT / unguarded DELEGATECALL), ownership & upgrade-admin concentration,
ERC-20 introspection (incl. the zero-supply trap), pausable state, tiny-bytecode
stubs, and action/target mismatches.

### Command Template
```bash
python sentinel_cli.py <address> <action>
```

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `<address>` | string | Yes | Target contract or counterparty (`0x` + 40 hex) |
| `<action>` | enum | Yes | `transfer` \| `swap` \| `approve` \| `call` |

### Output Parsing
| Field | Description |
|-------|-------------|
| `verdict` | `safe` \| `caution` \| `dangerous` \| `unknown` |
| `score` | additive risk score (`>=70` dangerous, `>=35` caution, else safe) |
| `reasons[]` | why the verdict was reached — always surface these to the user |
| exit code | `0` = safe/caution (proceed), `2` = dangerous (block) |

### Error Handling
| Error | Cause | Fix |
|-------|-------|-----|
| `unknown` verdict, "not a valid address" | malformed address | confirm `0x` + 40 hex characters |
| `unknown` verdict, "could not reach Pharos Atlantic RPC" | RPC unreachable | retry; confirm `rpc` in `assets/networks.json` |

> **Agent Guidelines:**
> 1. Run this BEFORE any write operation on the target.
> 2. If `verdict == dangerous` (exit `2`): STOP. Tell the user the reasons and do NOT send the transaction.
> 3. If `verdict == caution`: surface the reasons and ask the user to confirm, or reduce size.
> 4. If `verdict == safe`: proceed to the engine's normal write pre-checks.
> 5. Always show the `reasons` — they are the audit trail for the decision.

---

## Risk-Gated Execution Plan

### Overview
Turn a verdict into an actionable decision: approve or block the action within a
caller-specified risk tolerance, with a bounded (de-risked) size suggestion.

### Command Template
```bash
python sentinel_cli.py <address> <action> --plan --amount <PHRS> --max-risk <safe|caution>
```

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `<address>` | string | Yes | Target contract / counterparty |
| `<action>` | enum | Yes | `transfer` \| `swap` \| `approve` \| `call` |
| `--amount` | number | No | Intended size in PHRS (exposure context) |
| `--max-risk` | enum | Yes | Caller tolerance: `safe` or `caution` (block anything riskier) |

### Output Parsing
| Field | Description |
|-------|-------------|
| `approved` | `true` → proceed; `false` → block |
| `verdict` | the underlying risk verdict |
| `suggested.amount_phrs` | de-risked size (halved on a `caution` verdict) |
| exit code | `0` = approved, `2` = blocked |

> **Agent Guidelines:**
> 1. Use this as the gate for value-moving actions: only proceed when `approved == true`.
> 2. On block, do NOT run the write command; report the verdict + reasons.
> 3. Respect `suggested.amount_phrs` when sizing the action.

---

## Use as a Write-Operation Pre-Check

Before running any `cast send` / `forge script` write in the Pharos Skill Engine,
insert Sentinel as the first gate. It exits non-zero (`2`) on a `dangerous`
verdict, so it composes directly into a shell gate:

```bash
# 1. risk gate (read-only) — abort on a dangerous verdict
python sentinel_cli.py <target> <action> || { echo "Sentinel blocked (exit $?)"; exit 1; }

# 2. only if it passed, run the engine's existing write pre-checks + the write
cast send <target> "<method(...)>" <args> --private-key $PRIVATE_KEY --rpc-url $RPC
```

Sentinel is read-only and holds no key, so adding it changes nothing about the
engine's security posture — it only ever blocks, never signs.

> **Agent Guidelines:** Treat a non-zero exit from the risk gate as a hard stop.
> Never fall back to running the write command when Sentinel returns `dangerous`.
