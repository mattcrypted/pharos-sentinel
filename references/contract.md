# Contract Operation Instructions

This file contains detailed instructions for all contract operations on the Pharos chain, covering contract deployment, contract verification, and ERC20 one-click deployment.

> **Network Configuration**: The `<rpc>` parameter in all commands is read from the corresponding network's `rpcUrl` field in `assets/networks.json`. Defaults to the Atlantic testnet. **The `--rpc-url` parameter must be explicitly passed**, otherwise `forge` / `cast` will default to connecting to `localhost:8545`, causing connection failure.
>
> **Private Key Configuration**: All write operations must explicitly pass the private key via the `--private-key` parameter. Recommended to use environment variable: `--private-key $PRIVATE_KEY`. `forge` / `cast` do not automatically read environment variables; they must be explicitly referenced in the command.

---

## Deploy Contract (forge script)

### General Deployment Flow

For any Solidity contract in the user's project, the Agent can automatically generate a corresponding `forge script` deployment script and execute it. All operations are completed in the user's project directory, and contract source code and deployment scripts remain in the user's project.

**Step 1: Analyze User Contract**

Read the user's contract source code and extract the following information:
- Contract name (`contract` declaration)
- Constructor parameters (types and names)
- Import dependencies

**Step 2: Generate Deployment Script**

Generate `Deploy<ContractName>.s.sol` in the user's project `script/` directory with the following structure:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "forge-std/console.sol";
import "<relative path to user contract>";

contract Deploy<ContractName> is Script {
    function run() external {
        // ============ Deployment Parameters (fill based on user input) ============
        // Generate variable declarations based on constructor parameters
        // ==============================================================

        vm.startBroadcast();

        <ContractName> instance = new <ContractName>(/* constructor arguments */);

        console.log("=== Deploy Result ===");
        console.log("Contract address:", address(instance));
        console.log("Deployer:", msg.sender);
        // Output key state based on contract's public methods

        vm.stopBroadcast();
    }
}
```

**Step 3: Execute Deployment Script**

```bash
forge script script/Deploy<ContractName>.s.sol:Deploy<ContractName> \
  --rpc-url <rpc> \
  --private-key $PRIVATE_KEY \
  --broadcast
```

**Output Parsing**

After successful script execution, `console.log` outputs the contract address and key state information. Transaction record JSON files are also generated in the `broadcast/` directory.

**Error Handling**

| Error Signature | Cause | Suggested Action |
|----------------|-------|-----------------|
| Command missing `--private-key` | Private key not provided | Prompt user to pass explicitly via `--private-key $PRIVATE_KEY` |
| `compiler error` | Contract compilation failed | Check contract source code, dependencies, and remappings |
| `execution reverted` | Constructor execution reverted | Extract revert reason, prompt user to check constructor parameters |
| `insufficient funds` | Account balance insufficient | Prompt insufficient balance, suggest checking current balance |
| `connection refused` / connection timeout | Missing `--rpc-url` or RPC unreachable | Confirm `--rpc-url` is explicitly passed, check network connection |

> **Agent Guidelines**: The complete flow for deploying any contract is:
> 1. Complete "Write Operation Pre-checks" (see SKILL.md)
> 2. Read user contract source code, analyze contract name and constructor signature
> 3. Confirm constructor parameter values with user
> 4. **Automatic balance check**: Query deployer balance via `cast balance <deployer> --rpc-url <rpc>`, confirm balance is sufficient for deployment Gas fees. If insufficient, inform user directly without executing deployment
> 5. Generate `Deploy<ContractName>.s.sol` in user's project `script/` directory, with import path pointing to the actual location of the user's contract
> 6. Read target network's `rpcUrl` from `assets/networks.json`
> 7. Execute `forge script` in user's project directory (must include `--rpc-url`, `--private-key $PRIVATE_KEY`, `--broadcast`)
> 8. Extract contract address from output, display deployment result with block explorer link (`<explorerUrl>/address/<contractAddress>`)
> 9. Ask user if they want to verify the contract source code. **If yes, wait ~10 seconds before executing the verification command** — the block explorer's indexer needs time to process the deployment transaction; verifying immediately will trigger database query errors (`psycopg2` / SQL errors) and cause `forge verify-contract` to retry repeatedly until the indexer catches up

---

### Deploy via Compiled Bytecode

**Command Template**

> ⚠️ **Parameter order matters**: `--private-key` and `--rpc-url` must be placed **before** `--create`, otherwise `cast` will treat them as arguments to `--create`, causing parsing errors.

```bash
cast send \
  --private-key $PRIVATE_KEY \
  --rpc-url <rpc> \
  --create <bytecode>
