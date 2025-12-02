// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "forge-std/Script.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";

contract DeployTimelock is Script {
    // --- CONFIG ---
    uint256 public constant MIN_DELAY = 120;

    function run() external {
        vm.startBroadcast();

        // 1. Declare and initialize dynamic memory arrays for proposers and executors
        // The TimelockController constructor expects arrays of addresses.
        address[] memory proposers = new address[](1);
        address[] memory executors = new address[](1);

        // 2. Assign the temporary controller (msg.sender)
        executors[0] = msg.sender;
        proposers[0] = msg.sender;

        // 3. Deploy the TimelockController
        TimelockController timelock = new TimelockController(
            MIN_DELAY,
            proposers,
            executors,
            msg.sender // Admin address (can be set to the DAO later)
        );

        console.log("TimelockController deployed at:", address(timelock));
        console.log("Min Delay:", MIN_DELAY);
        console.log("Temporary Proposer:", msg.sender);
        console.log("Temporary Executor:", msg.sender);
        console.log("Temporary Admin:", msg.sender);

        vm.stopBroadcast();
    }
}
