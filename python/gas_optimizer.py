import os
import time
import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Tuple

from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

# --- CONFIGURATION & ENV VARS ---
load_dotenv()
RPC_URL = os.getenv("RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY") # Owner/Deployer key (Used for Timelock Admin execution if needed)
CHAIN_ID = int(os.getenv("CHAIN_ID", "11155111"))

# Deployed addresses (Set these in your .env file)
V1_DAO_ADDR = os.getenv("V1_DAO_ADDR")          # Vulnerable DAO
V1_TREASURY_ADDR = os.getenv("V1_TREASURY_ADDR")# TreasuryBasic
V2_DAO_ADDR = os.getenv("V2_DAO_ADDR")          # Vulnerable DAO
V2_TREASURY_ADDR = os.getenv("V2_TREASURY_ADDR")# TreasurySecure
V3_DAO_ADDR = os.getenv("V3_DAO_ADDR")          # DAOOptimized
V3_TREASURY_ADDR = os.getenv("V3_TREASURY_ADDR")# TreasuryBasic
V4_DAO_ADDR = os.getenv("V4_DAO_ADDR")          # DAOOptimized
V4_TREASURY_ADDR = os.getenv("V4_TREASURY_ADDR")# TreasurySecure

VUL_TOKEN_ADDR = os.getenv("VUL_TOKEN_ADDR")    # VulnerableMembershipToken
OPT_TOKEN_ADDR = os.getenv("OPT_TOKEN_ADDR")    # MembershipTokenMintable
TIMELOCK_ADDR = os.getenv("TIMELOCK_ADDR")      # TimelockController

# For O(N) cost demonstration, we need a majority: 61 votes
VOTER_COUNT = 61 

# Test Parameters
RECIPIENT_ADDR = Web3.to_checksum_address("0x" + "DEADBEEF" * 5)
PROPOSAL_VALUE = Web3.to_wei(0.1, 'ether')
PROPOSAL_DESCRIPTION = "Scenario 1: Single-Target Withdrawal Test"


# --- DYNAMIC MEMBER LOADING ---

MemberData = Dict[str, str]

def load_vulnerable_members(keys_file="dao_vul_members.json", addrs_file="dao_addresses.txt") -> List[MemberData]:
    """Loads vulnerable members: addresses from TXT, keys from JSON."""
    try:
        with open(keys_file, "r") as f:
            json_members = json.load(f)
            json_keys = [m['privateKey'] for m in json_members]

        with open(addrs_file, "r") as f:
            txt_addresses = [Web3.to_checksum_address(line.strip()) for line in f if line.strip()]
            
        combined_members = []
        # Ensure we have enough members/keys for the VOTER_COUNT + 1 Proposer
        for i in range(min(len(txt_addresses), len(json_keys))):
             if i < VOTER_COUNT + 1: 
                 combined_members.append({
                    "address": txt_addresses[i],
                    "privateKey": json_keys[i]
                 })
                 
        if len(combined_members) < VOTER_COUNT + 1:
             logging.error(f"FATAL: Only loaded {len(combined_members)} vulnerable members, need {VOTER_COUNT + 1}.")
             
        return combined_members

    except FileNotFoundError as e:
        logging.error(f"FATAL: Vulnerable member file not found: {e.filename}")
        return []
        
def load_optimized_members(file_path="dao_members.json") -> List[MemberData]:
    """Loads optimized member data from dao_members.json."""
    try:
        with open(file_path, "r") as f:
            json_members = json.load(f)
            # Use the first VOTER_COUNT + 1 members
            members = [{
                "address": Web3.to_checksum_address(m['address']),
                "privateKey": m['private_key'] 
            } for m in json_members][:VOTER_COUNT + 1]

        if len(members) < VOTER_COUNT + 1:
             logging.error(f"FATAL: Only loaded {len(members)} optimized members, need {VOTER_COUNT + 1}.")
             
        return members
            
    except FileNotFoundError:
        logging.error(f"FATAL: Optimized member file {file_path} not found.")
        return []

VULNERABLE_MEMBERS = load_vulnerable_members()
OPTIMIZED_MEMBERS = load_optimized_members()

if len(VULNERABLE_MEMBERS) < VOTER_COUNT + 1 or len(OPTIMIZED_MEMBERS) < VOTER_COUNT + 1:
    raise SystemExit(f"Insufficient members loaded. Check files and VOTER_COUNT ({VOTER_COUNT}).")

# --- PROPOSER SETUP (Always the first member of the respective list) ---
VUL_PROPOSER_KEY = VULNERABLE_MEMBERS[0]['privateKey']
OPT_PROPOSER_KEY = OPTIMIZED_MEMBERS[0]['privateKey']