```

If the contract has constructor parameters, first encode them with `cast abi-encode`, then append to the bytecode:

```bash
# Get bytecode
BYTECODE=$(forge inspect <path>:<ContractName> bytecode)

# Encode constructor arguments
CONSTRUCTOR_ARGS=$(cast abi-encode "constructor(<param_types>)" <args...>)

# Concatenate and deploy (note --create goes last)
cast send \
  --private-key $PRIVATE_KEY \
  --rpc-url <rpc> \
  --create ${BYTECODE}${CONSTRUCTOR_ARGS#0x}
```

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `<bytecode>` | string | Yes | Compiled contract bytecode, hex string (starting with `0x`). If constructor parameters exist, append ABI-encoded arguments to the end of bytecode |
| `<key>` | string | Yes | Deployer private key, or use environment variable `$PRIVATE_KEY` |
| `<rpc>` | string | Yes | RPC endpoint URL, read from `assets/networks.json` |

**Output Parsing**

`cast send --create` waits for transaction confirmation by default and outputs the transaction receipt with the following key fields:

| Field | Description |
|-------|-------------|
| `status` | Transaction status: `1` = success, `0` = failed |
| `contractAddress` | Newly deployed contract address |
| `transactionHash` | Deployment transaction hash |
| `gasUsed` | Actual Gas consumed |
| `blockNumber` | Block number containing the transaction |

Extract `contractAddress` from the output as the contract address.

**Error Handling**

| Error Signature | Cause | Suggested Action |
|----------------|-------|-----------------|
| Command missing `--private-key` | Private key not provided | Prompt user to configure via `--private-key` parameter or `$PRIVATE_KEY` environment variable |
| `invalid bytecode` / invalid hex | Invalid bytecode format | Prompt that bytecode must be a hex string starting with `0x` |
| `insufficient funds` | Account balance insufficient | Prompt insufficient balance, suggest checking current balance |
| `status` is `0` | Deployment transaction execution failed | Extract failure reason, possibly constructor revert or invalid bytecode |
| Connection timeout / `connection refused` | RPC node unreachable | Check network connection and RPC URL |

> **Agent Guidelines**: `cast send --create` (bytecode deployment) is suitable when the user already has compiled bytecode. Complete "Write Operation Pre-checks" (see SKILL.md) before execution. Automatically query deployer balance via `cast balance <deployer> --rpc-url <rpc>`, confirm balance is sufficient for deployment Gas fees; if insufficient, inform user directly without executing deployment. After successful deployment, display contract address, transaction hash, and include block explorer links: contract address `<explorerUrl>/address/<contractAddress>`, deployment transaction `<explorerUrl>/tx/<transactionHash>`. After deployment, ask user if they want to verify the contract source code on the block explorer. **If yes, wait ~10 seconds before executing the verification command** to allow the Explorer indexer to process the deployment transaction.

---

## Verify Contract

### forge verify-contract Command

**Command Template**

```bash
forge verify-contract <address> <path>:<ContractName> \
  --chain-id <chain_id> \
  --verifier-url <explorer_api_url> \
  --verifier blockscout \
  --constructor-args $(cast abi-encode "constructor(<param_types>)" <args...>)
```

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `<address>` | string | Yes | Deployed contract address |
| `<path>` | string | Yes | Solidity source file path |
| `<ContractName>` | string | Yes | Contract name |
| `<chain_id>` | number | Yes | Chain ID, read from `chainId` field in `assets/networks.json` |
| `<explorer_api_url>` | string | Yes | Block explorer API URL, read from `explorerApiUrl` field in `assets/networks.json` |
| `<param_types>` | string | Conditional | Constructor parameter type list, comma-separated (omit `--constructor-args` when no constructor parameters) |
| `<args...>` | any | Conditional | Constructor parameter values, passed in order |

**Network Parameter Reference**

| Network | chain_id | explorer_api_url |
|---------|----------|-----------------|
| Atlantic Testnet | `688689` | `https://api.socialscan.io/pharos-atlantic-testnet` |
| Mainnet | `1672` | `https://api.socialscan.io/pharos-mainnet` |

**Output Parsing**

- Successful verification outputs a message containing `Contract successfully verified` or similar
- Verification may take time; `forge verify-contract` automatically polls verification status
- After successful verification, users can view the verified contract source code on the block explorer (`<explorerUrl>/address/<address>`)

**Error Handling**

| Error Signature | Cause | Suggested Action |
|----------------|-------|-----------------|
| `contract not found` / invalid contract address | No deployed contract at the provided address | Prompt "contract address invalid or not deployed", suggest user confirm contract address and target network |
| `verification failed` / source code mismatch | Submitted source code doesn't match on-chain bytecode | Prompt verification failed, possible causes: inconsistent source version, different compiler version, different optimization settings |
| `constructor arguments mismatch` | Constructor argument encoding incorrect | Prompt user to check `--constructor-args` parameter types and values match those used during deployment |
| `invalid chain id` | Incorrect chain ID | Prompt user to confirm target network, read correct `chainId` from `assets/networks.json` |
| Connection timeout / API error | Block explorer API unreachable | Check network connection and `explorerApiUrl` |

> **Agent Guidelines**: Before verifying a contract, confirm the user has provided the correct contract address and source code path. Read the current network's `chainId` and `explorerApiUrl` from `assets/networks.json`. If the contract has constructor parameters, encode them using `cast abi-encode`. **If verification is performed immediately after deployment (in the same session), wait ~10 seconds before executing the verification command** — the block explorer's indexer needs time to write the deployment transaction into its database; verifying too soon will trigger `psycopg2` SQL errors and cause `forge verify-contract` to retry repeatedly. The retries will eventually succeed once the indexer catches up, but the delay avoids unnecessary noise. After successful verification, provide the block explorer link: `<explorerUrl>/address/<address>` to view the verified source code.

---

## ERC20 One-Click Deploy (Built-in Template)

ERC20 deployment is a shortcut for the general `forge script` deployment flow. The Skill includes a built-in standard ERC20 contract template (`assets/erc20/StandardERC20.sol`). The Agent copies it to the user's project, then automatically generates a deployment script and executes it following the general flow.

### Deployment Flow

ERC20 one-click deployment uses the `forge script` approach. The Agent copies the Skill's contract template and deployment script to the user's project, modifies them with user parameters, and executes the deployment. All files remain in the user's project for review and management.

**Step 1: Prepare Files in User's Project**

Copy the Skill's `assets/erc20/StandardERC20.sol` to the user's project (e.g., `src/erc20/StandardERC20.sol`), then the Agent follows the general deployment flow to auto-generate the deployment script.

**Step 2: Ensure User Project's Foundry Configuration is Correct**

The user project's `foundry.toml` needs to include OpenZeppelin remapping. If not present, prompt the user:

```bash
# Install OpenZeppelin dependency (if not already installed)
forge install OpenZeppelin/openzeppelin-contracts

# Ensure foundry.toml has the remapping
# remappings = ["@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/"]
```

**Step 3: Agent Auto-generates Deployment Script with Parameters**

The Agent follows the general deployment flow, reads the `StandardERC20.sol` constructor signature, generates the deployment script in the user's project `script/` directory, and fills in user-provided parameters.

**User-Provided Parameters**

| Parameter | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `name_` | string | Non-empty | Token name, e.g., `"Akio Token"` |
| `symbol_` | string | Non-empty | Token symbol, e.g., `"ATOKEN"` |
| `decimals_` | uint8 | ≤ 18 | Token precision, typically `18`, `8`, `6` |
| `initialSupply_` | uint256 | > 0 | Initial supply (contract automatically multiplies by `10^decimals`) |

**Step 4: Execute Deployment Script in User's Project**

```bash
forge script script/DeployStandardERC20.s.sol:DeployStandardERC20 \
  --rpc-url <rpc> \
  --private-key $PRIVATE_KEY \
  --broadcast \
  --skip-simulation
```

**Deployment Example**

```bash
forge script script/DeployStandardERC20.s.sol:DeployStandardERC20 \
  --rpc-url https://atlantic.dplabs-internal.com \
  --private-key $PRIVATE_KEY \
  --broadcast \
  --skip-simulation
```

**Output Parsing**

After successful script execution, `console.log` outputs the following information:

| Output Field | Description |
|-------------|-------------|
| `Token address:` | Newly deployed ERC20 token contract address |
| `Name:` | Token name |
| `Symbol:` | Token symbol |
| `Decimals:` | Token precision |
| `Total supply:` | Total supply (already multiplied by `10^decimals`) |
| `Deployer balance:` | Token amount held by deployer |
| `Deployer:` | Deployer address |

After successful deployment, the entire initial supply (`initialSupply × 10^decimals`) is allocated to the deployer address.

**Error Handling**

| Error Signature | Cause | Suggested Action |
|----------------|-------|-----------------|
| Command missing `--private-key` | Private key not provided | Prompt user to pass explicitly via `--private-key $PRIVATE_KEY` |
| `revert: decimals must be <= 18` | decimals parameter exceeds 18 | Prompt user that decimals must be ≤ 18 |
| `revert: initialSupply must be > 0` | initialSupply is 0 | Prompt user that initialSupply must be greater than 0 |
| `insufficient funds` | Account balance insufficient | Prompt insufficient balance, suggest checking current balance |
| `compiler error` | Contract compilation failed | Check if OpenZeppelin dependency is installed and remapping is correct |
| `connection refused` / connection timeout | Missing `--rpc-url` or RPC unreachable | Confirm `--rpc-url` is explicitly passed, check network connection |

---

### Post-Deployment Verification (Optional)

After successful deployment, optionally verify the contract source code on the block explorer:

**Command Template**

```bash
forge verify-contract <deployed_address> src/erc20/StandardERC20.sol:StandardERC20 \
  --chain-id <chain_id> \
  --verifier-url <explorer_api_url>/v1/explorer/command_api/contract \
  --verifier blockscout \
  --constructor-args $(cast abi-encode "constructor(string,string,uint8,uint256)" "<name>" "<symbol>" <decimals> <initialSupply>)
```

**Verification Example**

```bash
forge verify-contract 0x1234...abcd src/erc20/StandardERC20.sol:StandardERC20 \
  --chain-id 688689 \
  --verifier-url https://api.socialscan.io/pharos-atlantic-testnet/v1/explorer/command_api/contract \
  --verifier blockscout \
  --constructor-args $(cast abi-encode "constructor(string,string,uint8,uint256)" "Akio Token" "ATOKEN" 6 100)
```

**Error Handling**

Same as the "Verify Contract" section error handling table.

> **Agent Guidelines**: The complete ERC20 one-click deployment flow is:
> 1. Complete "Write Operation Pre-checks" (see SKILL.md)
> 2. Confirm token parameters are valid (decimals ≤ 18, initialSupply > 0)
> 3. **Automatic balance check**: Query deployer balance via `cast balance <deployer> --rpc-url <rpc>`, confirm balance is sufficient for deployment Gas fees. If insufficient, inform user directly without executing deployment
> 4. Copy the Skill's `assets/erc20/StandardERC20.sol` to the user's project (e.g., `src/erc20/`)
> 5. Ensure user project has OpenZeppelin dependency installed and remapping is correct
> 6. Agent follows the general deployment flow to auto-generate `script/DeployStandardERC20.s.sol` with user parameters
> 7. Read target network's `rpcUrl` from `assets/networks.json`
> 8. Execute `forge script` command in user's project directory (must include `--rpc-url`, `--private-key $PRIVATE_KEY`, `--broadcast`)
> 9. Extract contract address from output, display deployment result with block explorer link (`<explorerUrl>/address/<tokenAddress>`)
> 10. Ask user if they want to verify the contract source code; if yes, **wait ~10 seconds before executing the verification command** to allow the Explorer indexer to process the deployment transaction, then execute the verification command
