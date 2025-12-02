// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/MembershipToken.sol";

contract DeployMembershipToken is Script {
    // Address to initially own the token (DAO deployer / governance)
    address public tokenOwner;

    // Deployed token instance
    MembershipToken public membershipToken;

    constructor() {
        // Replace with your preferred deployer account
        tokenOwner = vm.envAddress("DEPLOYER_ADDRESS");
    }

    function run() external {
        // Start broadcasting transactions to Sepolia
        vm.startBroadcast(tokenOwner);

        // Deploy MembershipToken
        membershipToken = new MembershipToken();

        // Transfer ownership to tokenOwner if needed
        membershipToken.transferOwnership(tokenOwner);

        vm.stopBroadcast();

        // Log the deployed address
        console.log("MembershipToken deployed at:", address(membershipToken));
    }
}
