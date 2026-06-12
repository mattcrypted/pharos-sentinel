# Query Operation Instructions

This file contains detailed instructions for all query operations on the Pharos chain, covering balance queries, transaction queries, and contract read-only calls.

> **Network Configuration**: The `<rpc>` parameter in all commands is read from the corresponding network's `rpcUrl` field in `assets/networks.json`. Defaults to the Atlantic testnet.
>
> **Native Token Symbol**: Read the native token symbol from the current network's `nativeToken` field in `assets/networks.json` (e.g., `PHRS` for Atlantic testnet, `PROS` for mainnet), and use this symbol instead of the generic "ether" when displaying balances.

---

## Balance Query

### Native Token Balance (wei)

**Command Template**

```bash
cast balance <address> --rpc-url <rpc>
```

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `<address>` | string | Yes | Target address, format: `0x` + 40 hex characters |
| `<rpc>` | string | Yes | RPC endpoint URL, read from `assets/networks.json` |

**Output Parsing**

- Command outputs a decimal number string in wei
- Example output: `1000000000000000000` (i.e., 1 PHRS on Atlantic testnet)
- Use the `nativeToken` field from the current network in `assets/networks.json` as the token symbol when displaying

**Error Handling**

| Error Signature | Cause | Suggested Action |
|----------------|-------|-----------------|
| `invalid address` | Invalid address format | Prompt user to check address format (`0x` + 40 hex characters) |
| Connection timeout / `connection refused` | RPC node unreachable | Check network connection and RPC URL |

---

### Native Token Balance (ether)

**Command Template**

```bash
cast balance <address> --rpc-url <rpc> --ether
```

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `<address>` | string | Yes | Target address, format: `0x` + 40 hex characters |
| `<rpc>` | string | Yes | RPC endpoint URL |

**Output Parsing**

- Command outputs a decimal number string in ether (the standard unit of the native token)
- Example output: `1.000000000000000000`
- Display using the current network's native token symbol, e.g., `1.0 PHRS` (Atlantic testnet) or `1.0 PROS` (mainnet)

**Error Handling**

Same as "Native Token Balance (wei)".

> **Agent Guidelines**: When querying native balance, first read the `nativeToken` field from `assets/networks.json` to get the token symbol. When displaying results, always clearly state the target network (e.g., "Results from Atlantic testnet" or "Results from mainnet"). Execute both wei and ether commands and display both values using the correct token symbol (e.g., `1.0 PHRS` instead of `1.0 ether`). Also include a block explorer address link: `<explorerUrl>/address/<address>`.

---

### ERC20 Token Balance

**Command Template**

```bash
cast call <token> "balanceOf(address)(uint256)" <holder> --rpc-url <rpc>
```

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `<token>` | string | Yes | ERC20 token contract address |
| `<holder>` | string | Yes | Holder address |
| `<rpc>` | string | Yes | RPC endpoint URL |

**Output Parsing**

- Returns raw uint256 value (not adjusted for decimals)
- Convert to human-readable value using `decimals()`: `readable balance = raw value / 10^decimals`

**Error Handling**

| Error Signature | Cause | Suggested Action |
|----------------|-------|-----------------|
| `invalid address` | Invalid address format | Prompt user to check token contract address or holder address format |
| Empty return value | No contract code at target address | Prompt user to confirm token contract address is correct |
| `execution reverted` | Contract call failed | Prompt that target address may not be a valid ERC20 contract |

---

### ERC20 Token Symbol

**Command Template**

```bash
cast call <token> "symbol()(string)" --rpc-url <rpc>
```

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `<token>` | string | Yes | ERC20 token contract address |
| `<rpc>` | string | Yes | RPC endpoint URL |

**Output Parsing**

- Returns token symbol string, e.g., `USDT`, `WETH`

**Error Handling**

| Error Signature | Cause | Suggested Action |
|----------------|-------|-----------------|
| Empty return value | No contract code at target address | Prompt user to confirm token contract address |
| `execution reverted` | Contract does not support `symbol()` method | Prompt that target contract may not be a standard ERC20 |

---

### ERC20 Token Decimals

**Command Template**

```bash
cast call <token> "decimals()(uint8)" --rpc-url <rpc>
```

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `<token>` | string | Yes | ERC20 token contract address |
| `<rpc>` | string | Yes | RPC endpoint URL |

**Output Parsing**

- Returns uint8 value, typically `18`, `6`, `8`, etc.
- Used to convert `balanceOf` raw value to human-readable value

**Error Handling**

| Error Signature | Cause | Suggested Action |
|----------------|-------|-----------------|
| Empty return value | No contract code at target address | Prompt user to confirm token contract address |
| `execution reverted` | Contract does not support `decimals()` method | Prompt that target contract may not be a standard ERC20 |

