// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./AirdropHelper.sol";
import "./NativeDistributor.sol";

/// @title BatchAirdrop — Native Token Batch Airdrop Script Template
/// @notice Reads recipients from CSV, auto-selects execution mode, and distributes native tokens.
///         Customize CSV_PATH and BATCH_SIZE via environment variables before running.
/// @dev    Usage: forge script assets/airdrop/BatchAirdrop.s.sol --broadcast --rpc-url <RPC_URL>
contract BatchAirdrop is AirdropHelper {
    function run() external {
        // ── Configuration ──────────────────────────────────────
        string memory csvPath = vm.envOr("CSV_PATH", string("airdrop.csv"));
        uint256 batchSize = vm.envOr("BATCH_SIZE", DEFAULT_BATCH_SIZE);

        // ── Parse CSV ──────────────────────────────────────────
        (address[] memory recipients, uint256[] memory amounts) = _readCSV(csvPath);
        require(recipients.length > 0, "No recipients found in CSV");

        // ── Calculate total amount ─────────────────────────────
        uint256 totalAmount = 0;
        for (uint256 i = 0; i < amounts.length; i++) {
            totalAmount += amounts[i];
        }

        // ── Pre-flight summary ─────────────────────────────────
        uint256 expectedBatches = (recipients.length + batchSize - 1) / batchSize;
        AirdropMode mode = _selectMode(recipients.length, batchSize);

        console.log("=== Native Airdrop Plan ===");
        console.log("CSV file      : %s", csvPath);
        console.log("Total recipients: %d", recipients.length);
        console.log("Total amount    : %d wei", totalAmount);
        console.log("Batch size      : %d", batchSize);
        console.log("Expected batches: %d", expectedBatches);

        if (mode == AirdropMode.Simple) {
            console.log("Mode: Simple (direct transfers)");
        } else if (mode == AirdropMode.SingleBatch) {
            console.log("Mode: SingleBatch (one distributor call)");
        } else {
            console.log("Mode: MultiBatch (batched distributor calls)");
        }

        // ── Execute ────────────────────────────────────────────
        vm.startBroadcast();

        if (mode == AirdropMode.Simple) {
            // Direct transfers for small recipient lists
            for (uint256 i = 0; i < recipients.length; i++) {
                (bool ok, ) = recipients[i].call{value: amounts[i]}("");
                console.log("Transfer %d: %s", i + 1, vm.toString(recipients[i]));
                console.log("  Amount: %d wei | Success: %s", amounts[i], ok ? "true" : "false");
            }
        } else {
            NativeDistributor distributor = new NativeDistributor();
            console.log("NativeDistributor deployed at: %s", vm.toString(address(distributor)));

            if (mode == AirdropMode.SingleBatch) {
                console.log("Batch 1/1 | Recipients [0..%d]", recipients.length - 1);
                console.log("  Batch amount: %d wei", totalAmount);
                distributor.distribute{value: totalAmount}(recipients, amounts);
            } else {
                _executeBatchesNative(address(distributor), recipients, amounts, batchSize);
            }
        }

        vm.stopBroadcast();

        // ── Final summary ──────────────────────────────────────
        console.log("=== Airdrop Complete ===");
        console.log("Total recipients: %d", recipients.length);
        console.log("Total amount    : %d wei", totalAmount);
    }
}
