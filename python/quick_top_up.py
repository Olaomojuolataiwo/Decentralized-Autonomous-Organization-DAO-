import os
import time
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

# --- 1. SETUP ---
load_dotenv()
w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
deployer_acct = Account.from_key(os.getenv("PRIVATE_KEY"))
deployer_addr = deployer_acct.address

# DAO and Treasury pairs
SCENARIOS = {
    "V3_NEW_OPTIMIZED": {
        "DAO": "0xcCaD7C3EfE882167826120960d951c42d30342Ff",
        "TREASURY": "0x8Db4684aF971Fe772A26141B12f4c710fe4478d0"
    },
    "V4_NEW_SECURE": {
        "DAO": "0x5a89a310ade0Ed6b9D2085Fb7E98A0AAE4BFcb6A",
        "TREASURY": "0x1A00DCf264B0A37e86B2D8852888fd7F59665856"
    }
}

DAO_ABI = [
    {"inputs": [], "name": "quorumNumerator", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "token", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"}
]
TOKEN_ABI = [
    {"inputs": [{"name": "delegatee", "type": "address"}], "name": "delegate", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "account", "type": "address"}], "name": "getVotes", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"}
]

def send_signed_tx(to_addr, value_wei, data=b""):
    nonce = w3.eth.get_transaction_count(deployer_addr)
    tx = {
        'to': to_addr,
        'value': value_wei,
        'gas': 100000 if data else 21000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce,
        'data': data,
        'chainId': w3.eth.chain_id
    }
    signed = deployer_acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Transaction sent: {w3.to_hex(tx_hash)}")
    return w3.eth.wait_for_transaction_receipt(tx_hash)

def prepare_and_fund():
    print(f"Initiating readiness check for: {deployer_addr}\n")
    
    for name, addrs in SCENARIOS.items():
        print(f"--- Processing {name} ---")
        dao = w3.eth.contract(address=addrs["DAO"], abi=DAO_ABI)
        token_addr = dao.functions.token().call()
        token = w3.eth.contract(address=token_addr, abi=TOKEN_ABI)

        # 1. Check/Fix Voting Power
        balance = token.functions.balanceOf(deployer_addr).call()
        votes = token.functions.getVotes(deployer_addr).call()
        
        if balance > 0 and votes == 0:
            print(f"Found {w3.from_wei(balance, 'ether')} tokens but 0 voting power. Delegating to self...")
            data = token.encode_abi("delegate", [deployer_addr])
            send_signed_tx(token_addr, 0, data)
            print("Delegation complete. Waiting for checkpoint...")
            time.sleep(5)
            votes = token.functions.getVotes(deployer_addr).call()

        # 2. Check Quorum
        total_supply = token.functions.totalSupply().call()
        q_num = dao.functions.quorumNumerator().call()
        required = (total_supply * q_num) // 100
        
        if votes >= required and votes > 0:
            print(f"✅ Quorum Met ({w3.from_wei(votes, 'ether')} >= {w3.from_wei(required, 'ether')})")
            # 3. Fund Treasury
            print(f"Funding Treasury {addrs['TREASURY']}...")
            send_signed_tx(addrs['TREASURY'], w3.to_wei(0.05, 'ether'))
            print(f"💰 Funded 0.05 ETH successfully.")
        else:
            print(f"❌ Cannot proceed: Voting power ({w3.from_wei(votes, 'ether')}) is below quorum.")
        
        print("-" * 40)

if __name__ == "__main__":
    prepare_and_fund()
    print("\nCheck complete. If all were successful, run gas-runner.py now.")
