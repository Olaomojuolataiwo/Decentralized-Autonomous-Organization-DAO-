import os
import time
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

# --- 1. INITIAL SETUP ---
load_dotenv()
w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
deployer_acct = Account.from_key(os.getenv("PRIVATE_KEY"))
deployer_addr = deployer_acct.address

MIN_DELAY = 130 

SCENARIOS = {
    "V3_OLD": {
        "DAO": "0x254F72604187ed373ed2b489019f480a1cbC975B",
        "TREASURY": "0xB6Eb0b2098D14C4538958c85dc71e3601260D491",
        "TYPE": "BASIC"
    },
    "V4_OLD": {
        "DAO": "0xe60A30b207B16634a30396c112B5E0DE11702dF8",
        "TREASURY": "0x3E7546fF271BA6503ac4Fcd02b79BD5a9db94C28",
        "TYPE": "SECURE"
    },
    "V3_NEW_OPTIMIZED": {
        "DAO": "0xcCaD7C3EfE882167826120960d951c42d30342Ff",
        "TREASURY": "0x8Db4684aF971Fe772A26141B12f4c710fe4478d0",
        "TYPE": "BASIC"
    },
    "V4_NEW_SECURE": {
        "DAO": "0x5a89a310ade0Ed6b9D2085Fb7E98A0AAE4BFcb6A",
        "TREASURY": "0x1A00DCf264B0A37e86B2D8852888fd7F59665856",
        "TYPE": "SECURE"
    }
}

