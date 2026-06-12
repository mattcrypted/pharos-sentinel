// {{DEPENDENCY_COMMENT}}
// Run: node scripts/interact_<ContractName>.js

const { ethers } = require("ethers");

// ============================================================
// Network Configuration ({{NETWORK_NAME}})
// ============================================================
const RPC_URL = "{{RPC_URL}}";
const CHAIN_ID = {{CHAIN_ID}};

// ============================================================
// Contract Configuration
// ============================================================
const CONTRACT_ADDRESS = "{{CONTRACT_ADDRESS}}";
const ABI = {{ABI}};

// ============================================================
// Helpers
// ============================================================

/**
 * Format a value returned by a contract call into a human-readable string.
 * - BigInt values are converted to their decimal string representation.
 * - Arrays are recursively formatted.
 * - Other types are returned as-is via String().
 */
function formatValue(value) {
  if (typeof value === "bigint") {
    return value.toString();
  }
  if (Array.isArray(value)) {
    return value.map(formatValue);
  }
  return String(value);
}

/**
 * Call a read-only contract method with error handling.
 * Catches revert reasons and other contract call failures.
 */
async function safeCall(contract, methodName, ...args) {
  try {
    const result = await contract[methodName](...args);
    return formatValue(result);
  } catch (error) {
    // Extract revert reason if available
    if (error.reason) {
      console.error(`❌ Contract call "${methodName}" reverted: ${error.reason}`);
    } else if (error.data) {
      console.error(`❌ Contract call "${methodName}" failed with data: ${error.data}`);
    } else {
      console.error(`❌ Contract call "${methodName}" failed: ${error.message || error}`);
    }
    throw error;
  }
}

/**
 * Create an ethers.js v6 provider and verify the RPC connection.
 * Throws with a descriptive message when the connection fails.
 */
async function getProvider() {
  try {
    const provider = new ethers.JsonRpcProvider(RPC_URL, {
      chainId: CHAIN_ID,
      name: "{{NETWORK_NAME}}",
    });
    // Verify the connection by fetching the network
    await provider.getNetwork();
    return provider;
  } catch (error) {
    console.error("❌ Failed to connect to RPC endpoint:", RPC_URL);
    console.error("   Reason:", error.message || error);
    console.error("");
    console.error("   Suggestions:");
    console.error("   1. Check that the RPC URL is correct and reachable");
    console.error("   2. Verify your network connection");
    console.error("   3. The RPC endpoint may be temporarily unavailable — try again later");
    throw error;
  }
}

// ============================================================
// Read Method Functions
// ============================================================

{{METHOD_FUNCTIONS}}

// ============================================================
// Main
// ============================================================

async function main() {
  console.log("Connecting to {{NETWORK_NAME}} ...");
  const provider = await getProvider();
  const contract = new ethers.Contract(CONTRACT_ADDRESS, ABI, provider);

  {{MAIN_EXAMPLE}}
}

main().catch((error) => {
  console.error("Unhandled error:", error.message || error);
  process.exit(1);
});
