# Transaction Operation Instructions

This file contains detailed instructions for all transaction operations on the Pharos chain, covering sending transactions (native transfers and contract write calls) and Gas estimation.

> **Network Configuration**: The `<rpc>` parameter in all commands is read from the corresponding network's `rpcUrl` field in `assets/networks.json`. Defaults to the Atlantic testnet.
>
> **Private Key Configuration**: All write operations must explicitly pass the private key via the `--private-key` parameter. Recommended to use environment variable: `--private-key $PRIVATE_KEY`. `cast` does not automatically read environment variables; they must be explicitly referenced in the command.

---

## Send Transaction

### Native Token Transfer

**Command Template**

```bash
cast send <to> --value <amount>ether --private-key <key> --rpc-url <rpc>
```

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `<to>` | string | Yes | Recipient address, format: `0x` + 40 hex characters |
| `<amount>` | number | Yes | Transfer amount in ether (e.g., `0.1ether`, `1ether`) |
| `<key>` | string | Yes | Sender private key, or use environment variable `$PRIVATE_KEY` |
| `<rpc>` | string | Yes | RPC endpoint URL, read from `assets/networks.json` |

**Output Parsing**

`cast send` waits for transaction confirmation by default and outputs the transaction receipt with the following key fields:

| Field | Description |
|-------|-------------|
| `status` | Transaction status: `1` = success, `0` = failed |
| `blockNumber` | Block number containing the transaction |
| `gasUsed` | Actual Gas consumed |
| `transactionHash` | Transaction hash |
| `from` | Sender address |
| `to` | Recipient address |

**Error Handling**

| Error Signature | Cause | Suggested Action |
|----------------|-------|-----------------|
| Command missing `--private-key` | Private key not provided | Prompt user to configure via `--private-key` parameter or `$PRIVATE_KEY` environment variable |
| `insufficient funds` | Account balance insufficient for transfer amount + Gas fees | Prompt insufficient balance, suggest checking current balance via `cast balance` |
| `nonce too low` | Nonce conflict, usually because a previous transaction is not yet confirmed | Prompt nonce conflict, suggest waiting for prior transaction confirmation or manually specifying via `--nonce` |
| `invalid address` | Invalid recipient address format | Prompt user to check address format (`0x` + 40 hex characters) |
| Connection timeout / `connection refused` | RPC node unreachable | Check network connection and RPC URL |

> **Agent Guidelines**: Complete the "Write Operation Pre-checks" (see SKILL.md) before execution, which includes the network confirmation step — must clearly inform the user of the target network (testnet or mainnet). Automatically query sender balance via `cast balance <sender> --rpc-url <rpc>` and confirm balance ≥ transfer amount + estimated Gas fees. If balance is insufficient, inform the user directly without executing the transaction. After sending, display the transaction hash, status, and include a block explorer transaction link: `<explorerUrl>/tx/<transactionHash>`.

---

### Contract Write Call

**Command Template**

```bash
cast send <contract> "<method_sig>(<param_types>)" [args...] --private-key <key> --rpc-url <rpc>
```

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `<contract>` | string | Yes | Target contract address |
| `<method_sig>` | string | Yes | Method name |
| `<param_types>` | string | Yes | Parameter type list, comma-separated (empty for no parameters) |
| `[args...]` | any | No | Method argument values, passed in order |
| `<key>` | string | Yes | Sender private key, or use environment variable `$PRIVATE_KEY` |
| `<rpc>` | string | Yes | RPC endpoint URL |

**Common Call Examples**

```bash
# ERC20 transfer
cast send <token> "transfer(address,uint256)" <to> <amount> --private-key <key> --rpc-url <rpc>

# ERC20 approve
cast send <token> "approve(address,uint256)" <spender> <amount> --private-key <key> --rpc-url <rpc>

# Contract call with ETH value
cast send <contract> "deposit()" --value 1ether --private-key <key> --rpc-url <rpc>
```

**Output Parsing**

Same as native token transfer — `cast send` waits for transaction confirmation by default and outputs the transaction receipt (status, blockNumber, gasUsed, transactionHash, etc.).

