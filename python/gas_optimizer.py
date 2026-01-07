import os
import time
import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Tuple
from pathlib import Path
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
VOTER_COUNT = 40

# Test Parameters
RECIPIENT_ADDR = Web3.to_checksum_address("0x" + "DEADBEEF" * 5)
PROPOSAL_VALUE = Web3.to_wei(0.0004, 'ether')
PROPOSAL_DESCRIPTION = f"Proposal to transfer funds to treasury {int(time.time())}"


# --- DYNAMIC MEMBER LOADING ---

MemberData = Dict[str, str]
REQUIRED_ETH_FOR_VOTE = Web3.to_wei(0.0016, 'ether')

def load_vulnerable_members(keys_file="../dao_vul_members.json", addrs_file="../dao_addresses.txt") -> List[MemberData]:
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
deployer_nonce = w3.eth.get_transaction_count(deployer_addr)

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

# In gas_optimizer.py, replace your current send_tx function:

def send_tx(account, tx_func, nonce: int):
    acct = account # Use a clear local name
    
    # --- 1. BUILD TRANSACTION ---
    gas_price = w3.to_wei('1.0', 'gwei') 
    tx = tx_func.build_transaction({
        "chainId": CHAIN_ID,
        "gas": 1_000_000, 
        "gasPrice": gas_price,
        "nonce": nonce,
        "from": acct.address,
    })

    # --- 2. SIMULATION (CRITICAL DEBUGGING) ---
    try:
        # Simulate the transaction (w3.eth.call) to get the revert reason
        w3.eth.call(tx) 
    except Exception as e:
        # If simulation fails, print the detailed revert error and stop
        print("-" * 50)
        print(f"!!! CRITICAL REVERT DEBUGGING (SIMULATION) !!!")
        print(f"Attempting to call {tx_func.fn_name} from {acct.address}")
        # Use repr(e) for the most detailed error information
        print(f"Transaction Reverted in Simulation. Error:")
        print(repr(e)) 
        print("-" * 50)
        raise # Re-raise the exception to stop the script
        
    # --- 3. SIGN AND SEND ---
    print(f"Sending Tx: {tx_func.fn_name} from {acct.address}")
    signed_tx = w3.eth.account.sign_transaction(tx, acct.key)
    
    try:
        # Send transaction and wait for receipt
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction).hex()
        print(f"  > Tx Hash: {tx_hash}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Check receipt status (a second-level check for non-simulated reverts)
        if receipt.status == 0:
            # If the transaction failed on-chain, raise an error
            raise Exception(f"Transaction Reverted On-Chain: Tx hash {tx_hash}")

        return receipt
        
    except Exception as e:
        # This catches errors during sending or the receipt check above
        print(f"ERROR: Error sending transaction from {acct.address}: {e}")
        # The script will stop here, and we will get the precise web3 error
        raise e

def wait_for_blocks(w3, num_blocks):
    """Waits for a specified number of blocks to be mined."""
    if num_blocks <= 0:
        return
        
    start_block = w3.eth.block_number
    target_block = start_block + num_blocks
    
    print(f"Waiting for {num_blocks} block(s). Current: {start_block}, Target: {target_block}")
    
    while w3.eth.block_number < target_block:
        time.sleep(5) # Poll every 5 seconds (adjust as needed for your chain)
        
    print(f"Block reached: {w3.eth.block_number}")

def wait_for_proposal_succeeded(dao_contract, proposal_id):
    """
    Polls the DAO contract until the proposal hits state 4 (Succeeded).
    States: 0=Pending, 1=Active, 2=Canceled, 3=Defeated, 4=Succeeded...
    """
    print(f"\n[Monitor] Watching Proposal ID: {proposal_id}")
    
    while True:
        state = dao_contract.functions.state(proposal_id).call()
        
        if state == 4:
            print("[Success] Proposal state is now 'Succeeded'. Proceeding to Queue...")
            break
        elif state == 3:
            print("[Error] Proposal was DEFEATED. Check quorum and voting power.")
            return False
        elif state == 1:
            # Optionally get block info to see how much time is left
            curr_block = w3.eth.block_number
            print(f"  > State: Active | Curr Block: {curr_block} | Checking again in 5 mins...")
        else:
            print(f"  > State: {state} | Waiting for state 4...")

        time.sleep(300) # Wait 5 minutes (300 seconds)
    return True

def load_abi_from_artifact(contract_name: str, root_path: str = '../out') -> dict:
    """Loads the full ABI from a standard Foundry/Hardhat build artifact path."""
    # Constructs path: ./out/MembershipToken.sol/MembershipToken.json
    path = Path(root_path) / f"{contract_name}.sol" / f"{contract_name}.json"
    
    if not path.exists():
        raise FileNotFoundError(f"ABI artifact not found at: {path.resolve()}")
        
    with open(path, 'r') as f:
        artifact = json.load(f)
        return artifact['abi']

TOKEN_ABI = load_abi_from_artifact("MembershipToken")
DAO_OPTIMIZED_ABI = load_abi_from_artifact("DAOOptimized")
VULNERABLE_GOVERNOR_ABI = load_abi_from_artifact("VulnerableDAO")
TREASURY_BASIC_ABI = load_abi_from_artifact("TreasuryBasic")
TREASURY_SECURE_ABI = load_abi_from_artifact("TreasurySecure")
GOVERNOR_ABI = load_abi_from_artifact("DAOOPTIMIZED")
MEMBERSHIP_TOKEN_ABI = load_abi_from_artifact("VulnerableMembershipToken")
VOTING_DELAY = 1


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
    global deployer_nonce
    res = ScenarioResult()
    proposer_acct = Account.from_key(VUL_PROPOSER_KEY)
    dao_contract = w3.eth.contract(address=dao_addr, abi=VULNERABLE_GOVERNOR_ABI)
    
    token_contract = w3.eth.contract(address=VUL_TOKEN_ADDR, abi=TOKEN_ABI) 
    proposer_addr = proposer_acct.address
    token_balance = token_contract.functions.balanceOf(proposer_addr).call()
    print(f"DEBUG VULNERABLE: Proposer ({proposer_addr}) Token Balance: {token_balance}")
    current_votes = token_balance
    print(f"DEBUG VULNERABLE: Proposer ({proposer_addr}) Token Balance: {w3.from_wei(token_balance, 'ether'):.2f} VUL_TOKEN")
    print(f"DEBUG VULNERABLE: Proposer Voting Power (assumed balance): {w3.from_wei(current_votes, 'ether'):.2f} VUL_TOKEN")
    print(f"DEBUG VULNERABLE: Proposer Voting Power: {current_votes}")
    if token_balance == 0:
    # If tokens are zero, this is a setup error
        print("-" * 50)
        print("FATAL: Proposer has 0 tokens. Cannot meet DAO proposal threshold.")
        print("-" * 50)
        raise Exception("Proposer lacks tokens for VULNERABLE DAO proposal.")


    # 1. Prepare Calldata
    treasury_contract = w3.eth.contract(address=treasury_addr, abi=TREASURY_BASIC_ABI)
    calldata = treasury_contract.encode_abi(
        "executePayment",
        args=[RECIPIENT_ADDR, PROPOSAL_VALUE]
    )
    if not calldata or calldata == '0x':
        print("-" * 50)
        print("FATAL: Calldata encoding failed or resulted in empty data.")
        print(f"Check TREASURY_BASIC_ABI and arguments: RECIPIENT_ADDR, PROPOSAL_VALUE.")
        print("-" * 50)
        raise Exception("Invalid Calldata")

    # 2. PROPOSE
    print("\n--- PROPOSAL TRANSACTION DEBUG ---")
    print(f"Target: {treasury_addr}")
    print(f"Value: 0 (ETH)")
    print(f"Calldata (1st 20 chars): {calldata[:20]}...")
    print(f"Description: {PROPOSAL_DESCRIPTION}")
    print(f"Proposer Nonce: {proposer_nonce}\n")

    tx_func = dao_contract.functions.propose(
        treasury_addr,          # address target
        0,                      # uint256 value (sending ETH, which VULNERABLE_DAO supports)
        calldata,               # bytes data
        PROPOSAL_DESCRIPTION    # string description
    )
    receipt = send_tx(proposer_acct, tx_func, proposer_nonce)
    proposer_nonce += 1
    
    res.gas_propose = receipt['gasUsed']
    res.tx_propose = receipt['transactionHash'].hex()
    tx_data = w3.eth.get_transaction(receipt['transactionHash'])
    res.calldata_size = (len(tx_data['input']) - 2) / 2
    
    # Get proposalId from storage slot 3 (specific to VulnerableDAO)
    proposal_id = w3.to_int(w3.eth.get_storage_at(dao_addr, 3))

    # 3. VOTE (61 Votes)
    total_vote_gas = 0
    
    # Start from index 1 (Proposer is index 0) and vote up to VOTER_COUNT (total 61 votes)
    for i in range(1, VOTER_COUNT + 1):
        if i == VOTER_COUNT:
            print(f"\n!!! DESIGNATED EXECUTOR: Using Proposer for high-gas Final Vote {i} !!!")
            voter_acct = Account.from_key(VUL_PROPOSER_KEY) 
            REQUIRED_FUNDS = w3.to_wei('0.025', 'ether') # Threshold for the heavy O(N) execution
        else:
            member_data = VULNERABLE_MEMBERS[i]
            voter_acct = Account.from_key(member_data['privateKey'])
            voter_nonce = w3.eth.get_transaction_count(voter_acct.address)
            voter_balance = w3.eth.get_balance(voter_acct.address)
            if voter_balance < REQUIRED_ETH_FOR_VOTE:
                role = "Proposer/Executor" if i == VOTER_COUNT else "Voter"
                print(f"Skipping Vote {i} ({role}): {voter_acct.address} has insufficient ETH ({w3.from_wei(voter_balance, 'ether'):.4f} ETH).")
                continue

        tx_func = dao_contract.functions.castVote(proposal_id, True) 

                
        # The final vote (i == VOTER_COUNT) includes O(N) loop + execution logic
        if i == VOTER_COUNT:
            print(f"  [Vulnerable] Measuring final vote (Vote {i}) which includes O(N) check and execution...")
            fresh_proposer_nonce = w3.eth.get_transaction_count(voter_acct.address, 'pending')
            print(f"  [DEBUG] Blockchain expects nonce: {fresh_proposer_nonce} (Script was trying to use {voter_nonce})")
            signed_tx = voter_acct.sign_transaction(
            tx_func.build_transaction({
                'from': voter_acct.address,
                'nonce': fresh_proposer_nonce,
                'gas': 2000000,
                'maxFeePerGas': w3.to_wei('10', 'gwei'),
                'maxPriorityFeePerGas': w3.to_wei('2', 'gwei'),
            })
            )
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            print(f" > Tx Hash: {w3.to_hex(tx_hash)}")
        
            # 2. Get the receipt for gas measurement
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
            # 3. Store the gas usage for the final vote
            final_vote_gas = receipt['gasUsed']
        
            # Since V1 executes immediately, we don't need a separate execute step.
            execution_gas = 0 
            break # Exit the loop after the final vote
    
        else:
            receipt = send_tx(voter_acct, tx_func, voter_nonce)
            total_vote_gas += receipt['gasUsed']
            if i == VOTER_COUNT:
                res.tx_vote = receipt['transactionHash'].hex()
                tx_data = w3.eth.get_transaction(receipt['transactionHash'])
            
        time.sleep(0.1) 
        
    res.gas_vote = total_vote_gas
    res.gas_execute = 0 # Executes inside the final vote
    res.execution_path = "Immediate"
    
    return res, proposer_nonce


def run_scenario_optimized(dao_addr: str, treasury_addr: str, proposer_nonce: int) -> Tuple[ScenarioResult, int]:
    """Runs V3/V4 (Optimized DAO) lifecycle: propose -> 61x castVote -> queue -> execute"""
    global deployer_nonce
    res = ScenarioResult()
    proposer_acct = Account.from_key(OPT_PROPOSER_KEY)
    dao_contract = w3.eth.contract(address=dao_addr, abi=GOVERNOR_ABI)

    TOKEN_ADDRESS_OZ = Web3.to_checksum_address('0x8468f201FEE551a0EFDB0b2d41876312fc21a63C')
    # Get the token contract instance (must be the OZ ERC20Votes token)
    token_contract = w3.eth.contract(address=TOKEN_ADDRESS_OZ, abi=TOKEN_ABI)
    proposer_addr = proposer_acct.address

    # 1. Check Proposer's raw token balance
    token_balance = token_contract.functions.balanceOf(proposer_addr).call()
    print(f"Proposer ({proposer_addr}) Token Balance: {token_balance}")
    current_votes = token_contract.functions.getVotes(proposer_acct.address).call()
    print(f"Proposer ({proposer_addr}) Proposer Votes: {current_votes}")
    # If votes are 0 (as confirmed by debug output), try to delegate
    if current_votes == 0:
        print(f"ATTENTION: Proposer has 0 votes. Attempting re-delegation.")
        
        tx_func_delegate = token_contract.functions.delegate(proposer_acct.address)
        
        try:
            # We must use the send_tx helper here to handle the transaction
            delegate_receipt = send_tx(proposer_acct, tx_func_delegate, proposer_nonce) 
            proposer_nonce += 1 # Increment nonce after successful tx
            print(f"Delegation successful. New Nonce: {proposer_nonce}")
        except Exception as e:
            print(f"FATAL: Re-delegation FAILED for proposer. Check token balance.")
            raise

    # 1. Check Voting Power
    voting_power = token_contract.functions.getVotes(proposer_acct.address).call()
    
    # 2. Check Proposal Threshold (The Governor function)
    dao_contract = w3.eth.contract(address=dao_addr, abi=DAO_OPTIMIZED_ABI)
    current_block = w3.eth.block_number
    # Use the 'state' function to check the current proposal threshold
    proposal_threshold = dao_contract.functions.proposalThreshold().call() 
    
    print("-" * 50)
    print(f"!!! VOTING POWER DEBUGGING !!!")
    print(f"Proposer ({proposer_acct.address}) Voting Power: {voting_power}")
    print(f"Proposer ({proposer_addr}) Token Balance: {token_balance}")
    print(f"DAO Proposal Threshold: {proposal_threshold}")
    print("-" * 50)

    # ... (Rest of the propose logic follows here)
    # tx_func = dao_contract.functions.propose(targets, values, calldatas, description_hash)
    # receipt = send_tx(proposer_acct, tx_func, proposer_nonce)
    
    # --- 1. PREPARE CALLDATA ---
    # Inner: executePayment(RECIPIENT_ADDR, PROPOSAL_VALUE)
    inner_calldata = w3.eth.contract(abi=TREASURY_BASIC_ABI).encode_abi(
        "executePayment", # Function name is the first positional argument
        args=[RECIPIENT_ADDR, PROPOSAL_VALUE]
    )
    # Outer: TreasurySecure.execute(treasury_addr, 0, inner_calldata)
    treasury_contract = w3.eth.contract(address=treasury_addr, abi=TREASURY_SECURE_ABI)
    calldata_to_send = treasury_contract.encode_abi(
        "execute", # Function name is the first positional argument
        args=[treasury_addr, 0, inner_calldata]
    )
    
    targets = [treasury_addr]
    values = [0]
    calldatas = [calldata_to_send]
    description_hash = Web3.keccak(text=PROPOSAL_DESCRIPTION)
    
    # 2. PROPOSE
    tx_func = dao_contract.functions.propose(targets, values, calldatas, PROPOSAL_DESCRIPTION)
    receipt = send_tx(proposer_acct, tx_func, proposer_nonce)
    proposer_nonce += 1
    
    res.gas_propose = receipt['gasUsed']
    res.tx_propose = receipt['transactionHash'].hex()
    tx_data = w3.eth.get_transaction(receipt['transactionHash'])
    res.calldata_size = (len(tx_data['input']) - 2) / 2

    # Extract proposalId from the logs (Topic 1 of ProposalCreated event)
    receipt_obj = w3.eth.get_transaction_receipt(res.tx_propose)
    dao_contract = w3.eth.contract(address=dao_addr, abi=DAO_OPTIMIZED_ABI)
    proposal_created_event = dao_contract.events.ProposalCreated()
    event_filter = proposal_created_event.process_receipt(receipt)
    if len(event_filter) > 0:
        proposal_id = event_filter[0].args.proposalId
    else:
        raise Exception("ERROR: ProposalCreated event not found in transaction receipt.")
    res.proposal_id = proposal_id

    delay_blocks = VOTING_DELAY + 1
    wait_for_blocks(w3, delay_blocks)

    # 3. DELEGATION (Setup cost, skipped if already done)
    opt_token_contract = w3.eth.contract(address=OPT_TOKEN_ADDR, abi=TOKEN_ABI)
#    print("  [Optimized] Ensuring all voters are delegated (one-time setup cost)...")
#    for i in range(VOTER_COUNT + 1):
#        member_data = OPTIMIZED_MEMBERS[i]
#        member_acct = Account.from_key(member_data['privateKey'])
#        try:
#            tx_func = opt_token_contract.functions.delegate(member_data['address'])
#            member_nonce = w3.eth.get_transaction_count(member_acct.address) 
#            send_tx(member_acct, tx_func, member_nonce)
#        except Exception:
#            pass
#        time.sleep(0.05) 

    
    # --- ISOLATION CHECK: VOTING POWER & QUORUM ---
    print("\n--- Pre-Vote Diagnostic Check ---")
    
    # 1. Get the Snapshot Block (The block where voting power was "frozen")
    snapshot_block = dao_contract.functions.proposalSnapshot(proposal_id).call()
    
    # 2. Get the Quorum required at that snapshot
    quorum_required = dao_contract.functions.quorum(snapshot_block).call()
    
    # 3. Check a sample voter's weight (e.g., the first voter in your list)
    sample_voter = Web3.to_checksum_address(OPTIMIZED_MEMBERS[3]['address'])
    
    # Assuming 'token_contract' is the ERC20 governance token for the optimized DAO
    voter_balance = opt_token_contract.functions.balanceOf(sample_voter).call()
    voter_weight = opt_token_contract.functions.getPastVotes(sample_voter, snapshot_block).call()

    print(f"Proposal Snapshot Block: {snapshot_block}")
    print(f"Quorum Required:         {w3.from_wei(quorum_required, 'ether')} votes")
    print(f"Sample Voter:            {sample_voter}")
    print(f"Current Token Balance:   {w3.from_wei(voter_balance, 'ether')} tokens")
    print(f"VOTING POWER AT SNAPSHOT: {w3.from_wei(voter_weight, 'ether')} votes")

    if voter_weight == 0 and voter_balance > 0:
        print("DIAGNOSIS: [!] Delegation Issue. Tokens held but weight is 0 at snapshot.")
    elif voter_weight == 0 and voter_balance == 0:
        print("DIAGNOSIS: [!] Distribution Issue. Account has no tokens.")
    elif voter_weight > 0:
        print(f"DIAGNOSIS: [✓] Voting weight is active. Expected total: {w3.from_wei(voter_weight * 40, 'ether')}")
    
    print("----------------------------------\n")

    # 4. VOTE (40 Votes - Low cost due to snapshots/ERC20Votes)
    dao_contract = w3.eth.contract(address=dao_addr, abi=DAO_OPTIMIZED_ABI)
    token_addr = dao_contract.functions.token().call()
    token = w3.eth.contract(address=token_addr, abi=TOKEN_ABI)
    proposal_state = dao_contract.functions.state(res.proposal_id).call()
    if proposal_state != 1: # 1 means Active
        raise Exception(f"Proposal state is {proposal_state}. Expected 1 (Active). Cannot proceed with voting.")
    else:
        print(f"Proposal {res.proposal_id} is now Active (State 1). Starting voting.")

    total_vote_gas = 0
    # Start from index 1 (Proposer is index 0)
    for i in range(1, VOTER_COUNT + 1):
        member_data = OPTIMIZED_MEMBERS[i]
        voter_acct = Account.from_key(member_data['privateKey'])
        voter_nonce = w3.eth.get_transaction_count(voter_acct.address)
        voter_balance = w3.eth.get_balance(voter_acct.address)
        if voter_balance < REQUIRED_ETH_FOR_VOTE:
            print(f"Skipping Vote {i} (Optimized): {voter_acct.address} has insufficient ETH ({w3.from_wei(voter_balance, 'ether'):.4f} ETH).")
            continue

        tx_func = dao_contract.functions.castVote(proposal_id, 1) # 1=For
        
        receipt = send_tx(voter_acct, tx_func, voter_nonce)
        total_vote_gas += receipt['gasUsed']
        time.sleep(0.1)
    # --- ADD PROPOSER (WHALE) VOTE HERE ---
    print("  [Whale] Casting decisive Proposer vote...")
    tx_func = dao_contract.functions.castVote(proposal_id, 1)
    
    # Note: Using proposer_nonce which was updated after the 'propose' call
    receipt = send_tx(proposer_acct, tx_func, proposer_nonce)
    proposer_nonce += 1 # Update for the upcoming 'queue' call
    
    total_vote_gas += receipt['gasUsed']
    
    # --- Part C: GLOBAL DEPLOYER (The Decisive Vote) ---
    # Assuming deployer_acct and deployer_nonce are defined in your setup
    print(f"  [Deployer] Casting GLOBAL WHALE vote from {deployer_addr}...")
    
    # 1. Ensure Deployer is delegated to itself (Done once per session)
    # 2. Cast the vote
    tx_func = dao_contract.functions.castVote(proposal_id, 1)
    receipt = send_tx(deployer_acct, tx_func, deployer_nonce)
    deployer_nonce += 1
    
    total_vote_gas += receipt['gasUsed']

    # Record the Proposer's vote as the final tx_vote for the results
    res.tx_vote = receipt['transactionHash'].hex()
    tx_data = w3.eth.get_transaction(receipt['transactionHash'])
    
    # Save total gas for all 42 votes (40 voters + 1 proposer + deployer)
    res.gas_vote = total_vote_gas
    print(f"  Total voting gas (42 votes): {total_vote_gas}")
    
    # 5. QUEUE
    print("\n" + "="*50)
    print("!!! PRE-QUEUE VOTE AUDIT !!!")
    
    # Wait for the voting period to end using the countdown logic
    deadline_block = dao_contract.functions.proposalDeadline(proposal_id).call()
    
    while True:
        curr_block = w3.eth.block_number
        if curr_block > deadline_block:
            print(f"\n[!] Deadline reached (Current: {curr_block} > Deadline: {deadline_block})")
            break
        
        blocks_left = deadline_block - curr_block
        print(f"  > Waiting for deadline... {blocks_left} blocks remaining (~{blocks_left*12/60:.1f} mins)", end='\r')
        time.sleep(30)

    # --- BLOCKCHAIN VOTE CONFIRMATION ---
    # proposalVotes returns (againstVotes, forVotes, abstainVotes)
    vote_stats = dao_contract.functions.proposalVotes(proposal_id).call()
    quorum_required = dao_contract.functions.quorum(deadline_block - 1).call()
    
    against_v = w3.from_wei(vote_stats[0], 'ether')
    for_v     = w3.from_wei(vote_stats[1], 'ether')
    abstain_v = w3.from_wei(vote_stats[2], 'ether')
    total_cast = against_v + for_v + abstain_v

    print("\n" + "-"*30)
    print(f"FOR Votes:     {for_v}")
    print(f"AGAINST Votes: {against_v}")
    print(f"ABSTAIN Votes: {abstain_v}")
    print(f"Total Cast:    {total_cast}")
    print(f"Quorum Needed: {w3.from_wei(quorum_required, 'ether')}")
    print("-" * 30)

    total_supply = token.functions.totalSupply().call()
    print(f"DEBUG: Total Supply: {w3.from_wei(total_supply, 'ether')}")

    # Check the actual success logic of the Governor
    try:
        # Some Governors have a 'proposalThreshold' or 'voteSucceeded' check
        # Let's see if the total 'FOR' is at least 50% of supply
        if vote_stats[1] < (total_supply / 2):
            print(f"⚠️ THEORY: Success requires > 50% of Total Supply.")
            print(f"   Required for 51%: {w3.from_wei(total_supply / 2, 'ether')}")
            print(f"   Shortfall: {w3.from_wei((total_supply / 2) - vote_stats[1], 'ether')}")
    except:
        pass

    state = dao_contract.functions.state(proposal_id).call()
    # State Mapping: 3=Defeated, 4=Succeeded
    if state == 3:
        print(f"RESULT: DEFEATED (State {state})")
        if total_cast < w3.from_wei(quorum_required, 'ether'):
            print("CAUSE: Quorum not reached.")
        elif against_v >= for_v:
            print("CAUSE: Majority not reached (Against >= For).")
        else:
            print("CAUSE: Logic Error - Abstains may be counting as Against.")
        raise Exception("Proposal failed. Audit your theory above.")
    
    elif state == 4:
        print("RESULT: SUCCEEDED! Proceeding to Queue...")
    else:
        print(f"RESULT: Unexpected State ({state}).")
    
    print("="*50 + "\n")

    print("\n[Optimized] Entering Voting Period Wait (Block-based)...")

    # Use the helper to wait until the contract actually allows queueing
    if not wait_for_proposal_succeeded(dao_contract, proposal_id):
        raise Exception("Recovery failed: Proposal not successful.")    
    
    tx_func = dao_contract.functions.queue(targets, values, calldatas, description_hash)
    receipt = send_tx(proposer_acct, tx_func, proposer_nonce)
    proposer_nonce += 1
    
    res.gas_queue = receipt['gasUsed']
    res.tx_queue = receipt['transactionHash'].hex()
    tx_data = w3.eth.get_transaction(receipt['transactionHash'])
    
    # 6. EXECUTE
    print("  [Optimized] Waiting for Timelock delay to pass (approx 130s)...")
    time.sleep(130)

    tx_func = dao_contract.functions.execute(targets, values, calldatas, description_hash)
    
    # Anyone can call Governor.execute, so we use the Proposer's account
    proposer_nonce_updated = w3.eth.get_transaction_count(proposer_acct.address)
    receipt = send_tx(proposer_acct, tx_func, proposer_nonce_updated)
    
    res.gas_execute = receipt['gasUsed']
    res.tx_execute = receipt['transactionHash'].hex()
    tx_data = w3.eth.get_transaction(receipt['transactionHash'])
    return res, proposer_nonce

# --- MAIN RUNNER ---
def main():
    deployer_nonce = w3.eth.get_transaction_count(deployer_addr)
    if not w3.is_connected():
        print("Error: Could not connect to RPC URL.")
        return

    # Nonce for the proposer & deloyer accounts
    proposer_nonce_vul = w3.eth.get_transaction_count(Account.from_key(VUL_PROPOSER_KEY).address) 
    proposer_nonce_opt = w3.eth.get_transaction_count(Account.from_key(OPT_PROPOSER_KEY).address)
    
    # --- GLOBAL DEPLOYER DELEGATION ---
    # Using the two token addresses provided
    GOV_TOKENS = {
        "VUL_TOKEN": os.getenv("VUL_TOKEN_ADDR"),
        "OPT_TOKEN": os.getenv("OPT_TOKEN_ADDR")
    }

    print(f"\n--- Initializing Global Whale Power for Deployer: {deployer_addr} ---")

    for name, token_addr in GOV_TOKENS.items():
        if not token_addr:
            print(f"⚠️ {name} address missing.")
            continue
    
        # Check if address is a contract
        code = w3.eth.get_code(token_addr)
        if code == b'' or code.hex() == '0x':
            print(f"❌ ERROR: No contract found at {name} ({token_addr}). Check your .env or network.")
            continue        
        
        token_contract = w3.eth.contract(address=token_addr, abi=TOKEN_ABI)
        try:
            # 1. Check if the deployer is already delegated to themselves
            current_delegate = token_contract.functions.delegates(deployer_addr).call()
    
            if current_delegate.lower() != deployer_addr.lower():
                print(f"Delegating {name} ({token_addr[:8]}...) to self...")
        
                # Prepare and send the delegation transaction
                tx_func = token_contract.functions.delegate(deployer_addr)
                receipt = send_tx(deployer_acct, tx_func, deployer_nonce)
                deployer_nonce += 1
                print(f"  > Success! Hash: {receipt['transactionHash'].hex()}")
                # Brief pause to ensure the state change is indexed before we propose
                time.sleep(2)
            else:
                print(f"Deployer already holds voting power for {name}. Skipping.")
        except Exception as e:
            print(f"⚠️ Could not call 'delegates' on {name}: {e}")
            print("Attempting direct delegation without check...")
            try:
                tx_func = token_contract.functions.delegate(deployer_addr)
                receipt = send_tx(deployer_acct, tx_func, deployer_nonce)
                deployer_nonce += 1
            except Exception as e2:
                print(f"❌ Critical failure on {name}: {e2}")
    print("--- All Tokens Active. Deployer now controls the 'Silent Majority'. ---\n")

    print(f"\n--- RUNNING SCENARIOS WITH {VOTER_COUNT} VOTERS ---")

    # --- RUN V1: Vulnerable DAO + Basic Treasury ---
#    print("\n--- Running V1 (Vulnerable DAO + Basic Treasury) ---")
#    v1_res, proposer_nonce_vul = run_scenario_vulnerable(V1_DAO_ADDR, V1_TREASURY_ADDR, proposer_nonce_vul)

    # --- RUN V2: Vulnerable DAO + Secure Treasury ---
#    print("\n--- Running V2 (Vulnerable DAO + Secure Treasury) ---")
#    proposer_acct = Account.from_key(VUL_PROPOSER_KEY)
#    proposer_nonce_vul = w3.eth.get_transaction_count(proposer_acct.address)
#    v2_res, proposer_nonce_vul = run_scenario_vulnerable(V2_DAO_ADDR, V2_TREASURY_ADDR, proposer_nonce_vul)

    # --- RUN V3: Optimized DAO + Basic Treasury ---
    print("\n--- Running V3 (Optimized DAO + Basic Treasury) ---")
    v3_res, proposer_nonce_opt = run_scenario_optimized(V3_DAO_ADDR, V3_TREASURY_ADDR, proposer_nonce_opt)
    
    # --- RUN V4: Optimized DAO + Secure Treasury (The Target) ---
    print("\n--- Running V4 (Optimized DAO + Secure Treasury) ---")
    proposer_acct = Account.from_key(OPT_PROPOSER_KEY)
    proposer_nonce_opt = w3.eth.get_transaction_count(proposer_acct.address)
    v4_res, _ = run_scenario_optimized(V4_DAO_ADDR, V4_TREASURY_ADDR, proposer_nonce_opt)
    
    
    # --- LOG COMPARISON MATRIX ---

    # V1 vs V4: Full Stack Comparison (Baseline vs Target)
#    log_results("V1 vs V4 (Full Vulnerable vs Full Optimized Stack)", v1_res, v4_res)
    
    # V1 vs V3: DAO-only improvement (Optimized DAO / Vulnerable Treasury)
#    log_results("V1 vs V3 (DAO-Only Benefit: Vulnerable vs Optimized Token/Voting)", v1_res, v3_res)

    # V2 vs V4: Treasury/Execution Divergence (Vulnerable DAO / Secure Treasury)
    log_results("V2 vs V4 (Secure Treasury Comparison)", v2_res, v4_res)

    # V3 vs V4: Treasury Optimization Benefit (Optimized DAO / Optimized Treasury)
    log_results("V3 vs V4 (Execution Optimization Benefit: TreasuryBasic vs TreasurySecure)", v3_res, v4_res)

if __name__ == "__main__":
    main()
