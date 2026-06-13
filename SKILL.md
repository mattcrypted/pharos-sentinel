---
name: pharos-skill-engine
description: >
  REQUIRED for any Pharos blockchain task. This skill contains the RPC endpoints, chain IDs, explorer URLs, and token addresses needed to run cast/forge commands on Pharos — without reading it you will use wrong network config. Invoke whenever the user mentions "pharos", "PHRS", "PROS", "atlantic-testnet", or wants to do anything on the Pharos network: check balances, query transactions, call contracts, send transfers, deploy or verify Solidity contracts, run batch airdrops, or generate Web3 scripts targeting Pharos Chain / Pharos Network. It also bundles **Sentinel**, a read-only on-chain risk gate — invoke Sentinel whenever the user is about to move value or asks "is this safe?", "risk check", "should I approve this?", "is this token a trap?" before any transfer/approve/swap/deploy. Do not attempt Pharos on-chain operations without this skill.
version: 0.1.0
requires:
  anyBins:
  - cast
  - forge
---

# Pharos Chain Skills

Developer toolkit for the Pharos blockchain. Perform on-chain queries, send transactions, deploy and verify contracts via Foundry (`cast` / `forge`) CLI commands.

This package also bundles **Sentinel** — a read-only, pre-action **risk gate**. Before any value-moving operation, Sentinel reads the target over RPC and returns a `safe` / `caution` / `dangerous` verdict with reasons, so the agent can block or resize a risky action. Sentinel holds no private key and never signs or sends a transaction. See `references/sentinel.md`.

## Prerequisites

1. **Install Foundry** (MANDATORY — MUST be done before ANY other action):
   - The Agent MUST first run `which cast` to check if Foundry is installed.
   - If `cast` is NOT found, the Agent MUST immediately run the following installation commands. **Do NOT skip installation. Do NOT fall back to curl/JSON-RPC as a workaround. Do NOT proceed with any other task until Foundry is installed.**
     ```bash
     curl -L https://foundry.paradigm.xyz | bash
     ```
     Then run:
     ```bash
     source ~/.zshenv && foundryup
     ```
     Then verify with:
     ```bash
     cast --version
     ```
   - If installation fails, inform the user and STOP. Do not attempt alternative approaches.
2. **Configure Private Key**: Write operations (sending transactions, deploying contracts) require a private key, provided via one of the following:
   - Command argument: `--private-key <your_private_key>`
   - Environment variable: `$PRIVATE_KEY`
3. **Python 3** (for the Sentinel risk pre-check): the risk gate runs via `python sentinel_cli.py <address> <action>`. It performs its on-chain reads with the **Foundry `cast`** CLI from step 1 — so the only requirements are Foundry (already mandatory above) plus Python 3 and its standard library. Verify with `python3 --version`. **No private key is ever passed to Sentinel** — it is read-only (`cast call` / `cast code` / `cast storage` only, never `cast send`). (If `cast` or Python 3 is unavailable, the Agent should tell the user it cannot run the safety pre-check rather than silently skipping it.)

## Network Configuration

Network information is stored in `assets/networks.json`, containing both the Atlantic testnet and mainnet chains.

- **Default Network**: Atlantic testnet (`atlantic-testnet`). Used when the user does not specify a network.
- **Switching Networks**: When the user specifies `mainnet`, read the corresponding entry's `rpcUrl` from `assets/networks.json`.
- **Usage**: Read `assets/networks.json` and fill the target network's `rpcUrl` into each command's `--rpc-url` parameter. Contract verification also requires `chainId` and `explorerApiUrl`.

```bash
# Example: reading network configuration
RPC_URL=$(jq -r '.networks[] | select(.name=="atlantic-testnet") | .rpcUrl' assets/networks.json)
```

## Capability Index

Load the corresponding reference file based on user needs to get full command templates.

| User Need | Capability | Detailed Instructions |
|-----------|------------|----------------------|
| **"Is this safe?" · risk-check an address/contract before transfer/approve/swap/deploy · "is this token a trap?"** | **Sentinel risk gate (read-only RPC) — verdict + reasons** | **→ `references/sentinel.md#risk-check-pre-action-gate`** |
| **"Is it safe to approve this spender?" · "will this drain me?"** | **Sentinel risk check with `action=approve`** | **→ `references/sentinel.md#risk-check-pre-action-gate`** |
| **"How much should I send?" · "give me a safe plan"** | **Sentinel risk-gated execution plan (approve/block + bounded size)** | **→ `references/sentinel.md#risk-gated-execution-plan`** |
| **Add a safety pre-check before any transaction** | **Sentinel as a Write-Operation pre-check (Step 0)** | **→ `references/sentinel.md#use-as-a-write-operation-pre-check`** |
| View wallet portfolio / asset overview | `cast balance` + `cast call` (batch query all known tokens) | → `references/query.md#address-portfolio-wallet-asset-overview` |
| Query address balance | `cast balance` / `cast call` | → `references/query.md#balance-query` |
| Query transaction status | `cast tx` / `cast receipt` | → `references/query.md#transaction-query` |
| Call contract read-only method | `cast call` | → `references/query.md#contract-read-only-call` |
| Send transaction (native transfer) | `cast send` | → `references/transaction.md#native-token-transfer` |
| Call contract write method | `cast send` | → `references/transaction.md#contract-write-call` |
| Estimate Gas | `cast estimate` | → `references/transaction.md#gas-estimation` |
| Deploy contract | `forge script` (auto-generate deploy script) | → `references/contract.md#deploy-contract-forge-script` |
| Verify contract | `forge verify-contract` | → `references/contract.md#verify-contract` |
| One-click ERC20 deploy | `forge script` + built-in ERC20 template | → `references/contract.md#erc20-one-click-deploy-built-in-template` |
| Batch transfer / Airdrop | `forge script` (auto-generate airdrop script, supports 6000+ address batched airdrop, CSV file input, three-tier auto mode: ≤10 simple mode / 11-200 single batch / >200 multi-batch, hardened Distributor contract) | → `references/transaction.md#batch-transfer--airdrop` |
| Generate contract interaction scripts (read/write methods, JS/TS/Python) | Script_Generator (Agent auto-generates) | → `references/script-gen.md` |

