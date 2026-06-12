# Contract Interaction Script Generation Instructions

This file contains detailed instructions for generating contract interaction scripts on the Pharos chain. The Agent automatically generates ready-to-run interaction scripts based on contract information provided by the user (ABI JSON, method signatures, or Solidity source files), supporting JavaScript (ethers.js v6), TypeScript (viem), and Python (web3.py), covering both read methods (call) and write methods (send transaction).

> **Network Configuration**: The RPC URL and Chain ID embedded in generated scripts are read from `assets/networks.json`. Defaults to the Atlantic testnet.
>
> **Template Files**: Scripts are generated based on template files (`.tpl` suffix) in the `assets/templates/` directory. The Agent reads templates and replaces placeholders to generate the final script.

---

## Contract Information Parsing

The Agent supports three types of contract information input. Upon receiving a user request, determine the input type using the following rules and execute the corresponding parsing flow.

### Method A: Complete ABI JSON

**Use Case**: User directly provides the contract's ABI JSON array.

**Parsing Flow**:

1. **Validate JSON format**: Attempt to parse the user-provided string as a JSON array. If parsing fails, handle as "Invalid ABI format" error (see error handling rules below)
2. **Extract function entries**: Iterate through the ABI array, filter entries where `type === "function"`
3. **Classify read/write**: Classify each function entry based on its `stateMutability` field:
   - **Read methods**: `stateMutability` is `"view"` or `"pure"`
   - **Write methods**: `stateMutability` is `"nonpayable"` or `"payable"`
4. **Extract method information**: For each function entry, extract the following:

| Field | Source | Description |
|-------|--------|-------------|
| `name` | ABI entry's `name` field | Method name |
| `inputs` | ABI entry's `inputs` array | Parameter list, each item contains `name` and `type` |
| `outputs` | ABI entry's `outputs` array | Return value list, each item contains `name` and `type` |
| `stateMutability` | ABI entry's `stateMutability` field | `"view"` / `"pure"` / `"nonpayable"` / `"payable"` |

5. **Display method list**: Show parsing results to user, listing all method names and parameter types grouped by read/write, then proceed to script generation after confirmation

**ABI Entry Example**:

```json
{
  "type": "function",
  "name": "transfer",
  "inputs": [
    { "name": "to", "type": "address" },
    { "name": "amount", "type": "uint256" }
  ],
  "outputs": [
    { "name": "", "type": "bool" }
  ],
  "stateMutability": "nonpayable"
}
```

---

### Method B: Method Signature Strings

**Use Case**: User provides one or more method signature strings, e.g., `transfer(address,uint256)` or `balanceOf(address)`.

**Parsing Flow**:

1. **Parse method signature**: Extract method name and parameter type list from the signature string
   - Method name: part before parentheses (e.g., `transfer`)
   - Parameter types: comma-separated type list inside parentheses (e.g., `address,uint256`)
   - No parameters when parentheses are empty (e.g., `totalSupply()`)
2. **Infer read/write type**: Method signatures don't include `stateMutability` information, so the Agent follows these rules:
   - **Common read method patterns** (auto-infer as read): method name starts with `get`, `is`, `has`, `check`, `query`, or is a standard read-only method like `balanceOf`, `totalSupply`, `name`, `symbol`, `decimals`, `owner`, `allowance`, `tokenURI`, `supportsInterface`
   - **Common write method patterns** (auto-infer as write): method name is `transfer`, `approve`, `mint`, `burn`, `set`, `update`, `withdraw`, `deposit`, `swap`, etc.
   - **When unable to infer**: Ask the user whether the method is read (read-only, no Gas cost) or write (requires sending a transaction)
3. **Build method information**:
   - `name`: parsed method name
   - `inputs`: parameter type list (parameter names use placeholder names like `arg0`, `arg1`)
   - `outputs`: method signatures don't include return value info; read methods default to empty (script outputs raw return value)
   - `stateMutability`: set based on inference or user confirmation

**Signature Parsing Example**:

```
Input: transfer(address,uint256)
Parse result:
  name = "transfer"
  inputs = [{ name: "arg0", type: "address" }, { name: "arg1", type: "uint256" }]
  stateMutability = "nonpayable" (inferred as write)

Input: balanceOf(address)
Parse result:
  name = "balanceOf"
  inputs = [{ name: "arg0", type: "address" }]
  stateMutability = "view" (inferred as read)
```

---

### Method C: Solidity Source File Path

**Use Case**: User provides a `.sol` file path, and the Agent extracts the ABI via Foundry tools.

**Parsing Flow**:

