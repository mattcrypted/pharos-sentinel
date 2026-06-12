# {{DEPENDENCY_COMMENT}}
# Run: PRIVATE_KEY=your_private_key uv run scripts/interact_<ContractName>.py

import os
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


def get_account(w3):
    """
    Load the private key from the PRIVATE_KEY environment variable and create
    an account. Exits with a clear message if the key is not configured.
    """
    private_key = os.environ.get("PRIVATE_KEY")
    if not private_key:
        print("❌ PRIVATE_KEY environment variable is not set.")
        print()
        print("   To configure your private key, run:")
        print("     export PRIVATE_KEY=your_private_key_here")
        print()
        print("   Or pass it inline:")
        print(
            "     PRIVATE_KEY=your_private_key_here uv run scripts/interact_<ContractName>.py"
        )
        print()
        print("   ⚠️  Never commit your private key to version control!")
        sys.exit(1)
    if not private_key.startswith("0x"):
        private_key = "0x" + private_key
    account = w3.eth.account.from_key(private_key)
    return account


def send_transaction(w3, account, contract, method_name, args=None, value=0):
    """
    Build, sign, send a write transaction and parse the receipt.
    Logs transaction hash, block number, gas used, and status.

    Args:
        w3: Web3 instance.
        account: The account object created from the private key.
        contract: The contract instance.
        method_name: The contract method to call.
        args: Arguments to pass to the method (default: empty list).
        value: Value in wei to send with the transaction (for payable methods).
               Use w3.to_wei(0.1, "ether") to convert from ETH.
    """
    if args is None:
        args = []
    try:
        print(f"\n📤 Sending transaction: {method_name}(...)")

        method = contract.functions[method_name]
        tx = method(*args).build_transaction(
            {
                "from": account.address,
                "nonce": w3.eth.get_transaction_count(account.address),
                "chainId": CHAIN_ID,
                "value": value,
            }
        )

        signed_tx = w3.eth.account.sign_transaction(tx, account.key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"   Transaction hash: {tx_hash.hex()}")
        print("   Waiting for confirmation...")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        print("\n✅ Transaction confirmed!")
        print(f"   Transaction hash : {receipt.transactionHash.hex()}")
        print(f"   Block number     : {receipt.blockNumber}")
        print(f"   Gas used         : {receipt.gasUsed}")
        print(
            f"   Status           : {'Success' if receipt.status == 1 else 'Failed'}"
        )

        return receipt
    except Exception as e:
        error_msg = str(e)
        if "revert" in error_msg.lower() or "execution reverted" in error_msg.lower():
            print(f'\n❌ Transaction "{method_name}" reverted: {error_msg}')
        elif "insufficient funds" in error_msg.lower():
            print(f'\n❌ Insufficient funds to send transaction "{method_name}".')
            print(
                "   Please ensure your account has enough balance to cover gas and value."
            )
        elif "nonce" in error_msg.lower():
            print(f'\n❌ Nonce conflict for transaction "{method_name}".')
            print("   Another transaction may be pending. Try again shortly.")
        else:
            print(f'\n❌ Transaction "{method_name}" failed: {error_msg}')
        raise


# ============================================================
# Write Method Functions
# ============================================================

{{METHOD_FUNCTIONS}}

# ============================================================
# Main
# ============================================================


def main():
    print("Connecting to {{NETWORK_NAME}} ...")
    w3 = get_web3()
    account = get_account(w3)
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=ABI
    )

    print(f"Signer address: {account.address}")

    # For payable methods, set the value (in wei) to send with the transaction:
    #   value = w3.to_wei(0.1, "ether")
    # Then pass value as the last argument to send_transaction.

    {{MAIN_EXAMPLE}}


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Unhandled error: {e}")
        sys.exit(1)