## General Error Handling

Before executing commands, the Agent should perform pre-checks; when commands fail, provide user-friendly error messages based on stderr output.

| Error Scenario | CLI Error Signature | Handling |
|---------------|--------------------|---------| 
| Invalid address format | `invalid address` | Prompt to check address format (0x + 40 hex characters) |
| Transaction hash not found | `transaction not found` | Prompt that transaction was not found, suggest checking the hash |
| No contract code at address | Empty return value | Prompt that target address has no contract code |
| Call revert | `execution reverted` | Extract and display revert reason |
| Private key not configured | Command missing `--private-key` | Prompt user to configure private key (argument or environment variable) |
| Insufficient balance | `insufficient funds` | Prompt insufficient balance, show current balance |
| Nonce conflict | `nonce too low` | Suggest waiting or manually specifying nonce |
| Missing network config | `assets/networks.json` unreadable | Prompt that config file is missing or has invalid format |
| Unsupported network | Network name not in config list | Prompt that only `atlantic-testnet` and `mainnet` are supported |
| Sentinel `dangerous` verdict | risk gate exit code `2` | STOP the pending write; surface the `reasons` to the user (see `references/sentinel.md`) |

See the corresponding reference files for detailed error handling tables for each operation.

## Security Reminders

- **Private Key Protection**: Never expose private keys in logs, chat history, or version control. Store the private key in the `$PRIVATE_KEY` environment variable and reference it explicitly in commands via `--private-key $PRIVATE_KEY`. Note: `forge` / `cast` do not automatically read environment variables; they must be explicitly passed as command arguments.
- **Network Confirmation**: Before executing write operations, the Agent must clearly inform the user of the target network (testnet or mainnet). Mainnet operations require a prominent warning and user re-confirmation to prevent accidental operations.
- **Sentinel is read-only**: the bundled risk gate performs only read-only Foundry `cast` reads (`cast call` / `code` / `storage`), holds no private key, and NEVER signs or sends a transaction (never `cast send`) — it only ever blocks a risky action (exit `2`). Adding it changes nothing about the write path's security posture.

## Write Operation Pre-checks (Required for All Write Operations)

For all operations requiring a private key (transfers, contract calls, deployments, airdrops, etc.), the Agent must automatically complete the following checks before execution.

### 0. Risk Pre-Check (Sentinel) — run FIRST, before touching the key

Before any write, run the read-only risk gate against the operation's target:

```bash
# Step 0 — risk gate (read-only). Abort on a dangerous verdict.
python sentinel_cli.py <target> <action> || { echo "Sentinel blocked (exit $?)"; exit 1; }
```

- `<action>` is one of `transfer` | `swap` | `approve` | `call`.
- If the verdict is **`dangerous`** (exit `2`): **STOP** — do not proceed to the checks below or run the write. Surface the `reasons` to the user.
- If the verdict is **`caution`**: surface the `reasons`; ask the user to confirm or reduce size before continuing.
- If the verdict is **`safe`**: continue to the private-key checks below.

Full command specs, parameters, output parsing, and the risk-gated execution plan are in `references/sentinel.md`. Sentinel is also exposed as an **MCP server** (`python sentinel_skill.py`, tools `risk_check` and `execution_plan`) for MCP-native agents.

### 1. Private Key Check

Automatically detect whether the `$PRIVATE_KEY` environment variable is set:

```bash
# Check if environment variable exists (without outputting the private key)
[ -n "$PRIVATE_KEY" ] && echo "PRIVATE_KEY is set" || echo "PRIVATE_KEY is not set"
```

- If **not set**: Prompt the user to configure via `export PRIVATE_KEY=<your_private_key>`, do not proceed
- If **set**: Continue to next step

### 2. Derive Public Address and Confirm with User

Derive the corresponding public address from the private key via `cast wallet address`:

```bash
cast wallet address --private-key $PRIVATE_KEY
```

### 3. Network Confirmation (Must Clearly Inform User)

The Agent must clearly inform the user of the target network before executing any write operation. Read the target network info from `assets/networks.json` and display the network name and type to the user.

- If the user did not specify a network, use the default network (`atlantic-testnet`) and clearly inform the user: **Current operation targets the Atlantic testnet**
- If the user specified `mainnet`, prominently warn the user: **Current operation targets mainnet, please confirm to proceed**

Combine the information from steps 2 and 3 for user confirmation. Example format:

```
Detected private key address: 0x1234...abcd
Target network: Atlantic Testnet (atlantic-testnet)
Proceed with this account on this network?
```

Example format for mainnet operations:

```
Detected private key address: 0x1234...abcd
⚠️ Target network: Mainnet (mainnet) — please proceed with caution
Proceed with this account on mainnet?
```

- After user confirmation, continue with subsequent operations (balance check, transaction sending, etc.)
- If user declines, stop execution

### 4. Automatic Balance Check

After confirming the account and network, automatically query the balance (see the balance check steps in each operation's Agent guidelines).