1. **Confirm file exists**: Check if the user-provided `.sol` file path exists
2. **Detect contract count**: Read the `.sol` file content, find all `contract <Name>` declarations
   - **Single contract**: Use that contract name directly
   - **Multiple contracts**: List all contract names and let the user select the target contract
3. **Execute forge inspect to extract ABI**:

```bash
forge inspect <path>:<ContractName> abi
```

| Parameter | Description |
|-----------|-------------|
| `<path>` | Solidity source file path (e.g., `src/MyToken.sol`) |
| `<ContractName>` | Contract name (e.g., `MyToken`) |

4. **Handle execution result**:
   - **Success**: `forge inspect` outputs an ABI JSON array, continue parsing per Method A steps 2-5
   - **Failure**: Display compilation error to user, suggest fixing contract code before retrying

**Multiple Contract Selection Example**:

```
Detected the following contracts in src/MyProject.sol:
1. MyToken
2. MyTokenFactory
3. IMyToken (interface)

Please select the target contract for script generation:
```

> **Note**: Interfaces (`interface`) and abstract contracts (`abstract contract`) are also recognized by `forge inspect`, but scripts are typically not needed for interfaces. The Agent should label types in the list to help users choose.

---

## Missing Contract Information Prompt Rules

When the user provides a contract address but no ABI JSON, method signatures, or `.sol` file path, the Agent should not guess the contract interface. Instead, prompt the user to provide contract information:

```
To generate a contract interaction script, I need the contract's interface information. Please provide one of the following:

1. **ABI JSON**: The contract's complete ABI JSON array (usually available from the contract page on the block explorer)
2. **Method signature**: The specific method signature to call, e.g., `transfer(address,uint256)`
3. **Solidity source file path**: The contract's .sol file path — I'll automatically extract the ABI via forge inspect
```

---

## Error Handling Rules

### Invalid ABI Format

When the user-provided ABI JSON format is invalid, return a clear error message:

| Error Scenario | Detection Method | Prompt Content |
|---------------|-----------------|----------------|
| Not JSON format | JSON parsing failed | "The provided ABI is not valid JSON format. Please check for syntax errors (e.g., missing quotes, commas)" |
| Not array format | Parse result is not an array | "ABI should be in JSON array format (starting with `[` and ending with `]`). The provided value is a different JSON type" |
| No function entries | No entries with `type === "function"` in array | "No callable function definitions (`type: \"function\"`) found in the ABI. Please confirm the complete contract ABI was provided" |

### Invalid Contract Address Format

When the user-provided contract address format doesn't meet specifications, return an error:

| Error Scenario | Detection Method | Prompt Content |
|---------------|-----------------|----------------|
| Missing `0x` prefix | Address doesn't start with `0x` | "Contract address should start with `0x`. Current address format is invalid" |
| Incorrect length | Address length is not 42 characters (including `0x`) | "Contract address should be 42 characters (`0x` + 40 hex characters). Current address length is incorrect" |
| Contains illegal characters | Address contains non-hex characters | "Contract address contains illegal characters. Address should only contain `0x` prefix and hex characters (0-9, a-f, A-F)" |

### forge inspect Failure

When the `forge inspect` command fails:

```
Contract compilation failed, unable to extract ABI. Here is the compilation error:

<compilation error output>

Suggestion: Please fix the compilation errors in the contract code first, then retry.
```

---

## Missing Contract Address Placeholder Rules

When the user only provides a `.sol` file path or ABI/method signatures without a contract address, the Agent uses a placeholder in the generated script:

- Set contract address to the string `"<CONTRACT_ADDRESS>"`
- Add a comment next to the placeholder prompting the user to fill in the actual address

**Placeholder Examples by Language**:

JavaScript / TypeScript:
```javascript
// TODO: After deploying the contract, replace the address below with the actual contract address
const CONTRACT_ADDRESS = "<CONTRACT_ADDRESS>";
```

Python:
```python
# TODO: After deploying the contract, replace the address below with the actual contract address
CONTRACT_ADDRESS = "<CONTRACT_ADDRESS>"
```

---

## Language Selection Rules

The Agent selects the corresponding script library and template based on the user-specified target language:

| Priority | Condition | Target Language | Library | File Extension |
|----------|-----------|----------------|---------|---------------|
| 1 | User explicitly specifies JavaScript / JS | JavaScript | ethers.js v6 | `.js` |
| 2 | User explicitly specifies TypeScript / TS | TypeScript | viem | `.ts` |
| 3 | User explicitly specifies Python / Py | Python | web3.py | `.py` |
| **Default** | **User does not specify language** | **JavaScript** | **ethers.js v6** | **`.js`** |

**Rules**:

- When the user does not specify a target language, **default to generating a JavaScript script** using ethers.js v6
- Users can specify language via natural language (e.g., "generate in TypeScript", "Python version"), and the Agent should recognize and match accordingly
- Each generation outputs only one language's script. If the user needs multiple language versions, they must request separately