> **Agent Guidelines**: When querying ERC20 balance, first check the token list for the current network in `assets/tokens.json` to see if the user's token symbol matches a known token. If matched, use its `address` and `decimals` directly without calling on-chain `decimals()` and `symbol()`. If the user provides a token contract address directly (even for unknown tokens), use it to call `decimals()`, `symbol()`, and `balanceOf(address)` in sequence, then convert the raw balance to human-readable format: `balance = rawBalance / 10^decimals`, displayed with the token symbol. **If the token is not in `assets/tokens.json` AND the user did not provide a contract address: do NOT search the web or attempt to fetch the explorer page (the explorer has browser checks that block automated access).** Instead, immediately direct the user to find the token contract address themselves on the block explorer token list page: `<explorerUrl>/tokens` (read `explorerUrl` from `assets/networks.json` for the current network). Example response: "AWETH is not in the known token list. You can find its contract address at https://atlantic.pharosscan.xyz/tokens — once you have the address, share it with me and I'll query the balance for you." Also include block explorer links: holder address `<explorerUrl>/address/<holder>`, token contract `<explorerUrl>/address/<token>`.

---

## Transaction Query

### Transaction Details

**Command Template**

```bash
cast tx <tx_hash> --rpc-url <rpc>
```

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `<tx_hash>` | string | Yes | Transaction hash, format: `0x` + 64 hex characters |
| `<rpc>` | string | Yes | RPC endpoint URL |

**Output Parsing**

Command output contains the following key fields:

| Field | Description |
|-------|-------------|
| `from` | Sender address |
| `to` | Recipient address (null for contract creation transactions) |
| `value` | Transfer amount (wei) |
| `gas` | Gas Limit |
| `gasPrice` | Gas price |
| `input` | Transaction input data (calldata) |
| `blockNumber` | Block number (null for pending transactions) |
| `nonce` | Sender nonce |

**Error Handling**

| Error Signature | Cause | Suggested Action |
|----------------|-------|-----------------|
| `transaction not found` | Transaction hash does not exist on chain | Prompt that transaction was not found, suggest checking hash or waiting for node sync |
| `invalid hash` | Invalid hash format | Prompt user to check hash format (`0x` + 64 hex characters) |

---

### Transaction Receipt

**Command Template**

```bash
cast receipt <tx_hash> --rpc-url <rpc>
```

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `<tx_hash>` | string | Yes | Transaction hash, format: `0x` + 64 hex characters |
| `<rpc>` | string | Yes | RPC endpoint URL |

**Output Parsing**

Command output contains the following key fields:

| Field | Description |
|-------|-------------|
| `status` | Transaction status: `1` = success, `0` = failed |
| `blockNumber` | Block number containing the transaction |
| `gasUsed` | Actual Gas consumed |
| `effectiveGasPrice` | Actual Gas price |
| `contractAddress` | Newly created contract address (null for non-contract-creation transactions) |
| `logs` | Event log list |

**Error Handling**

| Error Signature | Cause | Suggested Action |
|----------------|-------|-----------------|
| `transaction not found` | Transaction hash does not exist or transaction is still pending | Combine with `cast tx` result to determine if pending or non-existent |
| `invalid hash` | Invalid hash format | Prompt user to check hash format (`0x` + 64 hex characters) |

---

### Transaction Status Determination Logic

When querying transaction status, combine `cast tx` and `cast receipt` results:

```
1. Execute cast tx <tx_hash> --rpc-url <rpc>
   - If no result → Transaction does not exist, prompt user to check hash
   - If result exists → Continue to step 2

2. Execute cast receipt <tx_hash> --rpc-url <rpc>
   - If no result → Transaction status is **pending** (submitted but not confirmed)
   - If result exists → Check status field:
     - status = 1 → Transaction status is **success**
     - status = 0 → Transaction status is **failed**
```

> **Agent Guidelines**: When querying transaction status, always execute `cast tx` first to confirm the transaction exists, then execute `cast receipt` to get the final status. When displaying status, also provide key information (block number, Gas consumed, sender/recipient, etc.) and include a block explorer transaction link: `<explorerUrl>/tx/<tx_hash>`.

---

## Contract Read-Only Call

### Generic cast call Command

**Command Template**

```bash
cast call <contract> "<method_sig>(<param_types>)(<return_types>)" [args...] --rpc-url <rpc>
```

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `<contract>` | string | Yes | Contract address |
| `<method_sig>` | string | Yes | Method name |
| `<param_types>` | string | Yes | Parameter type list, comma-separated (empty for no parameters) |
| `<return_types>` | string | Yes | Return type list, comma-separated |
| `[args...]` | any | No | Method argument values, passed in order |
| `<rpc>` | string | Yes | RPC endpoint URL |

**Common Call Examples**

