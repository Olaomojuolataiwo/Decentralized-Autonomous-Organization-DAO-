// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "forge-std/console.sol";

import "../src/DAOOptimized.sol";
import "../src/TreasurySecure.sol";
import "../src/MembershipToken.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";

contract DeployOptimizedStack is Script {
    function run() external {
        // --- read env ---
        address timelockAddr = vm.envAddress("EXISTING_TIMELOCK"); // must be set
        address tokenAddr = vm.envAddress("TOKEN_ADDRESS"); // must be set

        require(timelockAddr != address(0), "EXISTING_TIMELOCK not set");
        require(tokenAddr != address(0), "TOKEN_ADDRESS not set");

        console.log("Using existing timelock:", timelockAddr);
        console.log("Using token:", tokenAddr);

        // --- start broadcast (the PRIVATE_KEY passed to forge will be used) ---
        vm.startBroadcast();

        // sanity checks
        console.log("Is timelock a contract?", timelockAddr.code.length > 0);
        console.log("Is token a contract?", tokenAddr.code.length > 0);

        // Deploy TreasurySecure and set owner to timelock (TreasurySecure constructor Ownable(_governance))
        TreasurySecure treasury = new TreasurySecure(timelockAddr);
        console.log("TreasurySecure deployed at:", address(treasury));
        console.log("Treasury owner (should be timelock):", Ownable(address(treasury)).owner());

        // Cast types for DAO constructor
        TimelockController timelock = TimelockController(payable(timelockAddr));
        MembershipToken token = MembershipToken(tokenAddr);

        // Deploy DAOOptimized (tunable params)
        // These parameters are the same as used previously; adjust via env if needed in new script variant.
        DAOOptimized dao = new DAOOptimized(
            "DAOOptimized",
            token,
            timelock,
            1, // votingDelay
            45818, // votingPeriod
            103_549_028_532_224, // proposalThreshold
            4 // quorumNumerator (percentage)
        );

        console.log("DAOOptimized deployed at:", address(dao));

        vm.stopBroadcast();
    }
}
