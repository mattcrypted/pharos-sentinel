# {{DEPENDENCY_COMMENT}}
# Run: uv run scripts/interact_<ContractName>.py

import sys

from web3 import Web3

# ============================================================
# Network Configuration ({{NETWORK_NAME}})
# ============================================================
RPC_URL = "{{RPC_URL}}"
CHAIN_ID = {{CHAIN_ID}}

# ============================================================
# Contract Configuration
# ============================================================
CONTRACT_ADDRESS = "{{CONTRACT_ADDRESS}}"
ABI = {{ABI}}

# ============================================================
# Helpers
# ============================================================


def format_value(value):
    """
    Format a value returned by a contract call into a human-readable string.
    - Large integers (>= 10**15) are converted to their decimal string representation.
    - Lists / tuples are recursively formatted.
    - Other types are returned as-is via str().
    """
    if isinstance(value, int) and (value >= 10**15 or value <= -(10**15)):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [format_value(v) for v in value]
    if isinstance(value, bytes):
        return "0x" + value.hex()
    return str(value)


def get_web3():
    """
    Create a Web3 instance connected to the RPC endpoint and verify the connection.
    Raises with a descriptive message when the connection fails.
    """
    try:
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        if not w3.is_connected():
            raise ConnectionError("Web3 is_connected() returned False")
        # Verify the chain ID matches the expected value
        chain_id = w3.eth.chain_id
        if chain_id != CHAIN_ID:
            print(f"⚠️  Warning: Expected chain ID {CHAIN_ID}, got {chain_id}")
        return w3
    except Exception as e:
        print(f"❌ Failed to connect to RPC endpoint: {RPC_URL}")
        print(f"   Reason: {e}")
        print()
        print("   Suggestions:")
        print("   1. Check that the RPC URL is correct and reachable")
        print("   2. Verify your network connection")
        print("   3. The RPC endpoint may be temporarily unavailable — try again later")
        raise


def safe_call(contract, method_name, *args):
    """
    Call a read-only contract method with error handling.
    Catches revert reasons and other contract call failures.
    """
    try:
        method = contract.functions[method_name]
        result = method(*args).call()
        return format_value(result)
    except Exception as e:
        error_msg = str(e)
        if "revert" in error_msg.lower():
            print(f'❌ Contract call "{method_name}" reverted: {error_msg}')
        elif "execution reverted" in error_msg.lower():
            print(f'❌ Contract call "{method_name}" reverted: {error_msg}')
        else:
            print(f'❌ Contract call "{method_name}" failed: {error_msg}')
        raise


# ============================================================
# Read Method Functions
# ============================================================

{{METHOD_FUNCTIONS}}

# ============================================================
# Main
# ============================================================


def main():
    print("Connecting to {{NETWORK_NAME}} ...")
    w3 = get_web3()
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=ABI
    )

    {{MAIN_EXAMPLE}}


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Unhandled error: {e}")
        sys.exit(1)