```bash
# No-parameter call
cast call <contract> "totalSupply()(uint256)" --rpc-url <rpc>

# Single-parameter call
cast call <contract> "balanceOf(address)(uint256)" <address> --rpc-url <rpc>

# Multi-parameter call
cast call <contract> "allowance(address,address)(uint256)" <owner> <spender> --rpc-url <rpc>

# Multi-return-value call
cast call <contract> "getReserves()(uint112,uint112,uint32)" --rpc-url <rpc>
```

**Output Parsing**

- Return values are decoded according to declared return types
- Multiple return values appear on separate lines
- If return type declaration is incorrect, output may be raw hex data

**Error Handling**

| Error Signature | Cause | Suggested Action |
|----------------|-------|-----------------|
| `invalid address` | Invalid contract address format | Prompt user to check address format (`0x` + 40 hex characters) |
| Empty return value | No contract code at target address | Prompt "no contract code at target address", suggest confirming contract address |
| `function signature mismatch` | Method name or parameter types don't match | Prompt method signature error, suggest checking method name and parameter types |
| `execution reverted` | Contract execution reverted | Extract revert reason and display to user |
| `execution reverted: <reason>` | Contract execution reverted (with reason) | Display revert reason directly |

> **Agent Guidelines**: Before executing a contract read-only call, confirm the user has provided a complete method signature (method name + parameter types + return types). If the user only provided the method name, guide them to provide parameter and return type information. After the call, include a block explorer contract link: `<explorerUrl>/address/<contract>`.


---

## Address Portfolio (Wallet Asset Overview)

Aggregate and display all assets held by an address on the current network, including native token balance and all known ERC20 token balances from `assets/tokens.json`.

### Agent Execution Flow

When the user asks to view wallet assets / portfolio / holdings for an address, the Agent executes the following steps:

**Step 1: Read network configuration and token list**

```bash
# Read target network RPC URL and native token symbol from assets/networks.json
RPC_URL=<rpcUrl from target network>
NATIVE_SYMBOL=<nativeToken from target network>
EXPLORER_URL=<explorerUrl from target network>
```

Read the token list for the current network from `assets/tokens.json`. If the current network has no entry in `tokens.json`, only query the native token balance.

**Step 2: Query native token balance**

```bash
cast balance <address> --rpc-url <rpc> --ether
```

**Step 3: Query all known ERC20 token balances**

For each token in the current network's token list from `assets/tokens.json`, execute:

```bash
cast call <token_address> "balanceOf(address)(uint256)" <address> --rpc-url <rpc>
```

Use the `decimals` value from `assets/tokens.json` to convert the raw balance: `readable = raw / 10^decimals`.

Skip tokens with zero balance in the final display (do not show 0-balance tokens).

**Step 4: Display aggregated results**

Present results in a clear table format:

```
Wallet Portfolio for 0x1234...abcd
Network: Atlantic Testnet (atlantic-testnet)

| Token  | Balance          |
|--------|------------------|
| PHRS   | 12.5             |
| USDC   | 1,000.00         |
| WETH   | 0.25             |

Block Explorer: <explorerUrl>/address/<address>

💡 To query other tokens not listed above, find token contract addresses at:
   <explorerUrl>/tokens
```

### Command Summary


| Step | Command | Purpose |
|------|---------|---------|
| Native balance | `cast balance <address> --rpc-url <rpc> --ether` | Query native token balance |
| ERC20 balance (per token) | `cast call <token> "balanceOf(address)(uint256)" <address> --rpc-url <rpc>` | Query each known ERC20 token balance |

### Error Handling

| Error Signature | Cause | Suggested Action |
|----------------|-------|-----------------|
| `invalid address` | Invalid wallet address format | Prompt user to check address format (`0x` + 40 hex characters) |
| Connection timeout / `connection refused` | RPC node unreachable | Check network connection and RPC URL |
| `execution reverted` on a specific token | Token contract may be non-standard or paused | Skip this token, note it in the output, continue with remaining tokens |
| No token list for current network in `tokens.json` | Network not configured in tokens.json | Only display native token balance, inform user that no known ERC20 tokens are configured for this network |

> **Agent Guidelines**: When the user asks to "view wallet assets", "check portfolio", "show all balances", or similar, execute this aggregated query flow. Read the token list from `assets/tokens.json` for the current network — use the known `decimals` and `symbol` directly without making on-chain `decimals()` or `symbol()` calls. Execute all ERC20 balance queries and collect results. Filter out zero-balance tokens. Display the final result as a clean table with the native token listed first, followed by ERC20 tokens sorted alphabetically. Always include the block explorer address link. If any individual token query fails, log the error and continue with the remaining tokens — do not abort the entire portfolio query. After displaying results, remind the user: if they need to query other tokens not in the list, they can find token contract addresses themselves at `<explorerUrl>/tokens` (read `explorerUrl` from `assets/networks.json` for the current network). **Do NOT attempt to fetch or scrape the explorer page — it has browser checks that block automated access.** Once the user provides a contract address, the Agent can query the balance.