**Dependency Installation Commands by Language**:

| Language | Install Command | Run Command Example |
|----------|----------------|-------------------|
| JavaScript | `npm install ethers` | `node scripts/interact_<ContractName>.js` |
| TypeScript | `npm install viem` | `npx tsx scripts/interact_<ContractName>.ts` |
| Python | `uv init && uv add web3` | `uv run scripts/interact_<ContractName>.py` |

**Python Environment Management (uv)**:

When the user selects Python, the Agent uses `uv` to manage virtual environments and dependencies instead of using `pip` directly. The Agent needs to check and initialize the Python environment before generating scripts:

1. **Check if uv is available**: Execute `which uv`. If unavailable, prompt user to install:
   ```
   uv (Python package manager) needs to be installed. Install via:
     curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. **Check if project is initialized**: Check if `pyproject.toml` exists in the user's project root
   - **Does not exist**: Execute `uv init` to initialize (automatically creates `pyproject.toml` and `.venv` virtual environment)
   - **Exists**: Skip initialization
3. **Install web3 dependency**: Execute `uv add web3` (automatically installs into `.venv`)
4. **Run script**: Use `uv run scripts/interact_<ContractName>.py` (`uv run` automatically activates the virtual environment)

> **Note**: The Agent should complete the above environment initialization steps before generating the script file, ensuring the user can run the script immediately after receiving it.

---

## Network Configuration Reading Rules

When generating scripts, the Agent reads the target network's RPC URL and Chain ID from `assets/networks.json` and embeds them as constants in the script.

### networks.json Structure

```json
{
  "networks": [
    {
      "name": "atlantic-testnet",
      "rpcUrl": "https://atlantic.dplabs-internal.com",
      "chainId": 688689,
      "explorerUrl": "https://atlantic.pharosscan.xyz/",
      "nativeToken": "PHRS"
    },
    {
      "name": "mainnet",
      "rpcUrl": "https://rpc.pharosnetwork.xyz",
      "chainId": 6889,
      "explorerUrl": "https://explorer.pharosnetwork.xyz",
      "nativeToken": "PROS"
    }
  ],
  "defaultNetwork": "atlantic-testnet"
}
```

### Reading Rules

| Scenario | Handling |
|----------|---------|
| User does not specify network | Read `defaultNetwork` field value (`atlantic-testnet`), use that network's `rpcUrl` and `chainId` |
| User specifies network name | Find the entry with matching `name` in the `networks` array, use its `rpcUrl` and `chainId` |
| User-specified network name doesn't exist | Return error prompt and list all available network names |

**Error Prompt Template for Non-existent Network**:

```
The specified network "<user input network name>" does not exist. Available network configurations:

- atlantic-testnet (default)
- mainnet

Please use one of the above network names, or add a custom network configuration in assets/networks.json.
```

**Embedding Method**: The Agent writes the `rpcUrl` and `chainId` values directly into the script's configuration constant area, with comments noting the network name. Runtime dynamic reading of `networks.json` is not used, since generated scripts run in the user's project which may not have that file.

---

## Template Mapping Table

The Agent selects the corresponding template file based on target language and method type (read/write). Template files are located in the `assets/templates/` directory with `.tpl` suffix to avoid IDE misidentification.

| Target Language | Method Type | Template File Path |
|----------------|-------------|-------------------|
| JavaScript | Read (view/pure) | `assets/templates/template_read.js.tpl` |
| JavaScript | Write (nonpayable/payable) | `assets/templates/template_write.js.tpl` |
| TypeScript | Read (view/pure) | `assets/templates/template_read.ts.tpl` |
| TypeScript | Write (nonpayable/payable) | `assets/templates/template_write.ts.tpl` |
| Python | Read (view/pure) | `assets/templates/template_read.py.tpl` |
| Python | Write (nonpayable/payable) | `assets/templates/template_write.py.tpl` |

**Template Selection Rules**:

1. Determine language dimension based on user-specified language (or default JavaScript)
2. Determine method type dimension based on method's `stateMutability`:
   - `stateMutability` is `"view"` or `"pure"` → Use Read template
   - `stateMutability` is `"nonpayable"` or `"payable"` → Use Write template
3. When a contract contains both read and write methods, the Agent reads the corresponding templates separately and merges both types of method function bodies into a single output script

---

## Placeholder Replacement Rules

After reading the template file, the Agent replaces placeholders with actual values to generate the final script file. Here are all placeholders and their replacement rules:

| Placeholder | Replacement Source | Description |
|-------------|-------------------|-------------|
| `{{DEPENDENCY_COMMENT}}` | Language selection rules | Dependency install command comment. JS → `npm install ethers`; TS → `npm install viem`; Python → `uv init && uv add web3` |
| `{{RPC_URL}}` | Target network's `rpcUrl` field from `assets/networks.json` | e.g., `https://atlantic.dplabs-internal.com` |
| `{{CHAIN_ID}}` | Target network's `chainId` field from `assets/networks.json` | e.g., `688689` |
| `{{NETWORK_NAME}}` | Target network's `name` field from `assets/networks.json` | e.g., `atlantic-testnet`, used in comment annotations |
| `{{CONTRACT_ADDRESS}}` | User-provided contract address, or placeholder `<CONTRACT_ADDRESS>` | Uses placeholder with TODO comment when user hasn't provided address |
| `{{ABI}}` | Parsed ABI JSON | Only includes entries where `type === "function"`, formatted as JSON array |
| `{{METHOD_FUNCTIONS}}` | Agent generates based on method list | Each method generates an independent call function body with parameter placeholders and type comments |
| `{{MAIN_EXAMPLE}}` | Agent generates based on method list | Main function example, calling the first method as a demo |