**Error Handling**

| Error Signature | Cause | Suggested Action |
|----------------|-------|-----------------|
| Command missing `--private-key` | Private key not provided | Prompt user to configure via `--private-key` parameter or `$PRIVATE_KEY` environment variable |
| `insufficient funds` | Account balance insufficient for Gas fees | Prompt insufficient balance, suggest checking current balance |
| `nonce too low` | Nonce conflict | Prompt nonce conflict, suggest waiting for prior transaction confirmation or manually specifying nonce |
| `execution reverted` | Contract execution reverted | Extract and display revert reason |
| `execution reverted: <reason>` | Contract execution reverted (with reason) | Display revert reason directly, e.g., insufficient permissions, parameter validation failure |
| `function signature mismatch` | Method name or parameter types don't match | Prompt method signature error, suggest checking method name and parameter types |
| `invalid address` | Invalid contract address format | Prompt user to check address format |

> **Agent Guidelines**: Complete the "Write Operation Pre-checks" (see SKILL.md) before execution. Confirm the user has provided a complete method signature (method name + parameter types). If the user only provided the method name, guide them to provide parameter type information. Automatically query sender balance via `cast balance <sender> --rpc-url <rpc>` and confirm balance is sufficient for Gas fees before executing. If balance is insufficient, inform the user directly without executing the transaction. After successful transaction, include a block explorer transaction link: `<explorerUrl>/tx/<transactionHash>`.

---

## Gas Estimation

### Estimate Gas Consumption

**Command Template**

```bash
cast estimate <to> "<method_sig>(<param_types>)" [args...] --rpc-url <rpc>
```

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `<to>` | string | Yes | Target address (contract address or recipient address) |
| `<method_sig>` | string | No | Method name (omit for native transfers) |
| `<param_types>` | string | No | Parameter type list, comma-separated |
| `[args...]` | any | No | Method argument values, passed in order |
| `<rpc>` | string | Yes | RPC endpoint URL |

**Common Call Examples**

```bash
# Estimate native transfer Gas
cast estimate <to> --value <amount>ether --rpc-url <rpc>

# Estimate contract call Gas
cast estimate <contract> "transfer(address,uint256)" <to> <amount> --rpc-url <rpc>

# Estimate contract call with ETH value Gas
cast estimate <contract> "deposit()" --value 1ether --rpc-url <rpc>
```

**Output Parsing**

- Command outputs a decimal number string representing the estimated Gas consumption
- Example output: `21000` (standard Gas consumption for native transfers)

**Error Handling**

| Error Signature | Cause | Suggested Action |
|----------------|-------|-----------------|
| `execution reverted` | Transaction parameters would cause contract execution to revert | Extract revert reason and display, prompt user to check transaction parameters |
| `execution reverted: <reason>` | Contract execution reverted (with reason) | Display revert reason directly |
| CLI parameter missing error | Required parameters incomplete | Prompt user to provide missing parameters (target address, method signature, etc.) |
| `invalid address` | Invalid address format | Prompt user to check address format |
| Connection timeout / `connection refused` | RPC node unreachable | Check network connection and RPC URL |

---

### Query Gas Price

**Command Template**

```bash
cast gas-price --rpc-url <rpc>
```

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `<rpc>` | string | Yes | RPC endpoint URL, read from `assets/networks.json` |

**Output Parsing**

- Command outputs a decimal number string representing the current network Gas price in wei
- Example output: `1000000000` (i.e., 1 Gwei)

**Error Handling**

| Error Signature | Cause | Suggested Action |
|----------------|-------|-----------------|
| Connection timeout / `connection refused` | RPC node unreachable | Check network connection and RPC URL |

---

### Gas Fee Calculation Logic

After estimating Gas, calculate the suggested Gas Limit and estimated fee using the following logic:

```
1. Get estimated Gas consumption
   estimatedGas = output value from cast estimate

2. Calculate suggested Gas Limit (multiply by 1.2 safety factor, round up)
   suggestedGasLimit = ceil(estimatedGas × 1.2)

3. Get current Gas price
   gasPrice = output value from cast gas-price

4. Calculate estimated transaction fee
   estimatedCost = suggestedGasLimit × gasPrice (in wei)

5. Convert to ether for display
   estimatedCostEther = estimatedCost / 10^18
```

