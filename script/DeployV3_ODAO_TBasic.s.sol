// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "forge-std/console.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

// Ensure paths are correct for your project
import "../src/DAOOptimized.sol";
import "../src/TreasuryBasic.sol"; // V3 uses the Basic Treasury
import "../src/MembershipToken.sol"; // Optimized stack must use the OZ token (ERC20Votes)

contract DeployV3_ODAO_TBasic is Script {
    // Configuration Constants (Must match your testing parameters)
    uint256 public constant MIN_DELAY = 120; // 2 minutes (Timelock delay)
    uint256 public constant VOTING_DELAY = 1;
    uint256 public constant VOTING_PERIOD = 8;
    uint256 public constant QUORUM_NUMERATOR = 4; // 4% Quorum

    function run() external {
        address deployer = vm.envAddress("DEPLOYER");
        // Ensure this points to your deployed MembershipToken (ERC20Votes) address
        address tokenAddr = vm.envAddress("TOKEN_ADDRESS_OZ");
        require(tokenAddr != address(0), "TOKEN_ADDRESS_OZ required");

        vm.startBroadcast();

        // --- 1. DEPLOY TIMELOCK CONTROLLER ---
        // Setup: No initial proposers, anyone can execute (address(0)), Deployer is temporary admin
        address[] memory proposers = new address[](0);
        address[] memory executors = new address[](1);
        executors[0] = address(0x0000000000000000000000000000000000000000);

        TimelockController timelock = new TimelockController(MIN_DELAY, proposers, executors, deployer);
        address timelockAddr = address(timelock);
        console.log("V3_TIMELOCK_ADDR:", timelockAddr);

        // --- 2. DEPLOY DAOOPTIMIZED (Governor) ---
        // Binds the DAO to the TimelockController
        MembershipToken token = MembershipToken(tokenAddr);

        DAOOptimized dao = new DAOOptimized(
            "DAOOptimized-V3",
            token,
            timelock,
            VOTING_DELAY,
            VOTING_PERIOD,
            0, // Proposal Threshold
            QUORUM_NUMERATOR
        );
        address daoAddr = address(dao);
        console.log("V3_DAO_ADDR (DAOOptimized):", daoAddr);

        // --- 3. DEPLOY TREASURYBASIC (BOUND TO TIMELOCK) ---
        // CRITICAL FIX: Treasury is bound to the entity that executes the transfer: the Timelock.
        TreasuryBasic treasury = new TreasuryBasic(timelockAddr);
        address treasuryAddr = address(treasury);
        console.log("V3_TREASURY_ADDR (TreasuryBasic):", treasuryAddr);

        // --- 4. POST-DEPLOYMENT SETUP ---
        // a) Grant the DAO the PROPOSER role on the Timelock
        bytes32 PROPOSER_ROLE = timelock.PROPOSER_ROLE();
        timelock.grantRole(PROPOSER_ROLE, daoAddr);

        // b) Revoke the deployer's temporary admin role (Security best practice)
        bytes32 DEFAULT_ADMIN_ROLE = timelock.DEFAULT_ADMIN_ROLE();
        timelock.revokeRole(DEFAULT_ADMIN_ROLE, deployer);

        vm.stopBroadcast();

        // The three addresses (V3_DAO_ADDR, V3_TIMELOCK_ADDR, V3_TREASURY_ADDR) are now unique and correctly bound.
    }
}
