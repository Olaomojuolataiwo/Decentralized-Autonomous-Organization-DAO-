// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "forge-std/console.sol";
import "../src/VulnerableMembershipToken.sol";

contract DeployVulnerableToken is Script {
    function run() external {
        // token parameters (set via env or change here)
        string memory name_ = "Vulnerable Membership";
        string memory symbol_ = "VMBR";
        uint256 totalMint = vm.envUint("VUL_TOTAL_MINT"); // e.g. 100_000_000 * 1e18
        if (totalMint == 0) totalMint = 100_000_000 * 1e18;

        vm.startBroadcast();

        VulnerableMembershipToken token = new VulnerableMembershipToken(name_, symbol_);
        console.log("Vulnerable token deployed at:", address(token));

        // Mint entire supply to deployer (owner)
        address owner = msg.sender;
        token.mint(owner, totalMint);
        console.log("Minted total supply to deployer:", owner);

        vm.stopBroadcast();
    }
}
