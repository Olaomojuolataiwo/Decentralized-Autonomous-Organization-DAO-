// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ITreasuryBasic {
    function executePayment(address recipient, uint256 amount) external returns (bool);
}

contract VulnerableDAO {
    /// -----------------------------------------------------------------------
    /// STRUCTS
    /// -----------------------------------------------------------------------
    struct Proposal {
        address proposer;
        address recipient;
        uint256 amount;
        uint256 yesVotes;
        uint256 noVotes;
        uint256 startBlock;
        uint256 endBlock;
        bool executed;
    }

    /// -----------------------------------------------------------------------
    /// STORAGE — intentionally gas-inefficient
    /// -----------------------------------------------------------------------
    mapping(uint256 => Proposal) public proposals;
    mapping(uint256 => mapping(address => bool)) public hasVoted;
    uint256 public proposalCount;

    ITreasuryBasic public treasury;
    mapping(address => uint256) public votingPower; // ❌ manipulable — no snapshot

    /// -----------------------------------------------------------------------
    /// EVENTS
    /// -----------------------------------------------------------------------
    event ProposalCreated(uint256 indexed id, address indexed proposer);
    event VoteCast(uint256 indexed id, address indexed voter, bool support);
    event Executed(uint256 indexed id);

    /// -----------------------------------------------------------------------
    /// CONSTRUCTOR
    /// -----------------------------------------------------------------------
    constructor(address _treasury) {
        treasury = ITreasuryBasic(_treasury); // ❌ not immutable
    }

    /// -----------------------------------------------------------------------
    /// BAD ADMIN SYSTEM
    /// -----------------------------------------------------------------------
    function setVotingPower(address user, uint256 power) external {
        // ❌ Anyone can arbitrarily inflate their voting weight
        votingPower[user] = power;
    }

    /// -----------------------------------------------------------------------
    /// PROPOSE
    /// -----------------------------------------------------------------------
    function propose(address recipient, uint256 amount) external returns (uint256) {
        proposalCount += 1;

        proposals[proposalCount] = Proposal({
            proposer: msg.sender,
            recipient: recipient,
            amount: amount,
            yesVotes: 0,
            noVotes: 0,
            startBlock: block.number,
            endBlock: block.number + 20, // ❌ tiny voting window
            executed: false
        });

        emit ProposalCreated(proposalCount, msg.sender);
        return proposalCount;
    }

    /// -----------------------------------------------------------------------
    /// VOTE
    /// -----------------------------------------------------------------------
    function vote(uint256 id, bool support) external {
        Proposal storage p = proposals[id];

        require(block.number <= p.endBlock, "Voting ended");
        require(!hasVoted[id][msg.sender], "Already voted");

        hasVoted[id][msg.sender] = true;

        // ❌ manipulable
        uint256 power = votingPower[msg.sender];

        if (support) p.yesVotes += power;
        else p.noVotes += power;

        emit VoteCast(id, msg.sender, support);
    }

    /// -----------------------------------------------------------------------
    /// EXECUTE (insecure)
    /// -----------------------------------------------------------------------
    function execute(uint256 id) external {
        Proposal storage p = proposals[id];

        require(!p.executed, "Already executed");
        require(block.number > p.endBlock, "Voting not over");

        // ❌ No quorum criteria
        // ❌ Passes even with 1 vote
        require(p.yesVotes > p.noVotes, "Rejected");

        p.executed = true;

        // ❌ Executes blindly
        treasury.executePayment(p.recipient, p.amount);

        emit Executed(id);
    }
}