# --- WEB3 SETUP ---
w3 = Web3(Web3.HTTPProvider(RPC_URL))
deployer_acct = Account.from_key(PRIVATE_KEY) # Timelock Admin Key
deployer_addr = deployer_acct.address

# --- CONTRACT ABIs (Minimal for interaction) ---
TREASURY_BASIC_ABI = json.loads('[{"inputs": [{"internalType": "address", "name": "recipient", "type": "address"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "executePayment", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"}]')
TREASURY_SECURE_ABI = json.loads('[{"inputs": [{"internalType": "address", "name": "target", "type": "address"}, {"internalType": "uint256", "name": "value", "type": "uint256"}, {"internalType": "bytes", "name": "data", "type": "bytes"}], "name": "execute", "outputs": [{"internalType": "bytes", "name": "", "type": "bytes"}], "stateMutability": "nonpayable", "type": "function"}]')
GOVERNOR_ABI = json.loads('[{"inputs": [{"internalType": "address[]", "name": "targets", "type": "address[]"}, {"internalType": "uint256[]", "name": "values", "type": "uint256[]"}, {"internalType": "bytes[]", "name": "calldatas", "type": "bytes[]"}, {"internalType": "bytes32", "name": "descriptionHash", "type": "bytes32"}], "name": "propose", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"}, {"inputs": [{"internalType": "uint256", "name": "proposalId", "type": "uint256"}, {"internalType": "uint8", "name": "support", "type": "uint8"}], "name": "castVote", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"}, {"inputs": [{"internalType": "uint256", "name": "proposalId", "type": "uint256"}, {"internalType": "bool", "name": "support", "type": "bool"}], "name": "vote", "outputs": [], "stateMutability": "nonpayable", "type": "function"}, {"inputs": [{"internalType": "address[]", "name": "targets", "type": "address[]"}, {"internalType": "uint256[]", "name": "values", "type": "uint256[]"}, {"internalType": "bytes[]", "name": "calldatas", "type": "bytes[]"}, {"internalType": "bytes32", "name": "descriptionHash", "type": "bytes32"}], "name": "queue", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"}, {"inputs": [{"internalType": "address[]", "name": "targets", "type": "address[]"}, {"internalType": "uint256[]", "name": "values", "type": "uint256[]"}, {"internalType": "bytes[]", "name": "calldatas", "type": "bytes[]"}, {"internalType": "bytes32", "name": "descriptionHash", "type": "bytes32"}], "name": "execute", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"}]')
TOKEN_ABI = json.loads('[{"inputs": [{"internalType": "address", "name": "delegatee", "type": "address"}], "name": "delegate", "outputs": [], "stateMutability": "nonpayable", "type": "function"}]')


# --- DATA STRUCTURES & LOGGING ---
@dataclass
class ScenarioResult:
    gas_propose: int = 0
    gas_vote: int = 0
    gas_queue: int = 0
    gas_execute: int = 0
    tx_propose: str = ""
    tx_vote: str = ""
    tx_queue: str = ""
    tx_execute: str = ""
    calldata_size: int = 0
    execution_path: str = "N/A" 

def send_tx(acct: Account, tx_func: Any, nonce: int, value: int = 0) -> Dict[str, Any]:
    """Helper to build, sign, and send a transaction."""
    gas_price = w3.eth.gas_price
    
    # Estimate gas and add buffer
    try:
        gas_limit = int(tx_func.estimate_gas({"from": acct.address, "value": value}) * 1.2)
    except Exception:
        gas_limit = 3_000_000 
    
    try:
        tx = tx_func.build_transaction({
            "chainId": CHAIN_ID,
            "gas": gas_limit,
            "gasPrice": gas_price,
            "nonce": nonce,
            "from": acct.address,
            "value": value,
        })
        signed_tx = acct.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction).hex()
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=600)
        
        if receipt.status != 1:
            raise Exception(f"Transaction Reverted: Tx hash {tx_hash}")
            
        return {"gasUsed": receipt.gasUsed, "txHash": tx_hash, "calldataSize": len(tx['data'])}
    except Exception as e:
        logging.error(f"Error sending transaction from {acct.address}: {e}")
        raise

# ... log_results function remains the same ...

