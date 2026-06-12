// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./AirdropHelper.sol";
import "./ERC20Distributor.sol";

/// @notice Minimal ERC20 interface for token queries and approval.
interface IERC20Info {
    function approve(address spender, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
    function symbol() external view returns (string memory);
    function decimals() external view returns (uint8);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

/// @title BatchAirdropERC20 — ERC20 Token Batch Airdrop Script Template
/// @notice Reads recipients from CSV, auto-selects execution mode, and distributes ERC20 tokens.
///         Customize CSV_PATH, BATCH_SIZE, and TOKEN_ADDRESS via environment variables before running.
/// @dev    Usage: forge script assets/airdrop/BatchAirdropERC20.s.sol --broadcast --rpc-url <RPC_URL>
contract BatchAirdropERC20 is AirdropHelper {
    function run() external {
        // ── Configuration ──────────────────────────────────────
        string memory csvPath = vm.envOr("CSV_PATH", string("airdrop.csv"));
        uint256 batchSize = vm.envOr("BATCH_SIZE", DEFAULT_BATCH_SIZE);
        address tokenAddress = vm.envAddress("TOKEN_ADDRESS");
        IERC20Info token = IERC20Info(tokenAddress);

        // ── Parse CSV ──────────────────────────────────────────
        (address[] memory recipients, uint256[] memory amounts) = _readCSV(csvPath);
        require(recipients.length > 0, "No recipients found in CSV");

        // ── Calculate total amount ─────────────────────────────
        uint256 totalAmount = 0;
        for (uint256 i = 0; i < amounts.length; i++) {
            totalAmount += amounts[i];
        }

        // ── Pre-flight summary ─────────────────────────────────
        AirdropMode mode = _selectMode(recipients.length, batchSize);
        {
            string memory tokenSymbol = token.symbol();
            uint8 tokenDecimals = token.decimals();
            uint256 expectedBatches = (recipients.length + batchSize - 1) / batchSize;

            console.log("=== ERC20 Airdrop Plan ===");
            console.log("CSV file        : %s", csvPath);
            console.log("Token address   : %s", vm.toString(tokenAddress));
            console.log("Token symbol    : %s", tokenSymbol);
            console.log("Token decimals  : %d", uint256(tokenDecimals));
            console.log("Total recipients: %d", recipients.length);
            console.log("Total amount    : %d (raw)", totalAmount);
            console.log("Batch size      : %d", batchSize);
            console.log("Expected batches: %d", expectedBatches);
        }

        if (mode == AirdropMode.Simple) {
            console.log("Mode: Simple (direct transferFrom)");
        } else if (mode == AirdropMode.SingleBatch) {
            console.log("Mode: SingleBatch (one distributor call)");
        } else {
            console.log("Mode: MultiBatch (batched distributor calls)");
        }

        // ── Execute ────────────────────────────────────────────
        vm.startBroadcast();

        if (mode == AirdropMode.Simple) {
            for (uint256 i = 0; i < recipients.length; i++) {
                bool ok = token.transferFrom(msg.sender, recipients[i], amounts[i]);
                console.log("Transfer %d: %s", i + 1, vm.toString(recipients[i]));
                console.log("  Amount: %d | Success: %s", amounts[i], ok ? "true" : "false");
            }
        } else {
            ERC20Distributor distributor = new ERC20Distributor();
            console.log("ERC20Distributor deployed at: %s", vm.toString(address(distributor)));

            token.approve(address(distributor), totalAmount);

            if (mode == AirdropMode.SingleBatch) {
                console.log("Batch 1/1 | Recipients [0..%d]", recipients.length - 1);
                console.log("  Batch amount: %d (raw)", totalAmount);
                distributor.distribute(tokenAddress, msg.sender, recipients, amounts);
            } else {
                _executeBatchesERC20(address(distributor), tokenAddress, msg.sender, recipients, amounts, batchSize);
            }
        }

        vm.stopBroadcast();

        // ── Final summary ──────────────────────────────────────
        console.log("=== Airdrop Complete ===");
        console.log("Token           : %s", vm.toString(tokenAddress));
        console.log("Total recipients: %d", recipients.length);
        console.log("Total amount    : %d (raw)", totalAmount);
    }
}
