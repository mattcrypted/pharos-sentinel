// {{DEPENDENCY_COMMENT}}
// Run: PRIVATE_KEY=your_private_key node scripts/interact_<ContractName>.js

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

/**
 * Create a wallet signer from the PRIVATE_KEY environment variable.
 * Exits with a clear message if the key is not configured.
 */
function getSigner(provider) {
  const privateKey = process.env.PRIVATE_KEY;
  if (!privateKey) {
    console.error("❌ PRIVATE_KEY environment variable is not set.");
    console.error("");
    console.error("   To configure your private key, run:");
    console.error("     export PRIVATE_KEY=your_private_key_here");
    console.error("");
    console.error("   Or pass it inline:");
    console.error("     PRIVATE_KEY=your_private_key_here node scripts/interact_<ContractName>.js");
    console.error("");
    console.error("   ⚠️  Never commit your private key to version control!");
    process.exit(1);
  }
  return new ethers.Wallet(privateKey, provider);
}

/**
 * Send a write transaction and parse the receipt.
 * Logs transaction hash, block number, gas used, and status.
 *
 * @param {ethers.Contract} contract - The contract instance connected to a signer.
 * @param {string} methodName - The contract method to call.
 * @param {Array} args - Arguments to pass to the method.
 * @param {object} [overrides] - Optional transaction overrides (e.g. { value: ethers.parseEther("0.1") } for payable methods).
 */
async function sendTransaction(contract, methodName, args = [], overrides = {}) {
  try {
    console.log(`\n📤 Sending transaction: ${methodName}(...)`);
    const tx = await contract[methodName](...args, overrides);
    console.log(`   Transaction hash: ${tx.hash}`);
    console.log("   Waiting for confirmation...");

    const receipt = await tx.wait();

    console.log("\n✅ Transaction confirmed!");
    console.log(`   Transaction hash : ${receipt.hash}`);
    console.log(`   Block number     : ${receipt.blockNumber}`);
    console.log(`   Gas used         : ${receipt.gasUsed.toString()}`);
    console.log(`   Status           : ${receipt.status === 1 ? "Success" : "Failed"}`);

    return receipt;
  } catch (error) {
    // Extract revert reason if available
    if (error.reason) {
      console.error(`\n❌ Transaction "${methodName}" reverted: ${error.reason}`);
    } else if (error.data) {
      console.error(`\n❌ Transaction "${methodName}" failed with data: ${error.data}`);
    } else if (error.code === "INSUFFICIENT_FUNDS") {
      console.error(`\n❌ Insufficient funds to send transaction "${methodName}".`);
      console.error("   Please ensure your account has enough balance to cover gas and value.");
    } else if (error.code === "NONCE_EXPIRED") {
      console.error(`\n❌ Nonce conflict for transaction "${methodName}".`);
      console.error("   Another transaction may be pending. Try again shortly.");
    } else {
      console.error(`\n❌ Transaction "${methodName}" failed: ${error.message || error}`);
    }
    throw error;
  }
}

// ============================================================
// Write Method Functions
// ============================================================

{{METHOD_FUNCTIONS}}

// ============================================================
// Main
// ============================================================

async function main() {
  console.log("Connecting to {{NETWORK_NAME}} ...");
  const provider = await getProvider();
  const signer = getSigner(provider);
  const contract = new ethers.Contract(CONTRACT_ADDRESS, ABI, signer);

  console.log(`Signer address: ${signer.address}`);

  // For payable methods, set the value (in wei) to send with the transaction:
  //   const overrides = { value: ethers.parseEther("0.1") };
  // Then pass overrides as the last argument to sendTransaction.

  {{MAIN_EXAMPLE}}
}

main().catch((error) => {
  console.error("Unhandled error:", error.message || error);
  process.exit(1);
});
