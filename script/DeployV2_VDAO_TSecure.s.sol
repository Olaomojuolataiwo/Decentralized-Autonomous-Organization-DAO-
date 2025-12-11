// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "forge-std/console.sol";

// Ensure paths are correct for your project
import "../src/VulnerableMembershipToken.sol";
import "../src/VulnerableDAO.sol";
import "../src/TreasurySecure.sol"; // <-- Different Treasury

contract DeployV2_VDAO_TSecure is Script {
    function run() external {
        // --- 1. CONFIGURATION ---
        // Should be the address of your deployed VulnerableMembershipToken
        address tokenAddr = vm.envAddress("TOKEN_ADDRESS");
        require(tokenAddr != address(0), "TOKEN_ADDRESS required");

        vm.startBroadcast();

        // --- 2. VULNERABLE DAO DEPLOYMENT ---
        // Step 2a: Define the 120 member addresses array.
        // **IMPORTANT:** Use the exact 120 addresses from your V1 script here.
        address[120] memory fixedMembers = [
            0xAaC4A34f85f122f596e3eB104581BceB2A095715,
            0x127e548a314da196Dc29Adec1b9A347C7b6E019C,
            0xbCe4Ae99670a9862a9D0461476AbE4514FBF0968,
            0x6fcf7450f3c6b2eFc3215021333bFaDc9bC04c42,
            0x081BeD3aeF309AC70EAd44d2Bb06a2d9a91Bf22F,
            0x53d89EF8afB7EBCfAc4d5C05B4Ae9281feEFC4ed,
            0x809591FE0b0BbdfCec6AB4a1026d583a1D2CC0b0,
            0xd0388BC7727a609878c86059e6D013c2260A0F6b,
            0xa2527392F33C3816aAE1F5Ec967C0C9d9c1eB378,
            0x96B273Bf69A1d9B78D90694668732830D2E0F5Ce,
            0xfab0bADEF95dDa7F9067F4359B639Baf880D6E6E,
            0xf6b9F2C8B11984Ad3E0cbf13B8B52de3E359bA5f,
            0xe795f32b6758C3028Fb8a38300217E0Eb892c9C3,
            0x049b64A6Bee72c402e9C5678ea662899ceDdE52D,
            0x2532496398e69fc75b116dd26B8e018ce50746f8,
            0xc7C4Bc64aeea4965635A44eB326098CB749206b2,
            0x09126978500DA40017231bC6df1C4c74a8C58194,
            0xFa1959986439bD343097291BFBF4d060A00E8ECe,
            0xC931D455406Bd6f392eDa83f6B9A2809b3E0046A,
            0xe6414f0F8269CAf42902671295185b8CB4D41DEB,
            0xaE1fe4B094baFD7445a38Be888FB3e4e3e2B30B9,
            0x4d94b44526f4d44c945260D94E4b54DE2D81060f,
            0xc1A0d7cd782EF834AD41Efc9B37318531A10f9C1,
            0x2bAFD3b097c67AEC1b786924be841242eB6aAD83,
            0xD67faa4289423b8D7bFDC96F0Af6A246875050e7,
            0x9f06598C77cb3a3048d321b3Cb4E577d94204c88,
            0xd62D41B9e3dfC95fEbD05584CaDA17a5DaB4e992,
            0x463DFB8b3C797d853979533dbAfE285fd7335d00,
            0xD4B521E12d2DF29B86D3a1E4E0249F7EFd93d165,
            0xb1234457355F3c732C2749AD08F30a5c79e7EeEE,
            0x5CA628aE5e16BdDAEb6f0dfCA5BDc9E3CBc4B93C,
            0xFF34921f11F4F9329Fa7dE3B6578Cc933837cC3c,
            0xf1B3329F9798E21C873470b9e2cD3CEE9F6eE2Ff,
            0x56D841A82b20Dbb864b8d7E3674781f9D20B2339,
            0xaaD53FB05ca37C68108De45cA61179f0e0EcF6F8,
            0x421cA0117c4543707c65f6d55239F645bf1a0681,
            0x2d115e75dBc546fb4019781c9F901E53e9eb34Ee,
            0xa57F43703B23C52E91D3609DB6DE025a6b098b00,
            0x44D117B5D4F62c91587AB758788985fFafbbBc8a,
            0x058359DE64097bdCbB3d8D96Fd059E0b93Ab7518,
            0x314B5f059e8EB1d24aA0407398f71a57b94e5995,
            0x88646155fAB563E36aceA2F1b194611FE3956E24,
            0x773Be0467c83F57BB59ecdD9Dc9614F0B654F76B,
            0x7C0B2e4De959bB6872EC7b68b1b68431BBCD6f07,
            0x57eD538628E99913E3CDd377B5C5f92b6ef2a5D0,
            0x552190bDb2328945193E47C83Ad71ba0A44CBDcb,
            0xD31d8Ba6efD31e7A85B4faD3467C4Cbb2b80E8B9,
            0x6499b71C83695988137F427c3F1b3241C45984B1,
            0x66Ab1869adF3160852e0eb834b28CB64F9e785ed,
            0xacD319d2686345552644029cA9912E3506BD3cd8,
            0x79F688Ba3b2652353ACefDCD1faA85cD895B330f,
            0x6853B92711b1C5a693e695Aa35AeFBB2958D98c2,
            0x44Dc57D023c3dC1090410bC9E1545D98EA9e4022,
            0x79f7667B8844ae665665d988376D34cf64D6E753,
            0x872aF500a120B5b19358fDcC8a2C081211910D46,
            0x4E97C2272ca51615FC1B056579A46Caf6B807669,
            0x724CAF2160cb4e0909F7e6d12cE54CbFf0d4EC58,
            0xeBABf2690E38cf92FcF46De9f33d61ce43B33DA5,
            0x780428bEe53909dD5B17eE53DfB0b6cd0aae1d51,
            0x7E3feC4b55dEF1a0Da5C236E70BCc358e0F52A9d,
            0x4C23c1aDa55076b41B8dd781Ca0CC3696467B896,
            0x412f5Fcf23B5D933E068f3eec32731d10E0beB31,
            0x85c0Db3f35b5884245Cfe4c0abAc43364747f77e,
            0x130a9Fe13578f784336E04b9F76b8fAfAe322a92,
            0x8ba878Db6ef3BAdc4A966829177c0e0080fC6985,
            0x9E7f62021C0320a8E92aA695d71fce2C475B9a9C,
            0xD6D33B551351E8885F2371FABbb086B603605dc1,
            0x7259B2470bcd334AA7c38Ba4af1ACeA4bf6Ce340,
            0x1Ca61E1762e859DE63a9Aa69A187B5FebE9332BE,
            0x3CC35EA330aa36a29c48462225f02f2a5253fa7B,
            0xB7ee3646B13c3A0e4d648d82AaA954f6411A99F5,
            0xd0223bAEC42fc437d5c209A97a5775dDE6425f4a,
            0x791831E7ebf9dCC49f2f467e825789DeC17ED7Ac,
            0xD0202A1ec10b443C59940a477D058f700b795f1c,
            0xFDf6f137Dc847a4F9FA31bed3fBf4eE3fff36838,
            0x5B6C682ddF62c08d764e415974b4177a4D71c7D1,
            0xA6e7F91126a03cfE345e44154Ca6DD50773339C7,
            0xCf44f52B5B76D9bC5B55F0d4aE1F7476C4fEfa3A,
            0x33f0987F38eD099Bc3347293F641531e8D0EF143,
            0xb891C91C663Ccc84dDD8241D60dD94CDF107e9da,
            0xc2E9dAd3E85b41666EA7BFFaF84eED167e917a84,
            0xc8924657B37D65e41DFBbAE5265F4012BcFdBa6a,
            0x1895fac3d681634f87571885D4cb01cA6D0b087a,
            0x7BBbC006bFac892B0C0E2D5428E56D318Fc13487,
            0x23289a85C13826b1D9238f327f93a301CA37F725,
            0xeA4616547026091aE22Dd8bB35bb5Af9508b2Cc5,
            0xAb4CEAD09D63BBda9F81aC7cF76FC75C3afDD14e,
            0xa5bFE8992c474EC6B9a3BD24A0C9768Dcde0D537,
            0x9765A8ccD5526009E9a312AC0C598c5C451Ace5e,
            0xC2B94e9f3bE0D9F6147d23b93BDCF322eBaa93a9,
            0x7eEe4e583aAf89f157a28DfF878daEDc101249b1,
            0x256CE1c015f2C0f38e8fa10290de1D4478e23b7f,
            0xC807c4cAFf17997556281778aFc25404e020577a,
            0xEcF3Dc07d8B30c1cd137ceB266999399C6830FE0,
            0x18dB8D24de274Bc17AfAC315d8Af93BEF33D8889,
            0xBD12AFaCF211eFAe479A032903fC2Bbaf7E2eCE9,
            0x45474b800457B9922b0b8fdc77bb028630cbb60e,
            0xf1b8a1f2C7A78dB6Ee73B08Eac36Fa709F0072C5,
            0x7Be39d727B7BacF74A56f35eb20049BEEc3806F7,
            0x1CB973576a705e506f46dea654B037672D960750,
            0x0af7D3B45228FbAE93d00d1d63bbB02A15F52197,
            0x61DcA024a50b0138714d4774993adffbb3A72a61,
            0xe13cA154eD8Aa6820F7cDD644223748E318e6B6b,
            0x09F5daB633FBB7fcE857bA6cc49fF42f8b4b34bA,
            0x3f95127e51041290E73E7aF1C8750cC43D8794Ad,
            0xDD9b06d7cD9Ea8FCb204fD2e5ebb622bc8815286,
            0x951CFfa43ebeC96CB217E8705e0d3a8FA14aA9ec,
            0xA29af4492610B63b3FA4da6cc7E60D435221fA81,
            0xc6eD59E896568CfC7cd5109821dcF5e5c913318A,
            0xF69c552Ef1307F2A4F6251CD0D94511641e970FD,
            0x4208fAa7A377BcF5d32A4746F9FEc67cE9974C74,
            0x48D6599FF69Db38164702EC13Ab029B50754c540,
            0xBCD6b65EF5B728FE74429cb93fF0fbA9d0914C34,
            0x115A81aB697bd4996aA57dBfd28F12234bbA4c6d,
            0x5e9650092025315aeEc86F0107a59A03B94eD338,
            0xE80D763CF41d4727096e3bB238238D39D3B630Cb,
            0x075F8A84Eb6Af2B30a408bBbd16F44E726e84350,
            0x84e81e0F7782BEe452B9aF00465d9049530E4d61,
            0xa9EcBD6EcC75B419fD521Fa57b2406F26E96201e,
            0x707D88600D1f1Ce3d0cca27C6fb32810CEdc133e
        ];

        // Step 2b: Create the target DYNAMIC-SIZE array
        address[] memory members = new address[](fixedMembers.length);

        // Step 2c: Explicitly copy elements over
        for (uint256 i = 0; i < fixedMembers.length; i++) {
            members[i] = fixedMembers[i];
        }

        // Deploy the DAO first
        VulnerableDAO dao = new VulnerableDAO(tokenAddr, members);
        address daoAddr = address(dao);
        console.log("V2_DAO_ADDR (VulnerableDAO):", daoAddr);

        // --- 3. TREASURYSECURE DEPLOYMENT (BOUND TO DAO) ---
        // CRITICAL FIX: Bind the Treasury to the DAO address.
        // TreasurySecure is Ownable, and the DAO is set as the owner/governor.
        TreasurySecure treasury = new TreasurySecure(daoAddr);
        address treasuryAddr = address(treasury);
        console.log("V2_TREASURY_ADDR (TreasurySecure):", treasuryAddr);

        vm.stopBroadcast();
    }
}
