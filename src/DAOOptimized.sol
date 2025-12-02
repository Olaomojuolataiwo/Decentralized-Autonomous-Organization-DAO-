// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "@openzeppelin/contracts/governance/Governor.sol";
import "@openzeppelin/contracts/governance/extensions/GovernorSettings.sol";
import "@openzeppelin/contracts/governance/extensions/GovernorVotes.sol";
import "@openzeppelin/contracts/governance/extensions/GovernorTimelockControl.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import "@openzeppelin/contracts/governance/extensions/GovernorVotesQuorumFraction.sol";
import "@openzeppelin/contracts/governance/extensions/GovernorCountingSimple.sol";

/// @title DAOOptimized - Gas-Enhanced, Secure DAO
contract DAOOptimized is Governor, GovernorSettings, GovernorVotes, GovernorTimelockControl, GovernorVotesQuorumFraction, GovernorCountingSimple {

    // --- GAS METRICS EXPOSURE ---
    uint256 public gasUsed_lastProposalCreate;
    uint256 public gasUsed_lastExecute;

    constructor(
        string memory _name,
        ERC20Votes _votingToken,
        TimelockController _timelock,
        uint256 _votingDelay,
        uint256 _votingPeriod,
        uint256 _proposalThreshold,
        uint256 _quorumNumerator
    )
        Governor("DAOOptimized")
        GovernorSettings(uint32(_votingDelay), uint32(_votingPeriod), uint48(_proposalThreshold))
        GovernorVotes(_votingToken)
        GovernorTimelockControl(_timelock)
        GovernorVotesQuorumFraction(_quorumNumerator)
   {} 
   
    mapping(uint256 => ProposalVote) private _proposalVotes;

    // --- CUSTOM QUORUM OPTIMIZATION ---
    function _quorumReached(uint256 proposalId)
        internal
        view
        override (Governor, GovernorCountingSimple)
        returns (bool)
    {
        ProposalVote storage p = _proposalVotes[proposalId];
        uint256 snapshotBlockOrTimestamp = proposalSnapshot(proposalId);
        uint256 supply = token.getPastTotalSupply(snapshotBlockOrTimestamp);
        return p.forVotes * 100 >= supply * quorumNumerator(); // cheap multiplication
    }

    // --- GAS-MONITORING HOOKS ---
    function propose(address[] memory targets, uint256[] memory values, bytes[] memory calldatas, string memory description)
        public
        override(Governor)
        returns (uint256)
    {
        uint256 startGas = gasleft();
        uint256 proposalId = super.propose(targets, values, calldatas, description);
        gasUsed_lastProposalCreate = startGas - gasleft();
        return proposalId;
    }


    function proposalThreshold() public view override(Governor, GovernorSettings) returns (uint256) {
    return super.proposalThreshold();
    }

    function state(uint256 proposalId) public view override(Governor, GovernorTimelockControl) returns (ProposalState) {
    return super.state(proposalId);
    }

    function votingDelay() public view override(Governor, GovernorSettings) returns (uint256) {
        return super.votingDelay();
    }

    function votingPeriod() public view override(Governor, GovernorSettings) returns (uint256) {
        return super.votingPeriod();
    }


    // This is required by the IGovernor interface.
    function COUNTING_MODE() public pure override(GovernorCountingSimple, IGovernor) returns (string memory) {
        return "support=bravo";
    }

    function _cancel(
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    ) internal override(Governor, GovernorTimelockControl) returns (uint256) {
        return super._cancel(targets, values, calldatas, descriptionHash);
    }

    // --- OVERRIDES REQUIRED BY OZ GOVERNOR ---
    function _executor() internal view override(Governor, GovernorTimelockControl) returns (address)
    {
        return super._executor();
    }

    function supportsInterface(bytes4 interfaceId) public view override(Governor) returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
    
    function _executeOperations(
    uint256 proposalId,
    address[] memory targets,
    uint256[] memory values,
    bytes[] memory calldatas,
    bytes32 descriptionHash
    ) internal override(Governor, GovernorTimelockControl) {
    uint256 startGas = gasleft();
    // Inline assembly call for real gas savings (Your existing logic)
    for (uint256 i = 0; i < targets.length; i++) {
        address target = targets[i];
        uint256 value = values[i];
        bytes memory data = calldatas[i];
        bool ok;
        assembly {
            // Assembly block (Your original code)
            ok := call(gas(), target, value, add(data, 32), mload(data), 0, 0)
        }
        require(ok, "DAOOptimized: target call failed");
    }
    gasUsed_lastExecute = startGas - gasleft();
    }

    function _queueOperations(
    uint256 proposalId,
    address[] memory targets,
    uint256[] memory values,
    bytes[] memory calldatas,
    bytes32 descriptionHash
    ) internal override(Governor, GovernorTimelockControl) returns (uint48) { // <--- Added return type
    // It should call the parent to queue the proposal with the timelock
    return super._queueOperations(proposalId, targets, values, calldatas, descriptionHash);
    }

    function proposalNeedsQueuing(uint256 proposalId)
        public
        view
        override(Governor, GovernorTimelockControl)
        returns (bool)
    {
        return super.proposalNeedsQueuing(proposalId);
    
    }
    }
