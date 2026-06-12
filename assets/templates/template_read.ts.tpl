// {{DEPENDENCY_COMMENT}}
// Run: npx tsx scripts/interact_<ContractName>.ts

import { createPublicClient, http, defineChain } from "viem";

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
 * Format a value returned by a contract call into a human-readable string.
 * - BigInt values are converted to their decimal string representation.
 * - Arrays are recursively formatted.
 * - Other types are returned as-is via String().
 */
function formatValue(value: unknown): unknown {
  if (typeof value === "bigint") {
    return value.toString();
  }
  if (Array.isArray(value)) {
    return value.map(formatValue);
  }
  return String(value);
}

/**
 * Create a viem public client and verify the RPC connection.
 * Throws with a descriptive message when the connection fails.
 */
async function getClient() {
  try {
    const client = createPublicClient({
      chain,
      transport: http(RPC_URL),
    });
    // Verify the connection by fetching the chain ID
    await client.getChainId();
    return client;
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("❌ Failed to connect to RPC endpoint:", RPC_URL);
    console.error("   Reason:", message);
    console.error("");
    console.error("   Suggestions:");
    console.error("   1. Check that the RPC URL is correct and reachable");
    console.error("   2. Verify your network connection");
    console.error("   3. The RPC endpoint may be temporarily unavailable — try again later");
    throw error;
  }
}

/**
 * Call a read-only contract method with error handling.
 * Catches revert reasons and other contract call failures.
 */
async function safeRead(
  client: Awaited<ReturnType<typeof getClient>>,
  functionName: string,
  args: unknown[] = []
): Promise<unknown> {
  try {
    const result = await client.readContract({
      address: CONTRACT_ADDRESS,
      abi: ABI,
      functionName,
      args,
    });
    return formatValue(result);
  } catch (error: unknown) {
    const err = error as Record<string, unknown>;
    if (err.shortMessage) {
      console.error(`❌ Contract call "${functionName}" reverted: ${err.shortMessage}`);
    } else if (err.details) {
      console.error(`❌ Contract call "${functionName}" failed with details: ${err.details}`);
    } else {
      const message = error instanceof Error ? error.message : String(error);
      console.error(`❌ Contract call "${functionName}" failed: ${message}`);
    }
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
  const client = await getClient();

  {{MAIN_EXAMPLE}}
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : String(error);
  console.error("Unhandled error:", message);
  process.exit(1);
});