**Replacement Flow**:

1. Agent reads the complete template file content
2. Reads target network configuration from `assets/networks.json`, obtaining `rpcUrl`, `chainId`, `name`
3. Replace `{{RPC_URL}}`, `{{CHAIN_ID}}`, `{{NETWORK_NAME}}` with network configuration values
4. Replace `{{DEPENDENCY_COMMENT}}` with the corresponding language's dependency install command comment
5. Replace `{{CONTRACT_ADDRESS}}` with user-provided address or placeholder
6. Replace `{{ABI}}` with parsed ABI JSON array
7. Generate call function bodies for each method based on method list, replace `{{METHOD_FUNCTIONS}}`
8. Generate main function example based on method list, replace `{{MAIN_EXAMPLE}}`
9. Write final content to the user's project `scripts/` directory

---

## Read Method Script Generation Rules

The Agent generates an independent call function for each read method (`stateMutability` is `view` or `pure`), with a main function example at the end of the script.

### Independent Call Function Generation

For each read method in the ABI, the Agent generates an independent async function with the same name as the method. The function body contains:

1. **Parameter placeholders**: Each parameter uses a placeholder value with type comment describing the Solidity type
2. **Method call**: Calls the corresponding read-only method via the contract instance
3. **Return value formatting**: Converts BigNumber / BigInt type return values to readable decimal strings

**JavaScript (ethers.js v6) Example**:

Assuming the ABI contains `balanceOf(address)` and `allowance(address,address)` read methods, the Agent generates the following `{{METHOD_FUNCTIONS}}` content:

```javascript
/**
 * Query balanceOf
 * @param {string} arg0 - address: account address
 */
async function callBalanceOf(contract) {
  // TODO: Replace with actual parameter values
  const arg0 = "0x0000000000000000000000000000000000000000"; // address
  const result = await safeCall(contract, "balanceOf", arg0);
  console.log("balanceOf result:", result);
  return result;
}

/**
 * Query allowance
 * @param {string} arg0 - address: token holder address
 * @param {string} arg1 - address: spender address
 */
async function callAllowance(contract) {
  // TODO: Replace with actual parameter values
  const arg0 = "0x0000000000000000000000000000000000000000"; // address
  const arg1 = "0x0000000000000000000000000000000000000000"; // address
  const result = await safeCall(contract, "allowance", arg0, arg1);
  console.log("allowance result:", result);
  return result;
}
```

**TypeScript (viem) Example**:

```typescript
/**
 * Query balanceOf
 * @param arg0 - address: account address
 */
async function callBalanceOf(client: Awaited<ReturnType<typeof getClient>>) {
  // TODO: Replace with actual parameter values
  const arg0 = "0x0000000000000000000000000000000000000000"; // address
  const result = await safeRead(client, "balanceOf", [arg0]);
  console.log("balanceOf result:", result);
  return result;
}

/**
 * Query allowance
 * @param arg0 - address: token holder address
 * @param arg1 - address: spender address
 */
async function callAllowance(client: Awaited<ReturnType<typeof getClient>>) {
  // TODO: Replace with actual parameter values
  const arg0 = "0x0000000000000000000000000000000000000000"; // address
  const arg1 = "0x0000000000000000000000000000000000000000"; // address
  const result = await safeRead(client, "allowance", [arg0, arg1]);
  console.log("allowance result:", result);
  return result;
}
```

**Python (web3.py) Example**:

```python
def call_balance_of(contract):
    """
    Query balanceOf
    :param arg0: address - account address
    """
    # TODO: Replace with actual parameter values
    arg0 = "0x0000000000000000000000000000000000000000"  # address
    result = safe_call(contract, "balanceOf", arg0)
    print(f"balanceOf result: {result}")
    return result


def call_allowance(contract):
    """
    Query allowance
    :param arg0: address - token holder address
    :param arg1: address - spender address
    """
    # TODO: Replace with actual parameter values
    arg0 = "0x0000000000000000000000000000000000000000"  # address
    arg1 = "0x0000000000000000000000000000000000000000"  # address
    result = safe_call(contract, "allowance", arg0, arg1)
    print(f"allowance result: {result}")
    return result
```

### Parameter Placeholder Rules

The Agent generates corresponding placeholder values based on the parameter's Solidity type:

| Solidity Type | JS/TS Placeholder | Python Placeholder | Comment |
|--------------|-------------------|-------------------|---------|
| `address` | `"0x0000000000000000000000000000000000000000"` | `"0x0000000000000000000000000000000000000000"` | `// address` |
| `uint256` / `uint*` / `int256` / `int*` | `0` | `0` | `// uint256` |
| `bool` | `true` | `True` | `// bool` |
| `string` | `""` | `""` | `// string` |
| `bytes` / `bytes32` etc. | `"0x"` | `"0x"` | `// bytes32` |

If the ABI includes parameter names (non-empty strings), use the ABI parameter names as variable names; otherwise use placeholder names like `arg0`, `arg1`.

### Return Value Formatting Rules

All language templates include a `formatValue` (JS/TS) or `format_value` (Python) helper function for converting contract return values to readable format:

- **BigInt / BigNumber**: Convert to decimal string (e.g., `1000000000000000000` → `"1000000000000000000"`)
- **Arrays**: Recursively format each element
- **bytes**: Convert to `0x`-prefixed hex string
- **Other types**: Convert via `String()` / `str()`

### Main Function Example Generation Rules

- **Single read method**: Main function directly calls that method's function
- **Multiple read methods (≥ 2)**: Main function calls the first method as a demo, remaining methods listed as comments

**JavaScript main example**:

```javascript
// Call example — uncomment to call other methods
await callBalanceOf(contract);
// await callAllowance(contract);
```

**TypeScript main example**:

```typescript
// Call example — uncomment to call other methods
await callBalanceOf(client);
// await callAllowance(client);
```

**Python main example**:

```python
# Call example — uncomment to call other methods
call_balance_of(contract)
# call_allowance(contract)
```

---

## Write Method Script Generation Rules

The Agent generates an independent call function for each write method (`stateMutability` is `nonpayable` or `payable`). Write method scripts include private key loading, transaction sending, receipt parsing, and error handling.

### Private Key Loaded via Environment Variable

Write method scripts **never hardcode private keys or mnemonics**. Each language loads the private key from environment variables as follows:

| Language | Environment Variable Reading | Behavior When Not Set |
|----------|-----------------------------|-----------------------|
| JavaScript | `process.env.PRIVATE_KEY` | Output configuration prompt and `process.exit(1)` |
| TypeScript | `process.env.PRIVATE_KEY` | Output configuration prompt and `process.exit(1)` |
| Python | `os.environ.get("PRIVATE_KEY")` | Output configuration prompt and `sys.exit(1)` |

### Transaction Receipt Parsing

After each write transaction is sent, the script waits for confirmation and parses the receipt, outputting the following:

| Field | Description | JS/TS Source | Python Source |
|-------|-------------|-------------|--------------|
| Transaction hash | Transaction hash | `receipt.hash` / `receipt.transactionHash` | `receipt.transactionHash.hex()` |
| Block number | Block number | `receipt.blockNumber` | `receipt.blockNumber` |
| Gas used | Gas consumption | `receipt.gasUsed.toString()` | `receipt.gasUsed` |
| Status | Transaction status | `receipt.status === 1` (ethers) / `receipt.status === "success"` (viem) | `receipt.status == 1` |

### Payable Method Value Configuration

When a method's `stateMutability` is `payable`, the Agent includes a `value` parameter configuration in the generated function body:

- **JavaScript**: Pass via `overrides` object `{ value: ethers.parseEther("0.1") }`
- **TypeScript**: Generate `bigint` value via `parseEther("0.1")` and pass to `sendTransaction`
- **Python**: Generate wei value via `w3.to_wei(0.1, "ether")` and pass to `send_transaction`

For `nonpayable` methods, no `value` configuration is included.

### Revert Reason Extraction

All language write method templates include try-catch error capture logic that can extract and output the following error types:

