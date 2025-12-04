#!/usr/bin/env python3
"""
DAO Gas Comparison Test Harness
- Runs propose -> castVote (multi-member) -> queue -> execute
- For both Baseline (Vulnerable) and Optimized DAOs
- Uses members from dao_members.txt for voting
- Saves receipts, hashes, event logs and gas usage to reports/
"""

import os
import json
import time
from datetime import datetime
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

load_dotenv()

# -------------------------
# Config from environment
# -------------------------
RPC_URL = os.getenv("RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")            # main proposer / admin (must be funded)
PUBLIC_ADDRESS = os.getenv("PUBLIC_ADDRESS")      # hex address of PRIVATE_KEY
BASE_DAO = os.getenv("BASE_DAO")
BASE_TREASURY = os.getenv("BASE_TREASURY")
OPT_DAO = os.getenv("OPT_DAO")
OPT_TREASURY = os.getenv("OPT_TREASURY")

# Paths to ABIs (update if needed)
ABI_DAO_OPT = "out/DAOOptimized.sol/DAOOptimized.json"
ABI_DAO_BASE = "out/VulnerableDAO.sol/VulnerableDAO.json"
ABI_TREASURY_OPT = "out/TreasurySecure.sol/TreasurySecure.json"
ABI_TREASURY_BASE = "out/TreasuryBasic.sol/TreasuryBasic.json"

MEMBERS_FILE = "dao_members.txt"   # one private key per line
REPORT_DIR = "reports"
os.makedirs(REPORT_DIR, exist_ok=True)

# Safety checks
for varname in ["RPC_URL", "PRIVATE_KEY", "PUBLIC_ADDRESS", "BASE_DAO", "BASE_TREASURY", "OPT_DAO", "OPT_TREASURY"]:
    if not globals().get(varname):
        raise SystemExit(f"Missing env var: {varname}. Fill .env and retry.")

# -------------------------
# Helpers
# -------------------------
def timestamp():
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def save_json(obj, filename):
    with open(filename, "w") as f:
        json.dump(obj, f, indent=2)
    print(f"Saved: {filename}")

def tx_send_and_wait(web3, tx_dict, priv_key, verbose=True):
    signed = web3.eth.account.sign_transaction(tx_dict, priv_key)
    tx_hash = web3.eth.send_raw_transaction(signed.rawTransaction)
    txh_hex = web3.to_hex(tx_hash)
    if verbose: print(f"  Sent tx: {txh_hex}")
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=600)
    if verbose: print(f"  Included block: {receipt.blockNumber}, gasUsed: {receipt.gasUsed}")
    return txh_hex, receipt

def read_members(path):
    if not os.path.exists(path):
        raise SystemExit(f"Members file not found: {path}")
    with open(path, "r") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    # validate smallest sanity
    if len(lines) == 0:
        raise SystemExit("No member keys found in dao_members.txt")
    return lines