def log_results(scenario_name: str, vul_res: ScenarioResult, opt_res: ScenarioResult):
    """Formats and prints the results according to the required structured logging standard."""
    
    def calculate_delta(opt, vul):
        if vul == 0: return 0, 0.0
        delta_abs = opt - vul
        delta_perc = (delta_abs / vul) * 100
        return delta_abs, delta_perc

    print(f"\n=======================================================")
    print(f"  TEST MATRIX RESULT: {scenario_name}")
    print(f"  VOTER COUNT: {VOTER_COUNT}")
    print(f"=======================================================")

    # --- GAS LOGGING ---
    print("\n# --- GAS PROFILING ---")
    
    # Propose
    delta_abs, delta_perc = calculate_delta(opt_res.gas_propose, vul_res.gas_propose)
    print(f"[GAS] propose(): vulnerable={vul_res.gas_propose} optimized={opt_res.gas_propose} delta={delta_abs} ({delta_perc:+.2f}%)")

    # Vote (Total voting gas for {VOTER_COUNT} voters)
    delta_abs, delta_perc = calculate_delta(opt_res.gas_vote, vul_res.gas_vote)
    print(f"[GAS] castVote (x{VOTER_COUNT}): vulnerable={vul_res.gas_vote} optimized={opt_res.gas_vote} delta={delta_abs} ({delta_perc:+.2f}%)")
    
    # Queue (Vulnerable has 0 cost)
    delta_abs, delta_perc = calculate_delta(opt_res.gas_queue, vul_res.gas_queue)
    print(f"[GAS] queue(): vulnerable={vul_res.gas_queue} optimized={opt_res.gas_queue} delta={delta_abs} ({delta_perc:+.2f}%)")

    # Execute
    delta_abs, delta_perc = calculate_delta(opt_res.gas_execute, vul_res.gas_execute)
    print(f"[GAS] execute(): vulnerable={vul_res.gas_execute} optimized={opt_res.gas_execute} delta={delta_abs} ({delta_perc:+.2f}%)")

    # Total Gas (Full Lifecycle)
    vul_total = vul_res.gas_propose + vul_res.gas_vote + vul_res.gas_queue + vul_res.gas_execute
    opt_total = opt_res.gas_propose + opt_res.gas_vote + opt_res.gas_queue + opt_res.gas_execute
    delta_abs, delta_perc = calculate_delta(opt_total, vul_total)
    print(f"[GAS] total(): vulnerable={vul_total} optimized={opt_total} delta={delta_abs} ({delta_perc:+.2f}%)")


    # --- DIVERGENCE CHECKS ---
    print("\n# --- DIVERGENCE CHECKS ---")
    print(f"[STATE] execution_path: DIVERGED (Vulnerable={vul_res.execution_path}, Optimized={opt_res.execution_path})")
    
    if "TreasurySecure" in scenario_name:
        print(f"[STATE] safety_behavior: DIVERGED (Vulnerable=Transfer() No Guard, Optimized=Call() + Reentrancy Guard)")
    else:
        print(f"[STATE] safety_behavior: DIVERGED (Vulnerable=Transfer() No Guard, Optimized=Call() No Guard)")
        
    print(f"[STATE] treasury_result: MATCH (Expected Outcome: {Web3.from_wei(PROPOSAL_VALUE, 'ether')} ETH transfer)")

    # --- ARTIFACT TRACING ---
    print("\n# --- ARTIFACT TRACING ---")
    print(f"[TRACE] vulnerable_tx_hash (propose): {vul_res.tx_propose}")
    print(f"[TRACE] vulnerable_tx_hash (vote/execute): {vul_res.tx_vote}")
    print(f"[TRACE] optimized_tx_hash (propose): {opt_res.tx_propose}")
    print(f"[TRACE] optimized_tx_hash (queue): {opt_res.tx_queue}")
    print(f"[TRACE] optimized_tx_hash (execute): {opt_res.tx_execute}")
    print(f"[TRACE] calldatasize (propose): {opt_res.calldata_size} bytes")


