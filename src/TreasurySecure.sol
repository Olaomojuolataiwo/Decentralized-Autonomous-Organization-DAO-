// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

contract TreasurySecure is Ownable, ReentrancyGuard {
    /// -----------------------------------------------------------------------
    /// STORAGE
    /// -----------------------------------------------------------------------

    address public immutable governance; // ✔ cheaper SLOAD
    mapping(address => bool) public allowedTargets;

    /// -----------------------------------------------------------------------
    /// EVENTS
    /// -----------------------------------------------------------------------
    event TargetAllowed(address indexed target, bool allowed);
    event Executed(address indexed target, uint256 value, bytes data, bytes result);

    /// -----------------------------------------------------------------------
    /// CONSTRUCTOR
    /// -----------------------------------------------------------------------
    constructor(address _governance) Ownable(_governance) {
        governance = _governance;
    }

    /// -----------------------------------------------------------------------
    /// RECEIVE
    /// -----------------------------------------------------------------------
    receive() external payable {}

    /// -----------------------------------------------------------------------
    /// ADMIN (only governor can add/remove allowed targets)
    /// -----------------------------------------------------------------------
    function setAllowedTarget(address target, bool allowed) external onlyOwner {
        allowedTargets[target] = allowed;
        emit TargetAllowed(target, allowed);
    }

    /// -----------------------------------------------------------------------
    /// GOVERNANCE EXECUTION ENTRYPOINT
    /// -----------------------------------------------------------------------
    function execute(address target, uint256 value, bytes calldata data) external nonReentrant returns (bytes memory) {
        require(msg.sender == governance, "Not governance");
        require(allowedTargets[target], "Target not allowed");
        require(address(this).balance >= value, "Insufficient balance");

        (bool ok, bytes memory result) = target.call{value: value}(data);
        require(ok, "Call failed");

        emit Executed(target, value, data, result);
        return result;
    }
}