# -------------------------
# Main test logic
# -------------------------
def run_proposal_flow(web3, dao_contract, treasury_contract, label, members_privkeys, main_privkey):
    """
    Runs propose -> many votes (members) -> queue -> execute
    Uses main_privkey for propose/queue/execute.
    members_privkeys: list of private keys used to call castVote
    Returns a dict with detailed receipts and gas usage.
    """
    results = {"label": label, "steps": {}}
    sender_addr = web3.to_checksum_address(PUBLIC_ADDRESS)
    chain_id = web3.eth.chain_id

    # Build calldata for treasury: call a simple function. We'll attempt to call a
    # conventional function: for ERC20-like token it may be transfer; for simple
    # treasury we can assume a function `executePayment(address,uint256)` exists (Vulnerable uses executePayment).
    # We'll pick executePayment(recipient, amount) if available else fallback to generic low-value call (0 ETH).
    # Try to compute calldata robustly.
    # We'll attempt to use treasury.executePayment(recipient, amount) if function exists in ABI.
    transfer_data = None
    try:
        # use 1 wei (or small) to avoid large withdrawals
        if "executePayment" in treasury_contract.functions:
            transfer_data = treasury_contract.encodeABI(fn_name="executePayment", args=[sender_addr, 1])
        elif "transfer" in treasury_contract.functions:
            transfer_data = treasury_contract.encodeABI(fn_name="transfer", args=[sender_addr, 1])
        else:
            # fallback: empty call (no-op) to target address - may still cost gas in execute
            transfer_data = "0x"
    except Exception:
        # fallback safe
        transfer_data = "0x"

    # compute descriptionHash for governor functions (standard OZ Governor hash uses bytes32)
    description = "Gas test proposal"
    description_hash = web3.solidity_keccak(["string"], [description])

    # ---------------- PROPOSE ----------------
    print(f"\n[{label}] PROPOSE")
    nonce = web3.eth.get_transaction_count(sender_addr)
    tx_propose = dao_contract.functions.propose(
        [treasury_contract.address],
        [0],
        [transfer_data],
        description
    ).build_transaction({
        "chainId": chain_id,
        "from": sender_addr,
        "nonce": nonce,
        "gas": 5_000_000,
        "gasPrice": web3.eth.gas_price
    })
    txh, receipt = tx_send_and_wait(web3, tx_propose, main_privkey)
    results["steps"]["propose"] = {
        "tx_hash": txh, "receipt": dict(receipt), "gas_used": receipt.gasUsed
    }

    # Attempt to compute proposalId using hashProposal if available
    try:
        prop_id = dao_contract.functions.hashProposal(
            [treasury_contract.address],
            [0],
            [transfer_data],
            description_hash
        ).call()
        print(f"  proposalId: {prop_id}")
    except Exception as e:
        # fallback: try reading latest events to get created proposal id
        print("  Could not call hashProposal():", str(e))
        # scan event logs: 'ProposalCreated' typical event
        prop_id = None
        receipt_logs = receipt.logs
        # naive parse: try to find ProposalCreated topic if ABI present
        try:
            for log in receipt.logs:
                try:
                    decoded = dao_contract.events.ProposalCreated().processLog(log)
                    prop_id = decoded["args"]["id"] if "id" in decoded["args"] else decoded["args"].get("proposalId")
                    print("  Found ProposalCreated in logs:", prop_id)
                    break
                except Exception:
                    continue
        except Exception:
            prop_id = None

    if prop_id is None:
        raise SystemExit("Failed to determine proposal id. Cannot continue flow.")

    # ---------------- VOTING (multi-member) ----------------
    print(f"\n[{label}] CAST VOTES using {len(members_privkeys)} members (will stop early if any error)")

    votes_info = []
    i = 0
    for member_pk in members_privkeys:
        i += 1
        acct = Account.from_key(member_pk)
        member_addr = acct.address
        try:
            # build tx for castVote(proposalId, support)
            nonce_m = web3.eth.get_transaction_count(member_addr)
            # support = 1 (for)
            tx_vote = dao_contract.functions.castVote(prop_id, 1).build_transaction({
                "chainId": chain_id,
                "from": member_addr,
                "nonce": nonce_m,
                "gas": 500_000,
                "gasPrice": web3.eth.gas_price
            })
            txh_m, receipt_m = tx_send_and_wait(web3, tx_vote, member_pk, verbose=False)
            print(f"  vote #{i} by {member_addr} -> gas {receipt_m.gasUsed}")
            votes_info.append({"member": member_addr, "tx_hash": txh_m, "gas_used": receipt_m.gasUsed, "status": receipt_m.status})
        except Exception as e:
            # log and continue
            print(f"  vote #{i} FAILED for {member_addr}: {e}")
            votes_info.append({"member": member_addr, "error": str(e)})
        # slight delay to avoid nonce/rate issues
        time.sleep(0.15)

    results["steps"]["votes"] = votes_info

    # ---------------- QUEUE ----------------
    print(f"\n[{label}] QUEUE")
    nonce = web3.eth.get_transaction_count(sender_addr)
    tx_queue = dao_contract.functions.queue(
        [treasury_contract.address],
        [0],
        [transfer_data],
        description_hash
    ).build_transaction({
        "chainId": chain_id,
        "from": sender_addr,
        "nonce": nonce,
        "gas": 800_000,
        "gasPrice": web3.eth.gas_price
    })
    txh_q, receipt_q = tx_send_and_wait(web3, tx_queue, main_privkey)
    results["steps"]["queue"] = {"tx_hash": txh_q, "receipt": dict(receipt_q), "gas_used": receipt_q.gasUsed}

    # ---------------- EXECUTE ----------------
    print(f"\n[{label}] EXECUTE")
    nonce = web3.eth.get_transaction_count(sender_addr)
    tx_exec = dao_contract.functions.execute(
        [treasury_contract.address],
        [0],
        [transfer_data],
        description_hash
    ).build_transaction({
        "chainId": chain_id,
        "from": sender_addr,
        "nonce": nonce,
        "gas": 5_000_000,
        "gasPrice": web3.eth.gas_price
    })
    txh_e, receipt_e = tx_send_and_wait(web3, tx_exec, main_privkey)
    results["steps"]["execute"] = {"tx_hash": txh_e, "receipt": dict(receipt_e), "gas_used": receipt_e.gasUsed}

    # Save run-level report
    fname = f"{REPORT_DIR}/{label}_run_{timestamp()}.json"
    save_report_obj = {"meta": {"label": label, "timestamp": timestamp(), "chainId": chain_id}, "results": results}
    save_json(save_report_obj, fname)

    return results