**Calculation Example**

```
estimatedGas      = 21000
suggestedGasLimit = ceil(21000 × 1.2) = 25200
gasPrice          = 1000000000 (1 Gwei)
estimatedCost     = 25200 × 1000000000 = 25200000000000 wei
estimatedCostEther = 0.0000252 ether
```

> **Agent Guidelines**: When estimating Gas, execute `cast estimate` and `cast gas-price` in sequence, then calculate the suggested Gas Limit and estimated fee using the logic above. When displaying to the user, provide Gas consumption, suggested Gas Limit, Gas price, and estimated fee (in ether). If `cast estimate` returns a revert error, display the revert reason directly without performing fee calculation.

---

## Batch Transfer / Airdrop

### Overview

Use `forge script` to generate airdrop scripts in the user's project, batch-transferring to multiple addresses. Supports both native token and ERC20 token modes. All operations are completed in the user's project directory, and scripts remain in the user's project.

**Mode Selection**: The Agent automatically selects the execution mode based on the number of recipient addresses (see "Automatic Mode Selection" section):
- **≤ 10 addresses**: Simple mode — sequential transfers within the script, no contract deployment needed
- **11 ~ 200 addresses**: Single-batch Distributor mode — deploy a hardened distributor contract, complete all transfers in one transaction
- **> 200 addresses**: Multi-batch Distributor mode — deploy a hardened distributor contract, call distribute in batches, supports CSV file input

### User Input Format

Users need to provide a list of recipient addresses and amounts in the following formats:

Direct input:

```
# Format: address,amount
0xAddr1,100
0xAddr2,200
0xAddr3,50
```

Or in table format:

| Address | Amount |
|---------|--------|
| 0xAddr1 | 100 |
| 0xAddr2 | 200 |

Or provide a CSV file path (recommended for large-scale airdrops, see "CSV File Support" section):

```
Please use the airdrop.csv file for the airdrop
```

### Amount Unit Notes

- Native token: Values in the `amounts` array are in wei. The Agent should convert based on the user's input unit:
  - User inputs `1` (ether) → `1 ether` (i.e., `1e18`)
  - User inputs `0.5` (ether) → `0.5 ether` (i.e., `5e17`)
- ERC20 token: Values in the `amounts` array must include decimals. The Agent should convert based on token precision:
  - Token decimals=6, user inputs `100` → `100 * 1e6 = 100000000`
  - Token decimals=18, user inputs `100` → `100 * 1e18`
  - Check `assets/tokens.json` for known token decimals, or query via `cast call`

---

### Simple Mode (≤ 10 Addresses)

Suitable for small numbers of addresses, with sequential transfers within the script — simple and straightforward.

#### Native Token — Simple Mode

Agent generates `Airdrop.s.sol` in the user's project `script/` directory:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "forge-std/console.sol";

