// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

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

        // Refund remaining balance to caller
        uint256 remaining = address(this).balance;
        if (remaining > 0) {
            (bool refundOk, ) = msg.sender.call{value: remaining}("");
            require(refundOk, "refund failed");
        }
    }
}