| Error Type | JS (ethers.js) Detection | TS (viem) Detection | Python (web3.py) Detection |
|-----------|-------------------------|--------------------|-----------------------------|
| Contract revert | `error.reason` | `err.shortMessage` | `"revert" in error_msg` |
| Insufficient balance | `error.code === "INSUFFICIENT_FUNDS"` | `err.details` | `"insufficient funds" in error_msg` |
| Nonce conflict | `error.code === "NONCE_EXPIRED"` | `err.details` | `"nonce" in error_msg` |
| Other errors | `error.message` | `error.message` | `str(e)` |

### Write Method Function Body Examples

Assuming the ABI contains `transfer(address,uint256)` (nonpayable) and `deposit()` (payable) write methods:

**JavaScript (ethers.js v6) Example**:

```javascript
/**
 * Call transfer
 * @param {string} arg0 - address: recipient address
 * @param {number|string} arg1 - uint256: transfer amount
 */
async function callTransfer(contract) {
  // TODO: Replace with actual parameter values
  const arg0 = "0x0000000000000000000000000000000000000000"; // address
  const arg1 = 0; // uint256
  await sendTransaction(contract, "transfer", [arg0, arg1]);
}

/**
 * Call deposit (payable)
 * This method is payable and can include native token value
 */
async function callDeposit(contract) {
  // TODO: Set the amount of native tokens to send
  const overrides = { value: ethers.parseEther("0.0") };
  await sendTransaction(contract, "deposit", [], overrides);
}
```

**TypeScript (viem) Example**:

```typescript
/**
 * Call transfer
 * @param arg0 - address: recipient address
 * @param arg1 - uint256: transfer amount
 */
async function callTransfer(
  publicClient: Awaited<ReturnType<typeof getClients>>["publicClient"],
  walletClient: Awaited<ReturnType<typeof getClients>>["walletClient"]
) {
  // TODO: Replace with actual parameter values
  const arg0 = "0x0000000000000000000000000000000000000000"; // address
  const arg1 = 0n; // uint256
  await sendTransaction(publicClient, walletClient, "transfer", [arg0, arg1]);
}

/**
 * Call deposit (payable)
 * This method is payable and can include native token value
 */
async function callDeposit(
  publicClient: Awaited<ReturnType<typeof getClients>>["publicClient"],
  walletClient: Awaited<ReturnType<typeof getClients>>["walletClient"]
) {
  // TODO: Set the amount of native tokens to send
  const value = parseEther("0.0");
  await sendTransaction(publicClient, walletClient, "deposit", [], value);
}
```

**Python (web3.py) Example**:

```python
def call_transfer(w3, account, contract):
    """
    Call transfer
    :param arg0: address - recipient address
    :param arg1: uint256 - transfer amount
    """
    # TODO: Replace with actual parameter values
    arg0 = "0x0000000000000000000000000000000000000000"  # address
    arg1 = 0  # uint256
    send_transaction(w3, account, contract, "transfer", [arg0, arg1])


def call_deposit(w3, account, contract):
    """
    Call deposit (payable)
    This method is payable and can include native token value
    """
    # TODO: Set the amount of native tokens to send
    value = w3.to_wei(0, "ether")
    send_transaction(w3, account, contract, "deposit", value=value)
```

### Write Method Main Function Example

Similar to read methods, the main function calls the first write method as a demo, with the rest listed as comments:

**JavaScript**:

```javascript
await callTransfer(contract);
// await callDeposit(contract);
```

**TypeScript**:

```typescript
await callTransfer(publicClient, walletClient);
// await callDeposit(publicClient, walletClient);
```

**Python**:

```python
call_transfer(w3, account, contract)
# call_deposit(w3, account, contract)
```

---

## File Naming Rules

Generated script files follow this naming convention:

```
scripts/interact_<ContractName>.<ext>
```

| Component | Rule | Example |
|-----------|------|---------|
| Directory | Fixed as `scripts/` | `scripts/` |
| Prefix | Fixed as `interact_` | `interact_` |
| `<ContractName>` | Preserve original case of contract name, no conversion | `MyToken`, `ERC20`, `BatchAirdrop` |
| `<ext>` | Extension based on target language | `.js` (JavaScript), `.ts` (TypeScript), `.py` (Python) |

**Complete Examples**:

| Contract Name | Target Language | Generated File Path |
|--------------|----------------|-------------------|
| `MyToken` | JavaScript | `scripts/interact_MyToken.js` |
| `MyToken` | TypeScript | `scripts/interact_MyToken.ts` |
| `MyToken` | Python | `scripts/interact_MyToken.py` |
| `ERC20` | JavaScript | `scripts/interact_ERC20.js` |
| `BatchAirdrop` | Python | `scripts/interact_BatchAirdrop.py` |

