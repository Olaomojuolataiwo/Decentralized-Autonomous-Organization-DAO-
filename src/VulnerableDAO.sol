// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20Simple {
    function balanceOf(address) external view returns (uint256);
}

/// @notice Ultra-vulnerable DAO: members list + naive O(n) vote counting.
/// - No snapshots
/// - No delegation
/// - Votes use current token balances (vulnerable)
/// - Immediate execution if proposal passes
contract VulnerableDAO {
    struct Proposal {
        address proposer;
        string description;
        address target;
        uint256 value;
        bytes data;
        uint256 yes;
        uint256 no;
        uint256 createdAt;
        bool executed;
        mapping(address => bool) hasVoted; // expensive mapping inside struct
    }

    IERC20Simple public token;
    address[] public members;
    mapping(uint256 => Proposal) public proposals;
    uint256 public proposalCount;

    event ProposalCreated(uint256 id, address proposer);
    event VoteCast(uint256 id, address voter, bool support, uint256 weight);
    event Executed(uint256 id, address target, uint256 value);

    constructor(address _token, address[] memory initialMembers) {
        token = IERC20Simple(_token);
        for (uint256 i = 0; i < initialMembers.length; i++) {
            members.push(initialMembers[i]);
        }
    }

    /// @notice Create a simple single-target proposal
    function propose(address target, uint256 value, bytes calldata data, string calldata desc)
        external
        returns (uint256)
    {
        uint256 id = proposalCount++;
        Proposal storage p = proposals[id];
        p.proposer = msg.sender;
        p.description = desc;
        p.target = target;
        p.value = value;
        p.data = data;
        p.createdAt = block.timestamp;
        emit ProposalCreated(id, msg.sender);
        return id;
    }

    /// @notice Cast vote — one vote per member address. Vote weight = current token balance.
    function castVote(uint256 proposalId, bool support) external {
        Proposal storage p = proposals[proposalId];
        require(!p.executed, "Executed");
        require(!_hasVoted(p, msg.sender), "Already voted");

        // Mark voted (store in mapping inside struct)
        p.hasVoted[msg.sender] = true;

        uint256 weight = token.balanceOf(msg.sender);
        if (support) {
            p.yes += weight;
        } else {
            p.no += weight;
        }

        emit VoteCast(proposalId, msg.sender, support, weight);

        // naively check majority over sum of current balances (inefficient)
        uint256 totalYes = p.yes;
        uint256 totalNo = p.no;

        // compute total supply by summing members balances (O(n) every check)
        uint256 totalSupply = 0;
        for (uint256 i = 0; i < members.length; i++) {
            totalSupply += token.balanceOf(members[i]);
        }

        // pass if yes > no AND yes >= 50% of totalSupply (simple majority quorum)
        if (totalYes > totalNo && totalYes * 2 >= totalSupply) {
            _execute(proposalId);
        }
    }

    function _hasVoted(Proposal storage p, address who) internal view returns (bool) {
        return p.hasVoted[who];
    }

    /// @notice Very naive execution — calls target and marks executed
    function _execute(uint256 proposalId) internal {
        Proposal storage p = proposals[proposalId];
        require(!p.executed, "Already executed");
        (bool ok,) = p.target.call{value: p.value}(p.data);
        require(ok, "Call failed");
        p.executed = true;
        emit Executed(proposalId, p.target, p.value);
    }

    // receive funds so treasury / others can send ETH
    receive() external payable {}
}
