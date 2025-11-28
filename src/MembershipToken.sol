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
    // Required override #1
    // _update() is overridden by ERC20Votes and ERC20
    // ---------------------------------------------------------
    function _update(address from, address to, uint256 amount)
        internal
        virtual
        override(ERC20, ERC20Votes)
    {
        super._update(from, to, amount);
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