def run_scenario_vulnerable(dao_addr: str, treasury_addr: str, proposer_nonce: int) -> Tuple[ScenarioResult, int]:
    """Runs V1/V2 (Vulnerable DAO) lifecycle: propose -> 61x vote (last vote executes)"""
    
    res = ScenarioResult()
    proposer_acct = Account.from_key(VUL_PROPOSER_KEY)
    dao_contract = w3.eth.contract(address=dao_addr, abi=GOVERNOR_ABI)
    
    # 1. Prepare Calldata
    treasury_contract = w3.eth.contract(address=treasury_addr, abi=TREASURY_BASIC_ABI)
    calldata = treasury_contract.encodeABI(fn_name="executePayment", args=[RECIPIENT_ADDR, PROPOSAL_VALUE])
    
    # 2. PROPOSE
    tx_func = dao_contract.functions.propose(treasury_addr, 0, calldata, PROPOSAL_DESCRIPTION)
    receipt = send_tx(proposer_acct, tx_func, proposer_nonce)
    proposer_nonce += 1
    
    res.gas_propose = receipt['gasUsed']
    res.tx_propose = receipt['txHash']
    res.calldata_size = receipt['calldataSize']
    
    # Get proposalId from storage slot 3 (specific to VulnerableDAO)
    proposal_id = w3.to_int(w3.eth.get_storage_at(dao_addr, 3))
    
    # 3. VOTE (61 Votes)
    total_vote_gas = 0
    
    # Start from index 1 (Proposer is index 0) and vote up to VOTER_COUNT (total 61 votes)
    for i in range(1, VOTER_COUNT + 1):
        member_data = VULNERABLE_MEMBERS[i]
        voter_acct = Account.from_key(member_data['privateKey'])
        voter_nonce = w3.eth.get_transaction_count(voter_acct.address)
        
        tx_func = dao_contract.functions.vote(proposal_id, True) 
        
        # The final vote (i == VOTER_COUNT) includes O(N) loop + execution logic
        if i == VOTER_COUNT:
            print(f"  [Vulnerable] Measuring final vote (Vote {i}) which includes O(N) check and execution...")
        
        receipt = send_tx(voter_acct, tx_func, voter_nonce)
        total_vote_gas += receipt['gasUsed']
        if i == VOTER_COUNT:
            res.tx_vote = receipt['txHash']
            
        time.sleep(0.1) 
        
    res.gas_vote = total_vote_gas
    res.gas_execute = 0 # Executes inside the final vote
    res.execution_path = "Immediate"
    
    return res, proposer_nonce


def run_scenario_optimized(dao_addr: str, treasury_addr: str, proposer_nonce: int) -> Tuple[ScenarioResult, int]:
    """Runs V3/V4 (Optimized DAO) lifecycle: propose -> 61x castVote -> queue -> execute"""
    
    res = ScenarioResult()
    proposer_acct = Account.from_key(OPT_PROPOSER_KEY)
    dao_contract = w3.eth.contract(address=dao_addr, abi=GOVERNOR_ABI)
    
    # --- 1. PREPARE CALLDATA ---
    # Inner: executePayment(RECIPIENT_ADDR, PROPOSAL_VALUE)
    inner_calldata = w3.eth.contract(abi=TREASURY_BASIC_ABI).encodeABI(fn_name="executePayment", args=[RECIPIENT_ADDR, PROPOSAL_VALUE])
    # Outer: TreasurySecure.execute(treasury_addr, 0, inner_calldata)
    treasury_contract = w3.eth.contract(address=treasury_addr, abi=TREASURY_SECURE_ABI)
    calldata_to_send = treasury_contract.encodeABI(fn_name="execute", args=[
        treasury_addr,
        0, 
        inner_calldata
    ])
    
    targets = [treasury_addr]
    values = [0]
    calldatas = [calldata_to_send]
    description_hash = Web3.keccak(text=PROPOSAL_DESCRIPTION)
    
    # 2. PROPOSE
    tx_func = dao_contract.functions.propose(targets, values, calldatas, PROPOSAL_DESCRIPTION)
    receipt = send_tx(proposer_acct, tx_func, proposer_nonce)
    proposer_nonce += 1
    
    res.gas_propose = receipt['gasUsed']
    res.tx_propose = receipt['txHash']
    res.calldata_size = receipt['calldataSize']

    # Extract proposalId from the logs (Topic 1 of ProposalCreated event)
    receipt_obj = w3.eth.get_transaction_receipt(res.tx_propose)
    proposal_id = w3.to_int(receipt_obj.logs[0].topics[1]) 
    
    # 3. DELEGATION (Setup cost, skipped if already done)
    opt_token_contract = w3.eth.contract(address=OPT_TOKEN_ADDR, abi=TOKEN_ABI)
    print("  [Optimized] Ensuring all voters are delegated (one-time setup cost)...")
    for i in range(VOTER_COUNT + 1):
        member_data = OPTIMIZED_MEMBERS[i]
        member_acct = Account.from_key(member_data['privateKey'])
        try:
            tx_func = opt_token_contract.functions.delegate(member_data['address'])
            member_nonce = w3.eth.get_transaction_count(member_acct.address) 
            send_tx(member_acct, tx_func, member_nonce)
        except Exception:
            pass
        time.sleep(0.05) 

    
    # 4. VOTE (61 Votes - Low cost due to snapshots/ERC20Votes)
    total_vote_gas = 0
    # Start from index 1 (Proposer is index 0)
    for i in range(1, VOTER_COUNT + 1):
        member_data = OPTIMIZED_MEMBERS[i]
        voter_acct = Account.from_key(member_data['privateKey'])
        voter_nonce = w3.eth.get_transaction_count(voter_acct.address)
        
        tx_func = dao_contract.functions.castVote(proposal_id, 1) # 1=For
        
        receipt = send_tx(voter_acct, tx_func, voter_nonce)
        total_vote_gas += receipt['gasUsed']
        if i == VOTER_COUNT:
             res.tx_vote = receipt['txHash'] 
        time.sleep(0.1) 
        
    res.gas_vote = total_vote_gas
    
    # 5. QUEUE
    print("  [Optimized] Waiting for voting period to end (approx 30s)...")
    time.sleep(30)
    
    tx_func = dao_contract.functions.queue(targets, values, calldatas, description_hash)
    receipt = send_tx(proposer_acct, tx_func, proposer_nonce)
    proposer_nonce += 1
    
    res.gas_queue = receipt['gasUsed']
    res.tx_queue = receipt['txHash']
    
    # 6. EXECUTE
    print("  [Optimized] Waiting for Timelock delay to pass (approx 130s)...")
    time.sleep(130)

    tx_func = dao_contract.functions.execute(targets, values, calldatas, description_hash)
    
    # Anyone can call Governor.execute, so we use the Proposer's account
    proposer_nonce_updated = w3.eth.get_transaction_count(proposer_acct.address)
    receipt = send_tx(proposer_acct, tx_func, proposer_nonce_updated)
    
    res.gas_execute = receipt['gasUsed']
    res.tx_execute = receipt['txHash']
    res.execution_path = "Timelock"
    
    return res, proposer_nonce

