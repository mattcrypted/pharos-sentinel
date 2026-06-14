// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

// Sentinel risk-gallery fixtures. Each contract is engineered to light up a
// distinct Sentinel risk signal, producing a monotonic verdict spectrum when
// read live over RPC. Deployed to Pharos Atlantic; analysed by Sentinel.
// NOTE: deliberately minimal / not production tokens — these are risk decoys.

// --- SAFE baseline: a clean ERC-20 with no privileged owner -----------------
// Constant getters so the minimal proxy (below) reads the same values without storage.
contract CleanToken {
    function name() external pure returns (string memory) { return "Clean Token"; }
    function symbol() external pure returns (string memory) { return "CLEAN"; }
    function decimals() external pure returns (uint8) { return 18; }
    function totalSupply() external pure returns (uint256) { return 1_000_000e18; }
}

// --- CAUTION: zero-supply trap token, single EOA owner ----------------------
contract ZeroSupplyToken {
    address public owner;
    constructor(address o) { owner = o; }
    function name() external pure returns (string memory) { return "Ghost"; }
    function symbol() external pure returns (string memory) { return "GHOST"; }
    function decimals() external pure returns (uint8) { return 18; }
    function totalSupply() external pure returns (uint256) { return 0; } // <- trap
}

// --- CAUTION: EIP-1967 upgradeable proxy, paused, EOA owner ------------------
// Logic for the proxy. owner/paused live in slots 0/1 so a delegatecall through
// the proxy reads the proxy's own storage (set in the proxy constructor).
contract LogicV1 {
    address public owner;   // slot 0
    bool public paused;     // slot 1
    function initialize(address o) external { owner = o; paused = true; }
}

contract Eip1967Proxy {
    // bytes32(uint256(keccak256("eip1967.proxy.implementation")) - 1)
    bytes32 private constant _IMPL =
        0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc;

    constructor(address impl, address o) {
        assembly { sstore(_IMPL, impl) }
        (bool ok, ) = impl.delegatecall(
            abi.encodeWithSignature("initialize(address)", o)
        );
        require(ok, "init failed");
    }

    fallback() external payable {
        assembly {
            let impl := sload(0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc)
            calldatacopy(0, 0, calldatasize())
            let r := delegatecall(gas(), impl, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch r
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }
}

// --- DANGEROUS: backdoor — SELFDESTRUCT + unguarded DELEGATECALL + paused -----
contract Backdoor {
    address public owner;
    bool public paused;
    constructor(address o) { owner = o; paused = true; }
    // unguarded delegatecall: can run arbitrary external code in this context
    function exec(address t, bytes calldata d) external {
        (bool ok, ) = t.delegatecall(d);
        require(ok, "exec failed");
    }
    // self-destruct: the contract can be destroyed, taking its logic with it
    function kill() external {
        selfdestruct(payable(owner));
    }
}

// --- LIVE UPGRADE ATTACK: a mutable proxy + benign logic --------------------
// Benign logic the proxy initially points at: no privileged owner, not paused.
contract LogicBenign {
    function version() external pure returns (uint256) { return 1; }
}

// An EIP-1967 proxy whose admin can swap the implementation after deployment —
// the exact rug vector Sentinel warns about. upgradeToAndCall lets the admin
// point at hostile logic AND initialize it in one transaction.
contract MutableProxy {
    constructor(address impl, address admin_) {
        assembly {
            sstore(0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc, impl)
            sstore(0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103, admin_)
        }
    }

    function upgradeToAndCall(address newImpl, bytes calldata data) external {
        address a;
        assembly { a := sload(0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103) }
        require(msg.sender == a, "not admin");
        assembly { sstore(0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc, newImpl) }
        if (data.length > 0) {
            (bool ok, ) = newImpl.delegatecall(data);
            require(ok, "init failed");
        }
    }

    fallback() external payable {
        assembly {
            let impl := sload(0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc)
            calldatacopy(0, 0, calldatasize())
            let r := delegatecall(gas(), impl, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch r
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }

    receive() external payable {}
}

// --- LIVE PAUSE FLIP: operational state the operator can toggle after the fact -
// `admin` is private (no owner()/admin() getter), so before the flip Sentinel
// sees only the latent SELFDESTRUCT (−25 -> safety 75, still in the safe band).
// When the operator pauses it, the live −20 tips the verdict over to caution.
contract Destructible {
    address private admin;
    bool public paused;            // paused() getter — Sentinel reads this live
    constructor(address a) { admin = a; }
    function setPaused(bool p) external { require(msg.sender == admin, "not admin"); paused = p; }
    function kill() external { selfdestruct(payable(admin)); }
}