**Merge Rule**: When a contract contains both read and write methods, the Agent merges both types of method function bodies into **a single file**, not generating separate read and write files. The Agent reads the read template and write template separately, extracts their helper functions and method function bodies, and merges them into a single output file.

---

## File Overwrite Confirmation Rules

When the target file path (e.g., `scripts/interact_MyToken.js`) already exists, the Agent must inform the user and wait for confirmation before writing:

**Prompt Template**:

```
Target file scripts/interact_<ContractName>.<ext> already exists. Continuing will overwrite the file contents.

Continue?
```

**Handling Rules**:

| Scenario | Agent Behavior |
|----------|---------------|
| Target file does not exist | Generate and write file directly |
| Target file already exists | Inform user file will be overwritten, wait for confirmation |
| User confirms overwrite | Write new content, overwriting original file |
| User declines overwrite | Do not write file, suggest user can change contract name or manually delete old file before retrying |

---

## Agent-Level Error Handling Table

The Agent may encounter the following errors during the process of receiving user requests, parsing contract information, and generating scripts. The Agent should return clear error prompts according to the handling methods in the table below.

| Error Scenario | Trigger Condition | Handling |
|---------------|-------------------|---------|
| Invalid ABI JSON format | User-provided JSON cannot be parsed, or parse result is not an array, or array has no `type === "function"` entries | Return clear format error prompt, specifying the exact parsing failure reason (see "Invalid ABI Format" error handling rules above) |
| Invalid contract address format | Address doesn't start with `0x`, length is not 42 characters, or contains non-hex characters | Return address format error prompt, explaining correct format is `0x` + 40 hex characters |
| `forge inspect` failure | `.sol` file has compilation errors causing `forge inspect` command to fail | Display complete compilation error to user, suggest fixing compilation errors in contract code before retrying |
| Network name doesn't exist | User-specified network name has no match in `assets/networks.json`'s `networks` array | Return error prompt, listing all available network names from `assets/networks.json` for user selection |
| Missing contract information | User only provided contract address without ABI JSON, method signatures, or `.sol` file path | Prompt user to provide one of: ABI JSON array, specific method signatures, or Solidity source file path |
| Multiple contracts not selected | `.sol` file contains multiple contract definitions but user hasn't specified target contract | List all contract names in the file (labeling interface/abstract contract types), let user select target contract |

**Core Principle**: When encountering errors, the Agent should not guess user intent or generate incomplete scripts. Instead, return clear error prompts and fix suggestions to guide the user to provide correct input.

---

## Error Handling Rules in Generated Scripts

Generated script files must include comprehensive error handling logic to ensure users get clear error prompts when running scripts. The following error handling rules must be included in scripts:

### RPC Connection Failure

Scripts must include try-catch error capture when connecting to the RPC Provider. On connection failure, output:

- The failed RPC URL
- Possible causes (network unreachable, incorrect RPC address, node not started, etc.)
- Suggestion to check network connection and RPC URL configuration

**Handling by Language**:

| Language | Capture Method | Output Content |
|----------|---------------|----------------|
| JavaScript | `try { ... } catch (error) { ... }` | `console.error("RPC connection failed:", RPC_URL, error.message)` |
| TypeScript | `try { ... } catch (error) { ... }` | `console.error("RPC connection failed:", RPC_URL, error.message)` |
| Python | `try: ... except Exception as e: ...` | `print(f"RPC connection failed: {RPC_URL}, reason: {e}")` |

### Private Key Not Configured

Write method scripts must check if the private key environment variable is set at startup. If not set, output a configuration prompt and exit without throwing an unreadable exception.

**Handling by Language**:

| Language | Check Method | Output When Not Set |
|----------|-------------|-------------------|
| JavaScript | `if (!process.env.PRIVATE_KEY)` | `console.error("Error: PRIVATE_KEY environment variable not set\nPlease set via:\nexport PRIVATE_KEY=your_private_key")` then `process.exit(1)` |
| TypeScript | `if (!process.env.PRIVATE_KEY)` | Same as JavaScript |
| Python | `if not os.environ.get("PRIVATE_KEY")` | `print("Error: PRIVATE_KEY environment variable not set\nPlease set via:\nexport PRIVATE_KEY=your_private_key")` then `sys.exit(1)` |

### Contract Call Revert

Every contract call (read and write) in the script must include try-catch error capture that can extract and output revert reasons:

- **Read methods**: Capture call exceptions, output revert reason or error message
- **Write methods**: Capture exceptions during transaction sending and confirmation, output revert reason, error codes (e.g., insufficient balance, nonce conflict)

When generating scripts, the Agent ensures the template's `safeCall` / `safe_call` (read) and `sendTransaction` / `send_transaction` (write) helper functions include complete error capture logic.

---

## Security Rules

