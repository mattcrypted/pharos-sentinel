// {{DEPENDENCY_COMMENT}}
// Run: PRIVATE_KEY=your_private_key npx tsx scripts/interact_<ContractName>.ts

import {
  createPublicClient,
  createWalletClient,
  http,
  defineChain,
  parseEther,
} from "viem";
import { privateKeyToAccount } from "viem/accounts";

// ============================================================
// Network Configuration ({{NETWORK_NAME}})
// ============================================================
const RPC_URL = "{{RPC_URL}}";
const CHAIN_ID = {{CHAIN_ID}};

const chain = defineChain({
  id: CHAIN_ID,
  name: "{{NETWORK_NAME}}",
  nativeCurrency: { name: "PHRS", symbol: "PHRS", decimals: 18 },
  rpcUrls: {
    default: { http: [RPC_URL] },
  },
});

// ============================================================
// Contract Configuration
// ============================================================
const CONTRACT_ADDRESS = "{{CONTRACT_ADDRESS}}" as `0x${string}`;
const ABI = {{ABI}} as const;

// ============================================================
// Helpers
// ============================================================

/**
 * Load the private key from the PRIVATE_KEY environment variable.
 * Exits with a clear message if the key is not configured.
 */
function getPrivateKey(): `0x${string}` {
  const key = process.env.PRIVATE_KEY;
  if (!key) {
    console.error("❌ PRIVATE_KEY environment variable is not set.");
    console.error("");
    console.error("   To configure your private key, run:");
    console.error("     export PRIVATE_KEY=your_private_key_here");
    console.error("");
    console.error("   Or pass it inline:");
    console.error(
      "     PRIVATE_KEY=your_private_key_here npx tsx scripts/interact_<ContractName>.ts"
    );
    console.error("");
    console.error("   ⚠️  Never commit your private key to version control!");
    process.exit(1);
  }
  return (key.startsWith("0x") ? key : `0x${key}`) as `0x${string}`;
}


/**
 * Create a viem public client and verify the RPC connection.
 * Throws with a descriptive message when the connection fails.
 */
async function getClients() {
  try {
    const account = privateKeyToAccount(getPrivateKey());

    const publicClient = createPublicClient({
      chain,
      transport: http(RPC_URL),
    });

    const walletClient = createWalletClient({
      account,
      chain,
      transport: http(RPC_URL),
    });

    // Verify the connection by fetching the chain ID
    await publicClient.getChainId();

    return { publicClient, walletClient, account };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("❌ Failed to connect to RPC endpoint:", RPC_URL);
    console.error("   Reason:", message);
    console.error("");
    console.error("   Suggestions:");
    console.error("   1. Check that the RPC URL is correct and reachable");
    console.error("   2. Verify your network connection");
    console.error(
      "   3. The RPC endpoint may be temporarily unavailable — try again later"
    );
    throw error;
  }
}

/**
 * Send a write transaction, wait for the receipt, and log the result.
 * Logs transaction hash, block number, gas used, and status.
 *
 * @param publicClient - viem public client for waiting on receipts.
 * @param walletClient - viem wallet client for sending transactions.
 * @param functionName - The contract method to call.
 * @param args - Arguments to pass to the method.
 * @param value - Optional value in wei to send (for payable methods). Use parseEther("0.1") to convert from ETH.
 */
async function sendTransaction(
  publicClient: Awaited<ReturnType<typeof getClients>>["publicClient"],
  walletClient: Awaited<ReturnType<typeof getClients>>["walletClient"],
  functionName: string,
  args: unknown[] = [],
  value?: bigint
) {
  try {
    console.log(`\n📤 Sending transaction: ${functionName}(...)`);

    const txHash = await walletClient.writeContract({
      address: CONTRACT_ADDRESS,
      abi: ABI,
      functionName,
      args,
      ...(value !== undefined ? { value } : {}),
    });

    console.log(`   Transaction hash: ${txHash}`);
    console.log("   Waiting for confirmation...");

    const receipt = await publicClient.waitForTransactionReceipt({
      hash: txHash,
    });

    console.log("\n✅ Transaction confirmed!");
    console.log(`   Transaction hash : ${receipt.transactionHash}`);
    console.log(`   Block number     : ${receipt.blockNumber}`);
    console.log(`   Gas used         : ${receipt.gasUsed.toString()}`);
    console.log(
      `   Status           : ${receipt.status === "success" ? "Success" : "Failed"}`
    );

    return receipt;
  } catch (error: unknown) {
    const err = error as Record<string, unknown>;
    // Extract revert reason if available
    if (err.shortMessage) {
      console.error(
        `\n❌ Transaction "${functionName}" reverted: ${err.shortMessage}`
      );
    } else if (err.details) {
      console.error(
        `\n❌ Transaction "${functionName}" failed with details: ${err.details}`
      );
    } else {
      const message = error instanceof Error ? error.message : String(error);
      console.error(`\n❌ Transaction "${functionName}" failed: ${message}`);
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
  const { publicClient, walletClient, account } = await getClients();

  console.log(`Signer address: ${account.address}`);

  // For payable methods, set the value (in wei) to send with the transaction:
  //   const value = parseEther("0.1");
  // Then pass value as the last argument to sendTransaction.

  {{MAIN_EXAMPLE}}
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : String(error);
  console.error("Unhandled error:", message);
  process.exit(1);
});