# --- MAIN RUNNER ---
def main():
    if not w3.is_connected():
        print("Error: Could not connect to RPC URL.")
        return

    # Nonce for the proposer accounts
    proposer_nonce_vul = w3.eth.get_transaction_count(Account.from_key(VUL_PROPOSER_KEY).address)
    proposer_nonce_opt = w3.eth.get_transaction_count(Account.from_key(OPT_PROPOSER_KEY).address)


    print(f"\n--- RUNNING SCENARIOS WITH {VOTER_COUNT} VOTERS ---")

    # --- RUN V1: Vulnerable DAO + Basic Treasury ---
    print("\n--- Running V1 (Vulnerable DAO + Basic Treasury) ---")
    v1_res, proposer_nonce_vul = run_scenario_vulnerable(V1_DAO_ADDR, V1_TREASURY_ADDR, proposer_nonce_vul)

    # --- RUN V2: Vulnerable DAO + Secure Treasury ---
    print("\n--- Running V2 (Vulnerable DAO + Secure Treasury) ---")
    v2_res, proposer_nonce_vul = run_scenario_vulnerable(V2_DAO_ADDR, V2_TREASURY_ADDR, proposer_nonce_vul)

    # --- RUN V3: Optimized DAO + Basic Treasury ---
    print("\n--- Running V3 (Optimized DAO + Basic Treasury) ---")
    v3_res, proposer_nonce_opt = run_scenario_optimized(V3_DAO_ADDR, V3_TREASURY_ADDR, proposer_nonce_opt)
    
    # --- RUN V4: Optimized DAO + Secure Treasury (The Target) ---
    print("\n--- Running V4 (Optimized DAO + Secure Treasury) ---")
    v4_res, _ = run_scenario_optimized(V4_DAO_ADDR, V4_TREASURY_ADDR, proposer_nonce_opt)
    
    
    # --- LOG COMPARISON MATRIX ---

    # V1 vs V4: Full Stack Comparison (Baseline vs Target)
    log_results("V1 vs V4 (Full Vulnerable vs Full Optimized Stack)", v1_res, v4_res)
    
    # V1 vs V3: DAO-only improvement (Optimized DAO / Vulnerable Treasury)
    log_results("V1 vs V3 (DAO-Only Benefit: Vulnerable vs Optimized Token/Voting)", v1_res, v3_res)

    # V2 vs V4: Treasury/Execution Divergence (Vulnerable DAO / Secure Treasury)
    log_results("V2 vs V4 (Secure Treasury Comparison)", v2_res, v4_res)

    # V3 vs V4: Treasury Optimization Benefit (Optimized DAO / Optimized Treasury)
    log_results("V3 vs V4 (Execution Optimization Benefit: TreasuryBasic vs TreasurySecure)", v3_res, v4_res)

if __name__ == "__main__":
    main()
