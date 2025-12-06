// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "forge-std/Script.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";

contract DeployVulTimelock is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);
        // FIX 1: Define proposers and executors as address[] memory arrays
        address[] memory proposers = new address[](1);
        proposers[0] = vm.envAddress("DEPLOYER");

        address[] memory executors = new address[](1);
        executors[0] = vm.envAddress("DEPLOYER");

        vm.startBroadcast(deployerPrivateKey);

        console.log("Deploying Vulnerable TimelockController...");

        uint256 minDelay = 60; // 1 minute

        // ---------------------------------------------------------
        // FIXED: Declare arrays BEFORE they are used
        // ---------------------------------------------------------
        address;
        address;

        // ---------------------------------------------------------
        // Deploy the timelock controller
        // ---------------------------------------------------------
        TimelockController tl = new TimelockController(minDelay, proposers, executors, deployer);

        console.log("Vulnerable Timelock deployed at:", address(tl));

        vm.stopBroadcast();
    }
}