The Agent must strictly follow these security rules when generating scripts to ensure user sensitive information is not leaked.

### Rule 1: Never Hardcode Private Keys or Mnemonics

- Generated scripts must **never contain** any hardcoded private keys (64-character hex strings) or mnemonics (12/24 English words)
- Private keys must be loaded via environment variables:
  - JavaScript / TypeScript: `process.env.PRIVATE_KEY`
  - Python: `os.environ.get("PRIVATE_KEY")`

### Rule 2: Load Private Key via Environment Variable

- Write method scripts must include environment variable reading logic
- Usage instructions comment at the top of the script must include environment variable configuration:

```
Set private key environment variable:
  export PRIVATE_KEY=your_private_key (without 0x prefix)
```

### Rule 3: Remind Users Not to Commit Private Keys to Version Control

- Generated write method scripts must include the following security reminder comment:

```
⚠️ Security Reminder: Never hardcode private keys in scripts, and never commit files containing private keys to version control systems (e.g., Git).
It's recommended to store private keys in a .env file and ensure .env is added to .gitignore.
```

---

## Agent Operation Checklist

The following is the complete operation flow from receiving user request to outputting the script file. The Agent follows this checklist step by step for each script generation.

### Step 1: Receive and Understand User Request

- [ ] Confirm user's intent is to generate a contract interaction script
- [ ] Identify the type of contract information provided:
  - ABI JSON → Enter Method A parsing flow
  - Method signature strings → Enter Method B parsing flow
  - `.sol` file path → Enter Method C parsing flow
  - Only address provided, no interface info → Prompt user to provide ABI/signatures/.sol
- [ ] Identify whether user specified a contract address (use `<CONTRACT_ADDRESS>` placeholder if not provided)

### Step 2: Validate Input Information

- [ ] If contract address provided, validate address format (`0x` + 40 hex characters)
- [ ] If ABI JSON provided, validate JSON format and content (is it an array, does it contain function entries)
- [ ] If `.sol` file path provided, confirm file exists
- [ ] On input validation failure, return corresponding error prompt (see "Agent-Level Error Handling Table")

### Step 3: Parse Contract Information

- [ ] Execute parsing flow per corresponding method (A/B/C)
- [ ] Extract all callable method information (method name, parameters, return values, stateMutability)
- [ ] Classify methods as read (view/pure) and write (nonpayable/payable)
- [ ] Display parsing results to user, confirm method list

### Step 4: Determine Target Language

- [ ] Check if user specified a target language (JavaScript / TypeScript / Python)
- [ ] Default to JavaScript (ethers.js v6) if not specified
- [ ] Determine corresponding template file path (see "Template Mapping Table")

### Step 5: Read Network Configuration

- [ ] Read `assets/networks.json` file
- [ ] Determine target network (user-specified or use `defaultNetwork`)
- [ ] Extract target network's `rpcUrl`, `chainId`, `name`
- [ ] Return error prompt listing available networks if network doesn't exist

### Step 5.5: Initialize Python Environment (Python Only)

- [ ] If target language is Python, execute the following steps:
  - [ ] Check if `uv` is available (`which uv`), prompt user to install if unavailable
  - [ ] Check if `pyproject.toml` exists in project root, execute `uv init` if not
  - [ ] Execute `uv add web3` to install dependency

### Step 6: Read Templates and Replace Placeholders

- [ ] Read corresponding template files based on method type and target language
- [ ] Replace `{{DEPENDENCY_COMMENT}}`: Fill in corresponding language's dependency install command
- [ ] Replace `{{RPC_URL}}`: Fill in target network's RPC URL
- [ ] Replace `{{CHAIN_ID}}`: Fill in target network's Chain ID
- [ ] Replace `{{NETWORK_NAME}}`: Fill in target network name
- [ ] Replace `{{CONTRACT_ADDRESS}}`: Fill in user-provided address or placeholder
- [ ] Replace `{{ABI}}`: Fill in parsed ABI JSON (function entries only)
- [ ] Generate call function bodies for each method, replace `{{METHOD_FUNCTIONS}}`
- [ ] Generate main function example, replace `{{MAIN_EXAMPLE}}`

### Step 7: Check File Overwrite

- [ ] Determine output file path: `scripts/interact_<ContractName>.<ext>`
- [ ] Check if target file already exists
- [ ] If exists, inform user file will be overwritten, wait for confirmation
- [ ] If user declines overwrite, stop generation

### Step 8: Write File and Output Results

- [ ] Write generated script content to target file
- [ ] Display generation result summary to user:
  - Generated file path
  - Included method list (grouped by read/write)
  - Dependency install command
  - Environment variable configuration instructions (for write methods)
  - Run command example