# --- 2. FIXED ABIs (Including 'state') ---
DAO_ABI = [
    {"anonymous":False,"inputs":[{"indexed":False,"internalType":"uint256","name":"proposalId","type":"uint256"},{"indexed":False,"internalType":"address","name":"proposer","type":"address"},{"indexed":False,"internalType":"address[]","name":"targets","type":"address[]"},{"indexed":False,"internalType":"uint256[]","name":"values","type":"uint256[]"},{"indexed":False,"internalType":"string[]","name":"signatures","type":"string[]"},{"indexed":False,"internalType":"bytes[]","name":"calldatas","type":"bytes[]"},{"indexed":False,"internalType":"uint256","name":"voteStart","type":"uint256"},{"indexed":False,"internalType":"uint256","name":"voteEnd","type":"uint256"},{"indexed":False,"internalType":"string","name":"description","type":"string"}],"name":"ProposalCreated","type":"event"},
    {"inputs": [{"name": "targets", "type": "address[]"}, {"name": "values", "type": "uint256[]"}, {"name": "calldatas", "type": "bytes[]"}, {"name": "description", "type": "string"}], "name": "propose", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "proposalId", "type": "uint256"}, {"name": "support", "type": "uint8"}], "name": "castVote", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "proposalId", "type": "uint256"}], "name": "state", "outputs": [{"name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "targets", "type": "address[]"}, {"name": "values", "type": "uint256[]"}, {"name": "calldatas", "type": "bytes[]"}, {"name": "descriptionHash", "type": "bytes32"}], "name": "queue", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "targets", "type": "address[]"}, {"name": "values", "type": "uint256[]"}, {"name": "calldatas", "type": "bytes[]"}, {"name": "descriptionHash", "type": "bytes32"}], "name": "execute", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "payable", "type": "function"},
    {"inputs": [], "name": "token", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"}
]
TOKEN_ABI = [
    {"inputs": [{"name": "delegatee", "type": "address"}], "name": "delegate", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "account", "type": "address"}], "name": "getVotes", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}
]
TREASURY_ABI = [
    {"inputs": [{"name": "recipient", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "executePayment", "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "target", "type": "address"}, {"name": "allowed", "type": "bool"}], "name": "setAllowedTarget", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "target", "type": "address"}, {"name": "value", "type": "uint256"}, {"name": "data", "type": "bytes"}], "name": "execute", "outputs": [{"name": "", "type": "bytes"}], "stateMutability": "nonpayable", "type": "function"}
]

# --- 3. HELPERS ---
def send_tx(tx_func, gas=1000000):
    tx = tx_func.build_transaction({
        'from': deployer_addr,
        'nonce': w3.eth.get_transaction_count(deployer_addr),
        'gas': gas,
        'gasPrice': w3.eth.gas_price
    })
    signed = deployer_acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status == 0:
        raise Exception(f"Transaction failed at hash: {w3.to_hex(tx_hash)}")
    return receipt

def wait_for_state(dao_contract, prop_id, target_state, label):
    print(f"Waiting for state: {label}...")
    while True:
        current_state = dao_contract.functions.state(prop_id).call()
        if current_state == target_state:
            break
        if current_state == 3: raise Exception("Proposal Defeated.")
        time.sleep(15)

# --- 4. RECOVERY MISSION ---
def run_recovery_mission(name, config):
    print(f"\n--- MISSION: RECOVER {name} ---")
    
    # DYNAMIC BALANCE CHECK
    balance_wei = w3.eth.get_balance(config["TREASURY"])
    if balance_wei == 0:
        print(f"Skipping {name}: Treasury is empty.")
        return
    
    print(f"Balance to recover: {w3.from_wei(balance_wei, 'ether')} ETH")

    dao = w3.eth.contract(address=config["DAO"], abi=DAO_ABI)
    treasury = w3.eth.contract(address=config["TREASURY"], abi=TREASURY_ABI)

    # 1. Self-Delegate
    token_addr = dao.functions.token().call()
    token = w3.eth.contract(address=token_addr, abi=TOKEN_ABI)
    if token.functions.getVotes(deployer_addr).call() == 0:
        print(f"Delegating whale power...")
        send_tx(token.functions.delegate(deployer_addr))
        time.sleep(10)

    # 2. Build Proposal
    if config["TYPE"] == "BASIC":
        targets = [config["TREASURY"]]
        calldatas = [treasury.encode_abi("executePayment", [deployer_addr, balance_wei])]
    else: # SECURE
        targets = [config["TREASURY"], config["TREASURY"]]
        calldatas = [
            treasury.encode_abi("setAllowedTarget", [deployer_addr, True]),
            treasury.encode_abi("execute", [deployer_addr, balance_wei, b""])
        ]

    desc = f"Sweep {name} {int(time.time())}"
    desc_hash = w3.keccak(text=desc)

    # 3. Governance Lifecycle
    print("Proposing...")
    receipt = send_tx(dao.functions.propose(targets, [0]*len(targets), calldatas, desc))
    logs = dao.events.ProposalCreated().process_receipt(receipt)
    prop_id = logs[0]['args']['proposalId']
    
    wait_for_state(dao, prop_id, 1, "Active")
    send_tx(dao.functions.castVote(prop_id, 1))
    print("Whale vote cast.")
    
    wait_for_state(dao, prop_id, 4, "Succeeded")
    
    print("Queueing...")
    send_tx(dao.functions.queue(targets, [0]*len(targets), calldatas, desc_hash))
    
    print(f"Waiting {MIN_DELAY}s for Timelock...")
    time.sleep(MIN_DELAY)
    
    print("Executing final payout...")
    send_tx(dao.functions.execute(targets, [0]*len(targets), calldatas, desc_hash))
    print(f"DONE: {name} recovered!")

if __name__ == "__main__":
    start_bal = w3.eth.get_balance(deployer_addr)
    print(f"Initial Balance: {w3.from_wei(start_bal, 'ether')} ETH")
    
    for name, config in SCENARIOS.items():
        try:
            run_recovery_mission(name, config)
        except Exception as e:
            print(f"Failed {name}: {e}")
            
    end_bal = w3.eth.get_balance(deployer_addr)
    print(f"\nFinal Balance: {w3.from_wei(end_bal, 'ether')} ETH")
    
    diff = end_bal - start_bal
    if diff >= 0:
        print(f"Net Recovered: {w3.from_wei(diff, 'ether')} ETH")
    else:
        print(f"Net Loss (Gas): {w3.from_wei(abs(diff), 'ether')} ETH")
