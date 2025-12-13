#!/usr/bin/env python3
"""
fund_members.py

Loads addresses from both dao_members.json and dao_vul_members.json
and sends a small amount of Testnet ETH (0.001 ETH) to each address
from the deployer account to cover gas fees.
"""

import os
import json
import time
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
RPC_URL = os.getenv("RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")  # The funded deployer private key
CHAIN_ID = int(os.getenv("CHAIN_ID", "11155111"))  # Sepolia chain id default

# Files containing member addresses
OPT_MEMBERS_FILE = "dao_members.json"
VUL_MEMBERS_FILE = "../dao_vul_members.json"

# Amount of native currency (ETH/SepoliaETH) to send to each address
# 0.001 ETH is 1e15 Wei, which is enough for multiple transactions
FUNDING_AMOUNT_ETH = 0.0016

if not RPC_URL or not PRIVATE_KEY:
    raise SystemExit("RPC_URL and PRIVATE_KEY environment variables must be set.")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
owner_acct = Account.from_key(PRIVATE_KEY)
owner_addr = owner_acct.address

# Convert funding amount to Wei
FUNDING_AMOUNT_WEI = w3.to_wei(FUNDING_AMOUNT_ETH, 'ether')

print(f"--- MEMBER FUNDING SCRIPT ---")
print(f"RPC: {RPC_URL}")
print(f"Sender (Deployer): {owner_addr}")
print(f"Amount per address: {FUNDING_AMOUNT_ETH} ETH")
print(f"Chain ID: {CHAIN_ID}\n")

# --- HELPER FUNCTIONS ---

def load_all_member_addresses() -> set:
    """Loads all unique addresses from both member files."""
    all_addresses = set()
    
    # 1. Load Optimized Members
#    try:
#        with open(OPT_MEMBERS_FILE, "r") as f:
#            optimized_members = json.load(f)
#            for m in optimized_members:
#                all_addresses.add(Web3.to_checksum_address(m['address']))
#    except FileNotFoundError:
#        print(f"Warning: Optimized member file not found at {OPT_MEMBERS_FILE}")

    # 2. Load Vulnerable Members (using 'address' or 'privateKey' dictionary keys)
    try:
        with open(VUL_MEMBERS_FILE, "r") as f:
            vulnerable_members = json.load(f)
            for m in vulnerable_members:
                # Vulnerable members file uses 'address', Optimized uses 'address'
                addr_key = 'address' if 'address' in m else 'privateKey' 
                
                # Check if it's a private key or address, and handle accordingly
                if len(m.get(addr_key, "")) < 42: # if it's a private key, convert to address
                    # Note: We actually only need the 'address' key from dao_vul_members.json
                    # The structure of dao_vul_members.json shows 'address' is available
                    addr_to_add = Web3.to_checksum_address(m.get('address'))
                else:
                    addr_to_add = Web3.to_checksum_address(m.get('address'))
                
                all_addresses.add(addr_to_add)
    except FileNotFoundError:
        print(f"Warning: Vulnerable member file not found at {VUL_MEMBERS_FILE}")
        
    # Exclude the deployer/owner address from funding if it somehow got included
    if owner_addr in all_addresses:
        all_addresses.remove(owner_addr)

    return all_addresses

def send_eth_transaction(to_address: str, nonce: int) -> tuple[str, int]:
    """Builds, signs, and sends a simple ETH transfer transaction."""
    gas_price = w3.eth.gas_price
    
    # 1. Build the transaction
    tx = {
        'from': owner_addr,
        'to': to_address,
        'value': FUNDING_AMOUNT_WEI,
        'gas': 21000, # Base gas fee for ETH transfer
        'gasPrice': gas_price,
        'nonce': nonce,
        'chainId': CHAIN_ID,
    }

    # 2. Sign and Send
    signed_tx = owner_acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction).hex()
    
    # Wait for receipt
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
    
    if receipt.status != 1:
        raise Exception(f"Transaction Reverted for {to_address}: Tx hash {tx_hash}")

    return tx_hash, receipt.gasUsed

# --- MAIN EXECUTION ---
# --- MAIN EXECUTION ---
def main():
    if not w3.is_connected():
        print("Error: Could not connect to RPC URL.")
        return

    member_addresses = load_all_member_addresses()
    
    if not member_addresses:
        print("Error: No member addresses were loaded. Check your JSON files.")
        return
    # ... (connection and load_member_addresses code remains the same)
    print(f"Successfully loaded {len(member_addresses)} unique member addresses.")

    NUM_MEMBERS_TO_FUND = 62 
    member_addresses_list = list(member_addresses)
    members_to_fund = member_addresses_list[:NUM_MEMBERS_TO_FUND]

    
    # Get the current nonce for the sender (deployer)
    nonce = w3.eth.get_transaction_count(owner_addr)
    print(f"Starting transaction nonce: {nonce}")
    
    total_gas_spent = 0
    total_eth_sent = 0 # Initialize a cleaner variable for the total value
    successful_count = 0 # CRITICAL: New variable to track success
    
    # --- LOOP START ---
    for i, member_addr in enumerate(members_to_fund):
        
        # Check current balance of deployer before sending
        sender_balance = w3.eth.get_balance(owner_addr)
        if sender_balance < FUNDING_AMOUNT_WEI + w3.eth.gas_price * 21000:
            print("\nFATAL ERROR: Deployer account ran out of ETH for funding!")
            print(f"Please fund the deployer address ({owner_addr}) and restart.")
            # Added break here to stop execution if funds are insufficient
            break 
            
        # The progress indicator is now inside the properly indented loop
        print(f"[{i+1}/{NUM_MEMBERS_TO_FUND}] Sending {FUNDING_AMOUNT_ETH} ETH to {member_addr}...")

        try:
            # All logic below is now properly INSIDE the loop
            tx_hash, gas_used = send_eth_transaction(member_addr, nonce)
            total_gas_spent += gas_used
            total_eth_sent += FUNDING_AMOUNT_WEI # Changed to use the cleaner variable
            successful_count += 1 # Increment success counter
            print(f"    -> SUCCESS: Hash: {tx_hash} | Gas Used: {gas_used}")
            nonce += 1
            # Small pause to avoid RPC node throttling
            time.sleep(0.05)

        except Exception as e:
            print(f"    -> FAILURE: Error sending ETH to {member_addr}: {e}")
            # If a transaction fails, we stop to prevent nonce errors
            break 
    # --- LOOP ENDS HERE ---

    print("\n--- FUNDING COMPLETE ---")
    print(f"Funded {successful_count} addresses (out of {NUM_MEMBERS_TO_FUND}).")
    print(f"Total ETH sent (value): {w3.from_wei(total_eth_sent, 'ether')} ETH")
    print(f"Total gas used for funding: {total_gas_spent} gas")
    print("You can now re-run gas_optimizer.py.")

if __name__ == "__main__":
    main()