contract Airdrop is Script {
    function run() external {
        // ============ Airdrop Parameters (Agent generates based on user input) ============
        address[] memory recipients = new address[](<count>);
        uint256[] memory amounts = new uint256[](<count>);

        recipients[0] = <addr1>; amounts[0] = <amount1>;
        recipients[1] = <addr2>; amounts[1] = <amount2>;
        // ... more addresses
        // ==============================================================

        vm.startBroadcast();

        uint256 totalSent = 0;
        for (uint256 i = 0; i < recipients.length; i++) {
            (bool success, ) = recipients[i].call{value: amounts[i]}("");
            require(success, "Transfer failed");
            totalSent += amounts[i];
            console.log("Sent to:", recipients[i], "Amount:", amounts[i]);
        }

        console.log("=== Airdrop Complete ===");
        console.log("Total recipients:", recipients.length);
        console.log("Total sent (wei):", totalSent);

        vm.stopBroadcast();
    }
}
```

#### ERC20 Token — Simple Mode

Agent generates `AirdropERC20.s.sol` in the user's project `script/` directory:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "forge-std/console.sol";

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
    function decimals() external view returns (uint8);
    function symbol() external view returns (string memory);
}

contract AirdropERC20 is Script {
    function run() external {
        // ============ Airdrop Parameters (Agent generates based on user input) ============
        address token = <token_address>;

        address[] memory recipients = new address[](<count>);
        uint256[] memory amounts = new uint256[](<count>);

        recipients[0] = <addr1>; amounts[0] = <amount1>;
        recipients[1] = <addr2>; amounts[1] = <amount2>;
        // ... more addresses
        // ==============================================================

        IERC20 erc20 = IERC20(token);
        console.log("Token:", erc20.symbol());
        console.log("Decimals:", erc20.decimals());
        console.log("Sender balance:", erc20.balanceOf(msg.sender));

        vm.startBroadcast();

        uint256 totalSent = 0;
        for (uint256 i = 0; i < recipients.length; i++) {
            bool success = erc20.transfer(recipients[i], amounts[i]);
            require(success, "Transfer failed");
            totalSent += amounts[i];
            console.log("Sent to:", recipients[i], "Amount:", amounts[i]);
        }

        console.log("=== Airdrop Complete ===");
        console.log("Total recipients:", recipients.length);
        console.log("Total sent:", totalSent);

        vm.stopBroadcast();
    }
}
```

---

### Distributor Mode (> 10 Addresses)

Suitable for large-scale airdrops. The script deploys a lightweight Distributor contract inline, completing all transfers in a single transaction via the contract — far more Gas-efficient than sequential transfers. The contract is disposable and requires no ongoing management.

