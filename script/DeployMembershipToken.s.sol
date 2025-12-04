// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "forge-std/Script.sol";
import "../src/MembershipTokenMintable.sol";

contract DeployMembershipToken is Script {
    function run() external {
        vm.startBroadcast();

        console.log("Deploying MembershipToken...");
        MembershipToken token = new MembershipToken();
        console.log("MembershipToken deployed at:", address(token));

        vm.stopBroadcast();
    }
}
