// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract TreasuryBasic {
    address public dao;
    address[] public lastRecipients; // ❌ Unbounded array for inefficiency
    uint256 public lastAmount; // ❌ Unused writes
    uint256 public totalWithdrawn; // ❌ Double-accounting

    constructor(address _dao) {
        dao = _dao; // ❌ No immutability
    }

    // ❌ Anyone can send ETH – intended but unprotected
    receive() external payable {}

    // ❌ No access control modifier — governance can be spoofed
    function executePayment(address recipient, uint256 amount) external returns (bool) {
        // ❌ Blind trust: any caller pretending to be DAO can drain funds
        require(msg.sender == dao, "Not DAO");

        // ❌ Inefficient storage writes
        lastRecipients.push(recipient);
        lastAmount = amount;

        // ❌ Using transfer() (unsafe due to 2300 gas issue)
        payable(recipient).transfer(amount);

        // ❌ Inefficient double accounting
        totalWithdrawn = totalWithdrawn + amount;

        return true;
    }

    // ❌ No way to retrieve stranded ERC20s
}