# -------------------------
# Top-level runner
# -------------------------
def main():
    web3 = Web3(Web3.HTTPProvider(RPC_URL))
    assert web3.isConnected(), "RPC not connected"

    print("Loading ABIs...")
    dao_abi_opt = load_json(ABI_DAO_OPT)["abi"]
    dao_abi_base = load_json(ABI_DAO_BASE)["abi"]
    treasury_abi_opt = load_json(ABI_TREASURY_OPT)["abi"]
    treasury_abi_base = load_json(ABI_TREASURY_BASE)["abi"]

    # instantiate contracts
    base_dao = web3.eth.contract(address=Web3.to_checksum_address(BASE_DAO), abi=dao_abi_base)
    base_treasury = web3.eth.contract(address=Web3.to_checksum_address(BASE_TREASURY), abi=treasury_abi_base)

    opt_dao = web3.eth.contract(address=Web3.to_checksum_address(OPT_DAO), abi=dao_abi_opt)
    opt_treasury = web3.eth.contract(address=Web3.to_checksum_address(OPT_TREASURY), abi=treasury_abi_opt)

    # load members
    members_privkeys = read_members(MEMBERS_FILE)
    members_count = len(members_privkeys)
    print(f"Loaded {members_count} member keys")

    # For time/cost reasons, you can reduce the number of voters used in tests.
    # We'll try to use up to 120 (all loaded), but you may set a smaller test sample:
    MAX_VOTERS = 120
    members_for_test = members_privkeys[:MAX_VOTERS]

    # Run baseline
    print("\n====== RUNNING BASELINE (VULNERABLE DAO) ======")
    baseline_results = run_proposal_flow(web3, base_dao, base_treasury, "baseline", members_for_test, PRIVATE_KEY)

    # small pause
    time.sleep(3)

    # Run optimized
    print("\n====== RUNNING OPTIMIZED DAO ======")
    optimized_results = run_proposal_flow(web3, opt_dao, opt_treasury, "optimized", members_for_test, PRIVATE_KEY)

    # -------------------------
    # Compare gas usage
    # -------------------------
    summary = {"baseline": baseline_results, "optimized": optimized_results, "comparison": {}, "meta": {"run_at": timestamp()}}
    # Summarize: for each step (propose, votes aggregated, queue, execute) compute totals/averages
    def summarize_steps(res):
        s = {}
        steps = res["steps"]
        s["propose_gas"] = steps["propose"]["gas_used"]
        s["queue_gas"] = steps["queue"]["gas_used"]
        s["execute_gas"] = steps["execute"]["gas_used"]
        # votes — compute total gas used and average for successful votes
        votes = [v for v in steps["votes"] if v.get("gas_used")]
        total_votes_gas = sum(v["gas_used"] for v in votes) if votes else 0
        avg_vote_gas = (total_votes_gas / len(votes)) if votes else 0
        s["votes_total_gas"] = total_votes_gas
        s["votes_count"] = len(votes)
        s["votes_avg_gas"] = avg_vote_gas
        return s

    base_summary = summarize_steps(baseline_results)
    opt_summary = summarize_steps(optimized_results)

    # compute diffs
    for k in base_summary:
        b = base_summary[k]
        o = opt_summary.get(k, 0)
        diff = b - o
        pct = (diff / b * 100) if b else 0
        summary["comparison"][k] = {"baseline": b, "optimized": o, "difference": diff, "pct_saved": pct}

    # save summary and human-friendly md
    save_json(summary, f"{REPORT_DIR}/gas_summary_{timestamp()}.json")

    # produce human-friendly markdown summary
    md_lines = [
        f"# Gas Comparison Summary ({timestamp()})",
        "",
        "## Summary (numbers are gas units)",
        "",
    ]
    for k, v in summary["comparison"].items():
        md_lines.append(f"### {k}")
        md_lines.append(f"- Baseline: {v['baseline']}")
        md_lines.append(f"- Optimized: {v['optimized']}")
        md_lines.append(f"- Saved: {v['difference']} gas ({v['pct_saved']:.2f}%)")
        md_lines.append("")

    md_path = f"{REPORT_DIR}/gas_report_{timestamp()}.md"
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))
    print(f"Markdown summary saved: {md_path}")

    print("\nALL DONE. Reports are in the reports/ directory.")

if __name__ == "__main__":
    main()
