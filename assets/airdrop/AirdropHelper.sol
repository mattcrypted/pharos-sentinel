// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";

abstract contract AirdropHelper is Script {
    // ──────────────────────────────────────────────
    //  Mode Auto-Selection
    // ──────────────────────────────────────────────

    enum AirdropMode { Simple, SingleBatch, MultiBatch }

    uint256 internal constant DEFAULT_BATCH_SIZE = 200;

    /// @notice Select airdrop execution mode based on recipient count and batch size.
    /// @param count Number of recipient addresses.
    /// @param batchSize Maximum recipients per batch.
    /// @return mode The selected AirdropMode.
    function _selectMode(uint256 count, uint256 batchSize) internal pure returns (AirdropMode) {
        if (count <= 10) {
            return AirdropMode.Simple;
        } else if (count <= batchSize) {
            return AirdropMode.SingleBatch;
        } else {
            return AirdropMode.MultiBatch;
        }
    }

    /// @notice Select airdrop execution mode using the default batch size (200).
    /// @param count Number of recipient addresses.
    /// @return mode The selected AirdropMode.
    function _selectMode(uint256 count) internal pure returns (AirdropMode) {
        return _selectMode(count, DEFAULT_BATCH_SIZE);
    }

    // ──────────────────────────────────────────────
    //  CSV Parsing
    // ──────────────────────────────────────────────

    /// @notice Read a CSV file and parse recipient addresses and amounts.
    /// @param path Path to the CSV file (relative to project root).
    /// @return recipients Array of parsed addresses.
    /// @return amounts Array of parsed uint256 amounts.
    function _readCSV(string memory path)
        internal
        view
        returns (address[] memory recipients, uint256[] memory amounts)
    {
        string memory content = vm.readFile(path);
        bytes memory raw = bytes(content);

        // Count lines to allocate arrays
        uint256 lineCount = _countLines(raw);
        if (lineCount == 0) {
            return (new address[](0), new uint256[](0));
        }

        // Split into lines
        string[] memory lines = _splitLines(raw, lineCount);

        // Determine start index: skip header row if present
        uint256 startIdx = 0;
        if (lineCount > 0 && _isHeader(lines[0])) {
            startIdx = 1;
        }

        uint256 dataCount = lineCount - startIdx;
        recipients = new address[](dataCount);
        amounts = new uint256[](dataCount);

        for (uint256 i = 0; i < dataCount; i++) {
            uint256 lineNum = startIdx + i + 1; // 1-based line number for error messages
            string memory line = lines[startIdx + i];

            // Split line by comma
            (string memory addrStr, string memory amtStr) = _splitComma(line, lineNum);

            // Validate and parse address
            recipients[i] = _parseAndValidateAddress(addrStr, lineNum);

            // Parse amount (vm.parseUint reverts on invalid input)
            amounts[i] = _parseAmount(amtStr, lineNum);
        }
    }

    /// @dev Count non-empty lines in raw bytes.
    function _countLines(bytes memory raw) internal pure returns (uint256 count) {
        if (raw.length == 0) return 0;

        uint256 start = 0;
        for (uint256 i = 0; i <= raw.length; i++) {
            if (i == raw.length || raw[i] == 0x0A) {
                // Check if line is non-empty (skip blank lines and lone \r)
                uint256 end = i;
                if (end > start && raw[end - 1] == 0x0D) {
                    end--;
                }
                if (end > start) {
                    count++;
                }
                start = i + 1;
            }
        }
    }

    /// @dev Split raw bytes into an array of line strings, skipping empty lines.
    function _splitLines(bytes memory raw, uint256 lineCount)
        internal
        pure
        returns (string[] memory lines)
    {
        lines = new string[](lineCount);
        uint256 idx = 0;
        uint256 start = 0;

        for (uint256 i = 0; i <= raw.length; i++) {
            if (i == raw.length || raw[i] == 0x0A) {
                uint256 end = i;
                // Strip trailing \r for Windows-style line endings
                if (end > start && raw[end - 1] == 0x0D) {
                    end--;
                }
                if (end > start) {
                    bytes memory lineBytes = new bytes(end - start);
                    for (uint256 j = start; j < end; j++) {
                        lineBytes[j - start] = raw[j];
                    }
                    lines[idx] = string(lineBytes);
                    idx++;
                }
                start = i + 1;
            }
        }
    }

    /// @dev Check if a line is the CSV header "address,amount" (case-insensitive).
    function _isHeader(string memory line) internal pure returns (bool) {
        bytes memory b = bytes(line);
        // Strip trailing whitespace / \r
        uint256 len = b.length;
        while (len > 0 && (b[len - 1] == 0x20 || b[len - 1] == 0x0D || b[len - 1] == 0x09)) {
            len--;
        }
        if (len != 14) return false; // "address,amount" is 14 chars
        // Compare lowercase
        bytes memory expected = bytes("address,amount");
        for (uint256 i = 0; i < 14; i++) {
            bytes1 c = b[i];
            // Lowercase conversion for A-Z
            if (c >= 0x41 && c <= 0x5A) {
                c = bytes1(uint8(c) + 32);
            }
            if (c != expected[i]) return false;
        }
        return true;
    }

    /// @dev Split a CSV line by the first comma. Reverts if no comma found.
    function _splitComma(string memory line, uint256 lineNum)
        internal
        pure
        returns (string memory left, string memory right)
    {
        bytes memory b = bytes(line);
        uint256 commaIdx = type(uint256).max;

        for (uint256 i = 0; i < b.length; i++) {
            if (b[i] == 0x2C) { // comma
                commaIdx = i;
                break;
            }
        }

        require(
            commaIdx != type(uint256).max,
            string(abi.encodePacked("CSV parse error at line ", vm.toString(lineNum), ": missing comma delimiter"))
        );

        // Left part (address)
        bytes memory leftBytes = new bytes(commaIdx);
        for (uint256 i = 0; i < commaIdx; i++) {
            leftBytes[i] = b[i];
        }
        left = string(leftBytes);

        // Right part (amount) — trim trailing whitespace/\r
        uint256 rightStart = commaIdx + 1;
        uint256 rightEnd = b.length;
        while (rightEnd > rightStart && (b[rightEnd - 1] == 0x20 || b[rightEnd - 1] == 0x0D || b[rightEnd - 1] == 0x09)) {
            rightEnd--;
        }
        // Trim leading whitespace
        while (rightStart < rightEnd && (b[rightStart] == 0x20 || b[rightStart] == 0x09)) {
            rightStart++;
        }
        bytes memory rightBytes = new bytes(rightEnd - rightStart);
        for (uint256 i = rightStart; i < rightEnd; i++) {
            rightBytes[i - rightStart] = b[i];
        }
        right = string(rightBytes);
    }

    /// @dev Validate address format (0x prefix + 42 chars) and parse it.
    function _parseAndValidateAddress(string memory addrStr, uint256 lineNum)
        internal
        pure
        returns (address)
    {
        bytes memory b = bytes(addrStr);

        // Trim whitespace
        uint256 start = 0;
        uint256 end = b.length;
        while (start < end && (b[start] == 0x20 || b[start] == 0x09)) start++;
        while (end > start && (b[end - 1] == 0x20 || b[end - 1] == 0x09)) end--;

        uint256 trimmedLen = end - start;

        // Check 0x prefix
        bool hasPrefix = trimmedLen >= 2 && b[start] == 0x30 && (b[start + 1] == 0x78 || b[start + 1] == 0x58);

        require(
            hasPrefix && trimmedLen == 42,
            string(
                abi.encodePacked(
                    "CSV parse error at line ",
                    vm.toString(lineNum),
                    ": invalid address format (expected 0x + 40 hex chars)"
                )
            )
        );

        // Build trimmed string if needed
        string memory trimmed;
        if (start == 0 && end == b.length) {
            trimmed = addrStr;
        } else {
            bytes memory trimmedBytes = new bytes(trimmedLen);
            for (uint256 i = start; i < end; i++) {
                trimmedBytes[i - start] = b[i];
            }
            trimmed = string(trimmedBytes);
        }

        return vm.parseAddress(trimmed);
    }

    /// @dev Parse amount string to uint256, reverting with line number on failure.
    function _parseAmount(string memory amtStr, uint256 lineNum)
        internal
        pure
        returns (uint256)
    {
        bytes memory b = bytes(amtStr);
        require(
            b.length > 0,
            string(abi.encodePacked("CSV parse error at line ", vm.toString(lineNum), ": empty amount"))
        );

        // vm.parseUint will revert on invalid input; wrap with a descriptive message
        // Note: Foundry's vm.parseUint handles the actual parsing
        try VmSafe(VM_ADDRESS).parseUint(amtStr) returns (uint256 val) {
            return val;
        } catch {
            revert(
                string(
                    abi.encodePacked(
                        "CSV parse error at line ",
                        vm.toString(lineNum),
                        ": invalid amount format"
                    )
                )
            );
        }
    }

    // ──────────────────────────────────────────────
    //  Batch Execution — Native ETH
    // ──────────────────────────────────────────────

    /// @notice Execute batched native-ETH distribution via NativeDistributor.
    /// @param distributor Address of the deployed NativeDistributor contract.
    /// @param recipients  Full array of recipient addresses.
    /// @param amounts     Full array of amounts (in wei) corresponding to recipients.
    /// @param batchSize   Maximum number of recipients per batch.
    function _executeBatchesNative(
        address distributor,
        address[] memory recipients,
        uint256[] memory amounts,
        uint256 batchSize
    ) internal {
        uint256 totalBatches = (recipients.length + batchSize - 1) / batchSize;
        uint256 totalAmount = 0;

        for (uint256 b = 0; b < totalBatches; b++) {
            uint256 start = b * batchSize;
            uint256 end = start + batchSize;
            if (end > recipients.length) end = recipients.length;
            uint256 count = end - start;

            // Construct sub-arrays for current batch
            address[] memory batchRecipients = new address[](count);
            uint256[] memory batchAmounts = new uint256[](count);
            uint256 batchValue = 0;

            for (uint256 i = 0; i < count; i++) {
                batchRecipients[i] = recipients[start + i];
                batchAmounts[i] = amounts[start + i];
                batchValue += amounts[start + i];
            }

            // Log batch info before execution
            console.log("Batch %d/%d | Recipients [%d..%d]", b + 1, totalBatches);
            console.log("  Range: [%d..%d]", start, end - 1);

            // Call NativeDistributor.distribute{value: batchValue}(recipients, amounts)
            (bool ok, ) = distributor.call{value: batchValue}(
                abi.encodeWithSignature(
                    "distribute(address[],uint256[])",
                    batchRecipients,
                    batchAmounts
                )
            );
            require(ok, string(abi.encodePacked("Batch ", vm.toString(b + 1), " failed")));

            totalAmount += batchValue;
        }

        // Summary statistics
        console.log("--- Airdrop Summary (Native) ---");
        console.log("Total batches : %d", totalBatches);
        console.log("Total recipients: %d", recipients.length);
        console.log("Total amount  : %d wei", totalAmount);
    }

    // ──────────────────────────────────────────────
    //  Batch Execution — ERC20
    // ──────────────────────────────────────────────

    /// @notice Execute batched ERC20 distribution via ERC20Distributor.
    /// @param distributor Address of the deployed ERC20Distributor contract.
    /// @param token       Address of the ERC20 token contract.
    /// @param from        Address that has approved the distributor to spend tokens.
    /// @param recipients  Full array of recipient addresses.
    /// @param amounts     Full array of token amounts corresponding to recipients.
    /// @param batchSize   Maximum number of recipients per batch.
    function _executeBatchesERC20(
        address distributor,
        address token,
        address from,
        address[] memory recipients,
        uint256[] memory amounts,
        uint256 batchSize
    ) internal {
        uint256 totalBatches = (recipients.length + batchSize - 1) / batchSize;
        uint256 totalAmount = 0;

        for (uint256 b = 0; b < totalBatches; b++) {
            uint256 start = b * batchSize;
            uint256 end = start + batchSize;
            if (end > recipients.length) end = recipients.length;
            uint256 count = end - start;

            // Construct sub-arrays for current batch
            address[] memory batchRecipients = new address[](count);
            uint256[] memory batchAmounts = new uint256[](count);
            uint256 batchTotal = 0;

            for (uint256 i = 0; i < count; i++) {
                batchRecipients[i] = recipients[start + i];
                batchAmounts[i] = amounts[start + i];
                batchTotal += amounts[start + i];
            }

            // Log batch info before execution
            console.log("Batch %d/%d | Recipients [%d..%d]", b + 1, totalBatches);
            console.log("  Range: [%d..%d]", start, end - 1);

            // Call ERC20Distributor.distribute(token, from, recipients, amounts)
            (bool ok, ) = distributor.call(
                abi.encodeWithSignature(
                    "distribute(address,address,address[],uint256[])",
                    token,
                    from,
                    batchRecipients,
                    batchAmounts
                )
            );
            require(ok, string(abi.encodePacked("Batch ", vm.toString(b + 1), " failed")));

            totalAmount += batchTotal;
        }

        // Summary statistics
        console.log("--- Airdrop Summary (ERC20) ---");
        console.log("Total batches : %d", totalBatches);
        console.log("Total recipients: %d", recipients.length);
        console.log("Total amount  : %d tokens (raw)", totalAmount);
    }
}
