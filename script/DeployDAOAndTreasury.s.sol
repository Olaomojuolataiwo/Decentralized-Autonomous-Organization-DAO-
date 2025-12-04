// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "forge-std/Script.sol";
import "../src/DAOOptimized.sol";
import "../src/TreasurySecure.sol";
import "../src/MembershipToken.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";

contract DeployDAOAndTreasury is Script {
    function run() external {
        vm.startBroadcast();

        // --- TIMESTAMP FOR LOGGING ---
        console.log("Deploying DAO and Treasury...");

        // --- Existing deployed addresses ---
        address timelockAddr = 0xa71a17F8CC919800b2DD40A9E4472B746946C9C5;
        address tokenAddr = 0xF5b4ca1744438f403f0919fC1E51DcDBf43d9137;

        // --- Log addresses and check if contracts exist ---
        console.log("Timelock address:", timelockAddr);
        console.log("Is timelock a contract?", timelockAddr.code.length > 0);
        console.log("Token address:", tokenAddr);
        console.log("Is token a contract?", tokenAddr.code.length > 0);

        // --- Deploy TreasurySecure ---
        TreasurySecure treasury = new TreasurySecure(timelockAddr);
        console.log("TreasurySecure deployed at:", address(treasury));

        // --- Log treasury contract code length ---
        console.log("Is treasury a contract?", address(treasury).code.length > 0);

        // --- Cast deployed contracts properly ---
        TimelockController timelock = TimelockController(payable(timelockAddr));
        MembershipToken token = MembershipToken(tokenAddr);

        // --- Extra logging before DAO deployment ---
        console.log("TimelockController contract code length:", address(timelock).code.length);
        console.log("MembershipToken contract code length:", address(token).code.length);

        // --- Deploy DAOOptimized ---
        DAOOptimized dao = new DAOOptimized(
            "DAOOptimized",
            token,
            timelock,
            1, // votingDelay
            45818, // votingPeriod
            103_549_028_532_224, // proposalThreshold
            4 // quorum numerator %
        );

        console.log("DAOOptimized deployed at:", address(dao));
        console.log("DAO deployed successfully.");

        vm.stopBroadcast();
    }
}
