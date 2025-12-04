// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Permit} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import {ERC20Votes} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Nonces} from "@openzeppelin/contracts/utils/Nonces.sol";

contract MembershipToken is ERC20, ERC20Permit, ERC20Votes, Ownable {
    constructor()
        ERC20("Fulcrum Membership", "FMBR")
        ERC20Permit("Fulcrum Membership")
        Ownable(msg.sender)
    {}

    // ---------------------------------------------------------
    // Owner-only mint functions for initial distribution
    // ---------------------------------------------------------
    function mint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
    }

    /// @notice Mint to many addresses in a single tx (gas saving vs many single calls)
    function mintBatch(address[] calldata tos, uint256[] calldata amounts) external onlyOwner {
        require(tos.length == amounts.length, "LENGTH");
        for (uint256 i = 0; i < tos.length; i++) {
            _mint(tos[i], amounts[i]);
        }
    }

    // ---------------------------------------------------------
    // Required override #1 — from ERC20 + ERC20Votes
    // Handles mint, burn, and transfer voting logic
    // ---------------------------------------------------------
    function _update(address from, address to, uint256 value)
        internal
        override(ERC20, ERC20Votes)
    {
        super._update(from, to, value);
    }   
    // ---------------------------------------------------------
    // Required override #2
    // nonces() comes from both ERC20Permit and Nonces
    // ---------------------------------------------------------
    function nonces(address owner)
        public
        view
        override(ERC20Permit, Nonces)
        returns (uint256)
    {
        return super.nonces(owner);
    }

}