**Principle**:
1. Script deploys a temporary Distributor contract
2. Sends the total amount to the Distributor contract (native tokens via `value`, ERC20 via `approve` + contract's `transferFrom`)
3. Distributor contract distributes to all recipients in a single transaction
4. Contract has no owner, no state — disposable after use

#### Native Token — Distributor Mode

Agent generates `Airdrop.s.sol` in the user's project `script/` directory:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "forge-std/console.sol";

contract NativeDistributor {
    event Distributed(address indexed recipient, uint256 amount, bool success);

    function distribute(
        address[] calldata recipients,
        uint256[] calldata amounts
    ) external payable {
        require(recipients.length == amounts.length, "length mismatch");

        for (uint256 i = 0; i < recipients.length; i++) {
            (bool ok, ) = recipients[i].call{value: amounts[i], gas: 3000}("");
            emit Distributed(recipients[i], amounts[i], ok);
        }

        // Refund remaining funds to caller
        uint256 remaining = address(this).balance;
        if (remaining > 0) {
            (bool refundOk, ) = msg.sender.call{value: remaining}("");
            require(refundOk, "refund failed");
        }
    }
}

contract Airdrop is Script {
    function run() external {
        // ============ Airdrop Parameters (Agent generates based on user input) ============
        address[] memory recipients = new address[](<count>);
        uint256[] memory amounts = new uint256[](<count>);

        recipients[0] = <addr1>; amounts[0] = <amount1>;
        recipients[1] = <addr2>; amounts[1] = <amount2>;
        // ... more addresses
        // ==============================================================

        uint256 total = 0;
        for (uint256 i = 0; i < amounts.length; i++) {
            total += amounts[i];
        }

        console.log("=== Airdrop (Distributor) ===");
        console.log("Recipients:", recipients.length);
        console.log("Total (wei):", total);

        vm.startBroadcast();

        // Deploy temporary distributor contract and complete all transfers in one transaction
        NativeDistributor dist = new NativeDistributor();
        dist.distribute{value: total}(recipients, amounts);

        console.log("=== Airdrop Complete ===");

        vm.stopBroadcast();
    }
}
```

#### ERC20 Token — Distributor Mode

Agent generates `AirdropERC20.s.sol` in the user's project `script/` directory:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "forge-std/console.sol";

interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
    function decimals() external view returns (uint8);
    function symbol() external view returns (string memory);
}

contract ERC20Distributor {
    event Distributed(address indexed recipient, uint256 amount, bool success);

    function distribute(
        address token,
        address from,
        address[] calldata recipients,
        uint256[] calldata amounts
    ) external {
        require(recipients.length == amounts.length, "length mismatch");

        for (uint256 i = 0; i < recipients.length; i++) {
            try IERC20(token).transferFrom(from, recipients[i], amounts[i]) returns (bool ok) {
                emit Distributed(recipients[i], amounts[i], ok);
            } catch {
                emit Distributed(recipients[i], amounts[i], false);
            }
        }
    }
}

contract AirdropERC20 is Script {
    function run() external {
        // ============ Airdrop Parameters (Agent generates based on user input) ============
        address token = <token_address>;

        address[] memory recipients = new address[](<count>);
        uint256[] memory amounts = new uint256[](<count>);

        recipients[0] = <addr1>; amounts[0] = <amount1>;
        recipients[1] = <addr2>; amounts[1] = <amount2>;
        // ... more addresses
        // ==============================================================

        uint256 total = 0;
        for (uint256 i = 0; i < amounts.length; i++) {
            total += amounts[i];
        }

        IERC20 erc20 = IERC20(token);
        console.log("=== ERC20 Airdrop (Distributor) ===");
        console.log("Token:", erc20.symbol());
        console.log("Decimals:", erc20.decimals());
        console.log("Sender balance:", erc20.balanceOf(msg.sender));
        console.log("Recipients:", recipients.length);
        console.log("Total:", total);

        vm.startBroadcast();

        // Deploy temporary distributor contract
        ERC20Distributor dist = new ERC20Distributor();
        // Approve distributor contract to use tokens
        erc20.approve(address(dist), total);
        // Complete all transfers in one transaction
        dist.distribute(token, msg.sender, recipients, amounts);

        console.log("=== Airdrop Complete ===");

        vm.stopBroadcast();
    }
}
```

---

### Execute Airdrop Script

```bash
# Native token airdrop
forge script script/Airdrop.s.sol:Airdrop \
  --rpc-url <rpc> \
  --private-key $PRIVATE_KEY \
  --broadcast

# ERC20 token airdrop
forge script script/AirdropERC20.s.sol:AirdropERC20 \
  --rpc-url <rpc> \
  --private-key $PRIVATE_KEY \
  --broadcast
```

### Error Handling

| Error Signature | Cause | Suggested Action |
|----------------|-------|-----------------|
| `transfer failed` (simple mode) | Native transfer failed (recipient is a contract that doesn't accept ETH) | Check if recipient address is an EOA or a contract that supports receiving native tokens |
| `transferFrom failed` (simple mode) | ERC20 transferFrom failed (insufficient approval or balance) | Check approve allowance and sender balance |
| `Distributed(..., false)` event (Distributor mode) | Individual transfer failed, but doesn't block the entire batch | Check Distributed event logs, identify failed recipient addresses; failed funds are refunded to caller |
| `length mismatch` | recipients and amounts arrays have different lengths | Check that generated address and amount counts match |
| `ERC20: transfer amount exceeds balance` | Sender token balance insufficient | Prompt to check balance first, ensure balance ≥ sum of all transfer amounts |
| `insufficient funds` | Native token balance insufficient (transfer amount + Gas) | Prompt insufficient balance, check via `cast balance` |
| `compiler error` | Script compilation failed | Check address format and amounts are correct |
| `connection refused` | Missing `--rpc-url` | Confirm `--rpc-url` is explicitly passed |

> **Agent Guidelines**: The complete batch transfer/airdrop flow is:
> 1. Complete "Write Operation Pre-checks" (see SKILL.md)
> 2. Confirm airdrop type: native token or ERC20 token
> 3. If ERC20, confirm token contract address (check `assets/tokens.json` for known tokens)
> 4. Collect user's recipient addresses and amounts list (supports direct input or CSV file path)
> 5. Calculate total transfer amount
> 6. **Automatic balance check** (execute directly without asking user):
>    - Native token airdrop: `cast balance <sender> --rpc-url <rpc>`, confirm balance ≥ total transfer amount + estimated Gas fees
>    - ERC20 airdrop: `cast call <token> "balanceOf(address)" <sender> --rpc-url <rpc>`, confirm token balance ≥ total transfer amount
>    - If balance is insufficient, inform user of the shortfall directly without executing the airdrop
> 7. Display total amount and recipient count to user, continue after confirmation
> 8. Automatically select mode based on address count (see "Automatic Mode Selection"): ≤ 10 use simple mode, 11-200 use single-batch Distributor, > 200 use multi-batch Distributor
> 9. Generate the corresponding airdrop script in the user's project `script/` directory
> 10. Read the target network's `rpcUrl` from `assets/networks.json`
> 11. Execute `forge script` (must include `--rpc-url`, `--private-key $PRIVATE_KEY`, `--broadcast`)
> 12. Display airdrop results to user with block explorer link (`<explorerUrl>/address/<sender>`)

---

### Automatic Mode Selection

The Agent automatically selects the optimal execution mode based on the number of recipient addresses, without requiring manual user specification:

| Address Count | Mode | Description |
|--------------|------|-------------|
| ≤ 10 | Simple | Sequential `call` transfers within script, no contract deployment needed, suitable for small-scale airdrops |
| 11 ~ 200 | Single-batch Distributor (SingleBatch) | Deploy hardened distributor contract, complete all transfers in one transaction, high Gas efficiency |
| > 200 | Multi-batch Distributor (MultiBatch) | Deploy hardened distributor contract, call distribute in batches (default 200 addresses per batch), bypassing single-transaction Gas limit |

**Selection Logic** (implemented in `assets/airdrop/AirdropHelper.sol`'s `_selectMode` function):

```solidity
function _selectMode(uint256 count, uint256 batchSize) internal pure returns (AirdropMode) {
    if (count <= 10) return AirdropMode.Simple;
    else if (count <= batchSize) return AirdropMode.SingleBatch;
    else return AirdropMode.MultiBatch;
}
```

- Default `batchSize = 200`, user can customize via `BATCH_SIZE` environment variable
- When user specifies a custom `batchSize`, 11 ~ `batchSize` range uses single-batch mode, above `batchSize` uses multi-batch mode

---

### CSV File Support

When the number of recipient addresses is large (especially > 200), it's recommended to use an external CSV file for the address list, avoiding hardcoding large numbers of addresses in the Solidity script which could exceed contract code size limits.

#### CSV Format Requirements

- One record per line: `<address>,<amount>`
- Optional header row: `address,amount` (auto-detected and skipped)
- Address format: `0x` + 40 hex characters (42 characters total)
- Amount: positive integer (wei units or raw token units including decimals)

#### CSV File Example

```csv
address,amount
0x1234567890abcdef1234567890abcdef12345678,1000000000000000000
0xabcdefabcdefabcdefabcdefabcdefabcdefabcd,2000000000000000000
0x1111111111111111111111111111111111111111,500000000000000000
```

#### CSV Parsing Logic

CSV parsing is implemented by the `_readCSV` function in `assets/airdrop/AirdropHelper.sol`, using Foundry's `vm.readFile` to read file contents, then parsing line by line:

1. Split file contents by newline
2. Detect and skip optional header row (`address,amount`)
3. Split each line by comma into address and amount
4. Use `vm.parseAddress` to parse addresses, `vm.parseUint` to parse amounts
5. Address format validation: check `0x` prefix and 42-character length, revert with line number on invalid
6. Amount format validation: revert with line number on parse failure

#### CSV-Related Errors

| Error Signature | Cause | Suggested Action |
|----------------|-------|-----------------|
| `vm.readFile` revert | CSV file path does not exist or is unreadable | Check file path is correct, confirm file exists in project root directory |
| `CSV parse error at line N: invalid address format` | Line N address format invalid (not `0x` prefixed or length not 42) | Check address format on line N of CSV file |
| `CSV parse error at line N: invalid amount format` | Line N amount format invalid (not a positive integer) | Check amount value on line N of CSV file |
| `CSV parse error at line N: missing comma delimiter` | Line N missing comma separator | Check format on line N of CSV file |

---

### Multi-Batch Airdrop Mode

When the number of recipient addresses exceeds 200 (or custom `batchSize`), multi-batch mode is automatically activated. This mode deploys a hardened distributor contract, then calls the `distribute` method in batches, with each batch as an independent on-chain transaction.

#### Use Cases

- Recipient address count > 200
- Single-transaction Gas consumption may exceed block Gas limit
- Large-scale airdrops (e.g., 6000+ addresses)

#### Script Templates

Multi-batch airdrops use pre-built script templates located in the `assets/airdrop/` directory:

| Script File | Purpose | Description |
|-------------|---------|-------------|
| `assets/airdrop/BatchAirdrop.s.sol` | Native token multi-batch airdrop | Inherits AirdropHelper, reads CSV → deploys NativeDistributor → distributes in batches |
| `assets/airdrop/BatchAirdropERC20.s.sol` | ERC20 token multi-batch airdrop | Inherits AirdropHelper, reads CSV → deploys ERC20Distributor → approve → distributes in batches |

#### Environment Variable Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `CSV_PATH` | `airdrop.csv` | CSV file path (relative to project root) |
| `BATCH_SIZE` | `200` | Maximum addresses per batch |
| `TOKEN_ADDRESS` | None (required, ERC20 only) | ERC20 token contract address |

#### Execution Commands

```bash
# Native token multi-batch airdrop
CSV_PATH=airdrop.csv BATCH_SIZE=200 \
  forge script assets/airdrop/BatchAirdrop.s.sol:BatchAirdrop \
  --rpc-url <rpc> \
  --private-key $PRIVATE_KEY \
  --broadcast

# ERC20 token multi-batch airdrop
CSV_PATH=airdrop.csv BATCH_SIZE=200 TOKEN_ADDRESS=<token_address> \
  forge script assets/airdrop/BatchAirdropERC20.s.sol:BatchAirdropERC20 \
  --rpc-url <rpc> \
  --private-key $PRIVATE_KEY \
  --broadcast
```

---

### Agent Multi-Batch Operation Flow

When the Agent determines multi-batch mode is needed (address count > 200 or user provides CSV file), follow this flow:

> **Step 1: Parse CSV and Display Summary**
>
> Parse the user-provided CSV file and display the following information:
> - Total recipient address count
> - Total transfer amount
> - Preview of first 5 records (address + amount)
>
> Wait for user confirmation that data is correct before continuing.

> **Step 2: Display Batch Plan and Wait for Confirmation**
>
> Based on address count and batch size, display the batch split plan:
> - Addresses per batch (batchSize)
> - Expected batch count: `ceil(total addresses / batchSize)`
> - Execution mode (Simple / SingleBatch / MultiBatch)
>
> Wait for user confirmation before starting execution.

> **Step 3: Execute Batches and Report Progress**
>
> Execute each batch sequentially, reporting after each batch:
> - Batch number (e.g., `Batch 3/15`)
> - Address range for this batch (e.g., `Recipients [400..599]`)
> - Transaction hash for this batch
> - Transaction status (success/failed)
>
> If a batch fails, record the failure and continue with subsequent batches.

> **Step 4: Display Summary Statistics**
>
> After all batches complete, display the final summary:
> - Total batch count
> - Total recipient count
> - Total transfer amount
> - Successful batches / Failed batches
> - Block explorer link

---

### Multi-Batch Error Handling

| Error Signature | Cause | Suggested Action |
|----------------|-------|-----------------|
| CSV file not found | `vm.readFile` cannot read the file at specified path | Check CSV file path is correct, confirm file exists in project root directory |
| `CSV parse error at line N: invalid address format` | CSV line N address format invalid (not `0x` prefixed or length not 42 characters) | Check address on line N of CSV file, ensure format is `0x` + 40 hex characters |
| `CSV parse error at line N: invalid amount format` | CSV line N amount format invalid (not a positive integer) | Check amount value on line N of CSV file, ensure it's a positive integer |
| `Batch X failed` | Batch X distribute call execution failed | Check transaction logs for that batch, investigate if failure was due to insufficient Gas or contract anomaly; subsequent batches will continue executing |
