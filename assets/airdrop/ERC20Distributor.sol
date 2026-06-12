// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

contract ERC20Distributor {
    event Distributed(address indexed recipient, uint256 amount, bool success);

    function distribute(
        address token,
        address from,
        address[] calldata recipients,
        uint256[] calldata amounts
    ) external {
        require(recipients.length == amounts.length, "length mismatch");

        for (uint256 i = 0; i < recipients.length; i++) {
            try IERC20(token).transferFrom(from, recipients[i], amounts[i]) returns (bool ok) {
                emit Distributed(recipients[i], amounts[i], ok);
            } catch {
                emit Distributed(recipients[i], amounts[i], false);
            }
        }
    }
}
