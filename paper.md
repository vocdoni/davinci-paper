<div class="center">

Last update: 2026-02-27

</div>

# Introduction

Online voting remains one of the most studied yet elusive applications in applied cryptography. As digital services expand across both public and private sectors, secure and universally verifiable online voting systems have become an increasingly desirable goal. Remote electronic voting promises scalability, accessibility, and administrative efficiency; yet the design of systems that simultaneously ensure privacy, integrity, coercion resistance, and transparency under realistic adversarial models remains a formidable challenge. Numerous deployments have revealed deep-rooted usability flaws and security gaps, particularly when verifiability mechanisms are either poorly understood by users or reliant on centralized infrastructure.

Against this backdrop, the Vocdoni project was initiated in 2018 with the aim of rethinking online voting from first principles. The name Voĉdoni, meaning *to give voice* in Esperanto, reflects the project’s foundational goal: to empower collectives, from small associations to millions of citizens, to engage in secure and verifiable decision-making, regardless of technological or institutional barriers. Central to this vision was the idea that voting is not limited to formal governmental elections but serves as a more general-purpose mechanism for collective signaling. Vocdoni introduced a fully anonymous end-to-end verifiable voting system designed to operate efficiently on a range of devices, including smartphones. To support these goals, the team deployed a custom infrastructure emphasizing resilience, neutrality, and transparency.

Technically, the architecture of Vocdoni was based on a bespoke <span acronym-label="BFT" acronym-form="singular+short">BFT</span> layer-1 blockchain, named Vochain. At the time, efficient zero-knowledge (ZK) proof systems were emerging, but not yet practical for most deployments. Vochain provided a performant and low-cost environment (achieving approximately 700 transactions per second) in which advanced cryptographic tools could be used without the constraints imposed by general-purpose blockchains based on the <span acronym-label="EVM" acronym-form="singular+short">EVM</span>. The ability to issue voting transactions without requiring user fees enabled broader accessibility. Over several years of development and deployment, this architecture proved both viable and valuable in practice. However, broader adoption as a universal voting protocol highlighted the need for further architectural refinements and stronger formal guarantees.

In this work, we introduce DAVINCI, a new protocol that builds upon the lessons and conceptual groundwork laid by Vocdoni. DAVINCI adopts a modular design and integrates state-of-the-art cryptographic tools, including succinct ZK proofs, improved bulletin board constructions, and robust coercion resistance mechanisms, reflecting the most recent advances in academic research. Unlike monolithic designs, DAVINCI is conceived as a composable primitive: a foundational layer intended to support secure and verifiable voting in diverse contexts, from blockchain governance to institutional elections. This shift in design philosophy aims to address long-standing challenges in the field, offering a cleaner abstraction with clearer security boundaries and formal underpinnings.  

## Contributions

This work introduces DAVINCI, a modular and verifiable protocol for digital voting, designed to support privacy-preserving, auditable, and adaptable election processes across diverse governance contexts. The protocol *models voting as a constrained state machine*, in which each valid operation is expressed as a formally defined state transition, enforced through succinct <span acronym-label="ZK" acronym-form="singular+short">ZK</span> proofs. That is, at the core of the system lies a set of reusable arithmetic circuits that implement voter authentication, encrypted ballot validation, state transitions, and tally finalization. These circuits are optimized for off-chain proving and are compatible with modern <span acronym-label="ZK-SNARK" acronym-form="singular+short">ZK-SNARK</span> protocols. Application-layer state is maintained off-chain and committed on-chain using Merkle trees as cryptographic accumulators.

A key contribution of this work is the introduction of a generic ballot protocol that abstracts a wide range of voting systems into a unified, parameterized representation. Instead of designing specialized circuits for each voting rule, ballots are expressed as fixed-length vectors subject to configurable constraints, enabling support for approval, ranking, quadratic, single-choice, and multiple-choice elections within the same circuit framework. This design significantly reduces circuit complexity while allowing different tallying and counting rules to be enforced efficiently inside <span acronym-label="ZK" acronym-form="singular+short">ZK</span> proofs.

To coordinate protocol execution over a decentralized network of nodes, DAVINCI includes a set of Ethereum smart contracts that mediate the setup of elections, manage finalization procedures, and verify submitted proofs of correctness. A standardized transaction and data encoding format supports all stages of the process, including vote casting, ballots aggregation, and result publication. This approach ensures that protocol interactions remain deterministic and interoperable across clients and backends. The system also introduces the Vocdoni token, which is used to align incentives between participants. Altogether, the design aims to balance auditability and privacy while reducing trust assumptions on infrastructure providers. By cleanly separating functionalities and providing modular interfaces, the protocol is intended to serve as a foundation for both practical deployments and future extensions, such as integration with alternative identity systems, off-chain data availability layers, or other consensus backends.

## Related work

- State of the art of e-voting: <https://research.azkr.org/blog/evoting-review/>.

## Paper organization

The rest of the paper is organized as follows. In Section  we introduce the necessary background. In Section  we provide a high-level overview of a voting process, omitting technical details for clarity. In Section  we describe the full voting process in detail and in Section  we focus on the ballot protocol. In Section  we discuss the role of the Vocdoni token within the incentive structure of the system. In Section  we analyze the protocol, covering its security properties, implementation details, and performance evaluation. In Section  we conclude the paper with final remarks and future work. Finally, we include Appendix  with the concrete instantiations of all the cryptographic primitives used in the protocol.

# Background

The DAVINCI protocol builds on several decentralized technologies and advanced cryptographic tools. In this section, we give a high-level overview of these components and their role in the system. We first introduce the <span acronym-label="IPFS" acronym-form="singular+short">IPFS</span>, which serves as a decentralized storage layer for distributing large datasets off-chain. We then describe Ethereum, the settlement layer where commitments are published, rules are enforced through smart contracts, and state data is managed using recent mechanisms such as data blobs. Finally, we present the <span acronym-label="ZK" acronym-form="singular+short">ZK</span> proof systems that underpin the protocol’s integrity and security, focusing on <span acronym-label="ZK-SNARK" acronym-form="plural+short">ZK-SNARKs</span> and arithmetic circuits, which allow participants to prove compliance with protocol rules without revealing sensitive information.

## Interplanetary file system

The <span acronym-label="IPFS" acronym-form="singular+full">IPFS</span> is a peer-to-peer distributed storage network designed to make the web more resilient, permanent, and decentralized. Unlike traditional client-server architectures that retrieve data from a specific location (e.g., a URL pointing to a server), <span acronym-label="IPFS" acronym-form="singular+short">IPFS</span> retrieves data based on its content. Every file stored in <span acronym-label="IPFS" acronym-form="singular+short">IPFS</span> is split into blocks, each block is hashed, and the resulting cryptographic hash is used as its unique identifier. This property, known as content addressing, ensures that data is tamper-evident: if the file changes, so does its hash. <span acronym-label="IPFS" acronym-form="singular+short">IPFS</span> also provides deduplication (the same content is only stored once across the network), versioning (content identifiers can point to immutable snapshots of data), and distributed availability (data can be fetched from any node that stores it). Together, these features allow IPFS to function as a decentralized content delivery network.

In the context of the DAVINCI voting protocol, <span acronym-label="IPFS" acronym-form="singular+short">IPFS</span> is particularly useful for off-chain data distribution. Large datasets such as the full census (eligible voters and their weights) and election metadata (which may include questions, options, images, etc.) do not need to be stored directly on Ethereum. Instead, they are stored in <span acronym-label="IPFS" acronym-form="singular+short">IPFS</span>, and only their content hashes are published on-chain. This approach ensures transparency and verifiability, as anyone can fetch the dataset from <span acronym-label="IPFS" acronym-form="singular+short">IPFS</span> and recompute the hash to confirm its integrity, while keeping on-chain storage costs low. That is, election participants can therefore rely on <span acronym-label="IPFS" acronym-form="singular+short">IPFS</span> to access the data without burdening the blockchain with large amounts of data.

## Ethereum

Ethereum is a decentralized blockchain platform that supports programmable transactions through its built-in execution environment, the <span acronym-label="EVM" acronym-form="singular+full">EVM</span>. All interactions with the Ethereum network take the form of transactions, which must be broadcast to the network, validated by consensus, and permanently recorded on-chain. Every transaction requires the payment of a fee (gas), denominated in ETH, to compensate validators for computation and storage. This fee model ensures that resources are used efficiently and prevents denial-of-service attacks by making large or complex operations costly. In the context of DAVINCI, Ethereum serves as the settlement layer where critical commitments are published, ensuring transparency and immutability.

#### Smart contracts.

Smart contracts are programs deployed on the Ethereum blockchain that execute deterministically in response to transactions. Once deployed, they cannot be altered, and their execution is guaranteed by the consensus of the network. In DAVINCI, smart contracts orchestrate the election by managing state transitions and storing critical data such as the current state root and the encryption public key. They enforce the protocol rules in a trustless environment, ensuring that no single participant can manipulate the election. By anchoring these rules in Ethereum smart contracts, DAVINCI guarantees that the election logic is applied consistently and verifiably across all participants.

#### Data blobs.

Data availability is a key requirement for decentralized protocols. Ethereum’s recent EIP-4844 (Buterin et al. 2022) introduces data blobs as a mechanism for publishing large volumes of off-chain data alongside transactions at a lower cost than traditional storage. These blobs are kept on-chain for 4096 epochs, approximately 18 days, after which they are pruned. For longer election periods, third-party solutions based on EIP-4844 can be used to extend data availability (AAAATODOauthor 9999). In DAVINCI, sequencers use data blobs to share state transition data efficiently. By publishing state updates in blobs, sequencers allow other participants to reconstruct and verify the evolution of the election without overloading Ethereum’s permanent storage. This ensures scalable, decentralized data availability while retaining verifiability.

## Merkle trees

Merkle trees (Merkle 1987) are cryptographic hash trees that enable compact proofs of data inclusion. Formally, a Merkle tree is a binary tree structure where each leaf node represents the cryptographic hash of a set of data and every non-leaf node is derived from the hash of its children. The apex of the tree, the *Merkle root*, acts as a succinct cryptographic commitment to the entire dataset. To prove that a specific element $x$ exists within the set, a prover provides a Merkle path consisting of the sibling nodes along the path from the leaf to the root. A verifier can reconstruct the root in logarithmic time $O(\log n)$ and check it against the committed state, without requiring access to the full dataset. In DAVINCI, we use two specialized variants of this structure to commit critical data: a sparse Merkle tree for the voting state and an incremental Merkle tree for the voter registry (census).

#### Sparse Merkle trees.

A <span acronym-label="SMT" acronym-form="singular+short">SMT</span> represents a key-value map where each leaf is the hash of a (key, value) pair and each parent node is the hash of its two children. In an <span acronym-label="SMT" acronym-form="singular+short">SMT</span>, every possible key maps to a unique leaf position (with empty slots defaulting to a zero value), yielding a fixed-height binary tree. This property is circuit-friendly, since the proof of a leaf’s membership or non-membership has a consistent length and can be efficiently verified inside a <span acronym-label="ZK-SNARK" acronym-form="singular+short">ZK-SNARK</span> circuit using a SNARK-optimized hash. In DAVINCI, the state tree is implemented as an <span acronym-label="SMT" acronym-form="singular+short">SMT</span> of fixed depth. In particular, configuration parameters occupy reserved leaf addresses, each voter’s encrypted ballot is stored at a leaf indexed by their unique identifier, and each one-time vote identifier is recorded at a dedicated leaf path. Because the <span acronym-label="SMT" acronym-form="singular+short">SMT</span> covers a vast key space, a user or sequencer can prove that a given key is present in the state (or conversely, that it remains empty) by providing a short Merkle proof against the tree’s root, rather than revealing the entire state. This enables compact proofs of state correctness. For instance, showing in ZK that a vote identifier has not appeared before or that a new ballot’s ciphertext is correctly inserted into the state. The <span acronym-label="SMT" acronym-form="singular+short">SMT</span> used in DAVINCI follows the circomlib Merkle tree specification (Poseidon-based) (AAAATODOauthor 9999), ensuring that state updates can be verified succinctly on-chain via the Merkle root and proof.

#### Incremental Merkle trees.

The census (voter registry) is maintained with an <span acronym-label="IMT" acronym-form="singular+short">IMT</span>, a binary Merkle tree designed for efficient sequential updates (AAAATODOauthor 9999). Unlike a sparse tree, the <span acronym-label="IMT" acronym-form="singular+short">IMT</span> grows in height only as needed with the number of leaves and eliminates the overhead of hashing dummy “zero” siblings. In this scheme, voters are assigned sequential leaf indices in a continuously evolving tree, rather than being placed at cryptographic key-derived positions. In DAVINCI, the census Merkle tree is built as an <span acronym-label="IMT" acronym-form="singular+short">IMT</span>: each eligible voter’s identifier (or a commitment to it) and voting weight are stored in the next available leaf, and only the Merkle root of this tree (the `censusRoot`) is published on-chain. This design makes membership updates and proof generation extremely low-cost for the census. Appending a new voter requires recomputing hashes only along the single path from the new leaf to the root, and the tree’s depth adjusts optimally (e.g. a tree of N voters has height $\approx \log_2{N}$, instead of a fixed large height). Consequently, proving one’s inclusion in the voter list is more efficient than it would be with an SMT: the Merkle proof is shorter and involves no unnecessary default nodes. A voter can thus obtain a small proof of their membership in the census (their leaf’s existence under the known root) without revealing their index or identity, and include this in a <span acronym-label="ZK-SNARK" acronym-form="singular+short">ZK-SNARK</span> to demonstrate eligibility. In summary, the <span acronym-label="IMT" acronym-form="singular+short">IMT</span>’s focus on sequential insertion and minimal hashing overhead makes it well-suited for the frequently-updated census tree, offering better update performance and smaller circuits for verification than a traditional <span acronym-label="SMT" acronym-form="singular+short">SMT</span> structure in this context.

## Zero-knowledge proofs

Zero-knowledge (ZK) proofs are cryptographic protocols that allow one party (the prover) to convince another (the verifier) that a certain statement is true, without revealing any information beyond the validity of the statement itself. In the context of voting, this enables participants to prove that their encrypted ballot is well-formed and complies with the election rules, without disclosing their actual choice.

#### <span acronym-label="ZK-SNARK" acronym-form="plural+short">ZK-SNARKs</span>.

We focus on a specific type of proof system called zero-knowledge succinct non-interactive arguments of knowledge (<span acronym-label="ZK-SNARK" acronym-form="plural+abbrv">ZK-SNARKs</span>). Informally, while a <span acronym-label="ZK" acronym-form="singular+short">ZK</span> proof convinces the verifier that a valid witness exists, an argument of knowledge additionally ensures that the prover actually knows such a witness, except with negligible probability. <span acronym-label="ZK-SNARK" acronym-form="plural+abbrv">ZK-SNARKs</span> extend this notion with two crucial properties: they are non-interactive, requiring only a single message from prover to verifier, and succinct, meaning that proof size and verification cost remain small regardless of the size of the underlying statement. For instance, Groth16 proofs (Groth 2016), which rely on pairing-based cryptography over elliptic curves, are only about 200 bytes long and can be verified in a few milliseconds. These properties make <span acronym-label="ZK-SNARK" acronym-form="plural+abbrv">ZK-SNARKs</span> particularly well-suited for blockchain applications, where verification cost and data size are critical. In DAVINCI, <span acronym-label="ZK-SNARK" acronym-form="plural+abbrv">ZK-SNARKs</span> are used at multiple stages of the protocol: voters generate proofs to show that their encrypted ballots are correct and sequencers use recursive <span acronym-label="ZK-SNARK" acronym-form="plural+abbrv">ZK-SNARKs</span> to allow multiple proofs to be aggregated efficiently and generate proofs to attest to valid state transitions. In essence, <span acronym-label="ZK-SNARK" acronym-form="plural+abbrv">ZK-SNARKs</span> enable both voters and sequencers to produce compact proofs that can be checked on-chain, ensuring that all protocol rules are followed without requiring trust in any party.

#### Trusted setup.

A limitation of some <span acronym-label="ZK-SNARK" acronym-form="singular+short">ZK-SNARK</span> protocols is their reliance on a <span acronym-label="CRS" acronym-form="singular+short">CRS</span> generated during a so-called trusted setup. The <span acronym-label="CRS" acronym-form="singular+short">CRS</span> is built from random values that must not be known to either the prover or the verifier. To achieve this, the <span acronym-label="CRS" acronym-form="singular+short">CRS</span> can be created by a trusted third party or, more robustly, via a secure <span acronym-label="MPC" acronym-form="singular+short">MPC</span> protocol (Canetti 2001). In an MPC setup, it suffices that at least one participant discards their secret contribution to ensure the integrity of the whole ceremony. For DAVINCI, we run an <span acronym-label="MPC" acronym-form="singular+short">MPC</span> for each of the circuits, see Sections  and .

#### Arithmetic circuits.

In general, <span acronym-label="ZK-SNARK" acronym-form="plural+abbrv">ZK-SNARKs</span> operate by proving the satisfiability of an arithmetic circuit. An arithmetic circuit (from now on also called circuit or <span acronym-label="ZK" acronym-form="singular+short">ZK</span> circuit) is a directed acyclic graph where nodes represent addition or multiplication gates over a finite field. The inputs and outputs of the circuit correspond to the public inputs and private witnesses of the computation, while the intermediate wires carry intermediate values. Any deterministic computation, from verifying an encryption to checking Merkle proofs, can be compiled into an arithmetic circuit (Gennaro et al. 2013). In practice, proving with <span acronym-label="ZK-SNARK" acronym-form="plural+abbrv">ZK-SNARKs</span> means showing knowledge of a secret witness (e.g., a plaintext ballot or encryption randomness) that satisfies all the equations encoded in the circuit. For example, the ballot circuit in DAVINCI encodes the constraints that a ciphertext is well-formed, that the vote identifier is correctly derived, and that the ballot complies with the rules of the voting mode. The prover generates a proof of satisfiability, while the verifier only checks the proof against the public inputs, without learning the secret witness. By building complex protocol logic from arithmetic circuits, and using <span acronym-label="ZK-SNARK" acronym-form="plural+abbrv">ZK-SNARKs</span> to prove their satisfiability, DAVINCI ensures that every step of the election process, from ballot submission to state transitions, is enforced cryptographically and publicly verifiable.

# Protocol intuition

The following section provides an overview of the DAVINCI protocol, describing its main phases and actors without delving into technical details. The election process is governed by smart contracts deployed on Ethereum, which ensure transparency, enforce rules, and verify proofs. As shown in Figure , the protocol consists of five main phases, from the setup of the election to the publication and verification of final results.

<figure id="fig:protocol-intuition">
<embed src="docs/media/a54af9f48759f41103fb436b7b251e948496bdcb.pdf" style="width:4.44444in" />
<p></p>
<figcaption>Overview of the protocol flow. <span>Figure is outdated with respect to new actors and phases.</span></figcaption>
</figure>

1.  *Election setup*. In the first phase, the *organizer* gathers all census data and generates a cryptographic commitment to this data. Additionally, the organizer defines the voting parameters, including the number of voting options and the vote-counting mechanism (e.g., weighted voting, quadratic voting, etc.). Once these details are set, the organizer submits a transaction to the process management smart contract on the Ethereum blockchain. This transaction publicly records the voting parameters and census commitment, ensuring transparency and preventing any subsequent alterations to the voting setup.  

2.  *Encryption key generation.* A designated group of participants, referred to as *key wardens*, collaboratively generate a shared encryption public key, which voters will use to encrypt their votes. This key is established through a <span acronym-label="DKG" acronym-form="singular+short">DKG</span> protocol, ensuring that no single party can control or reconstruct the corresponding private key independently. Once the encryption public key is securely computed and published in the smart contract, the voting period can start.  

3.  *Voting period*. During the voting period, two actors interact continuously: *voters*, who cast their encrypted ballots, and *sequencers*, independent entities responsible for collecting, verifying, and processing these ballots before committing them to the shared state. Both processes, ballot submission by voters () and vote batching by sequencers (), occur continuously and in parallel throughout this phase. The voting period remains open until the deadline defined by the organizer, allowing voters to submit or overwrite ballots at any time, while sequencers periodically process new submissions and update the election state accordingly.  

    1.   *Vote casting*. Voters select their preferred choices according to the voting rules established by the organizer and captured in the process management smart contract. Instead of submitting their votes directly on-chain, they send them off-chain to a sequencer of their choice for processing. To ensure privacy, votes are encrypted using the available encryption public key. To ensure privacy, votes are encrypted using the available encryption public key. Additionally, users compute a unique vote identifier that will allow them to verify that their vote has been included in the final result. Alongside the encrypted vote and the vote identifier, each voter must also provide the following data: a proof of valid voting, demonstrating that the vote complies with the election rules; a proof of eligibility, verifying that they are registered in the census; and a proof of identity ownership, in the form of a digital signature, confirming that they are the legitimate voter and are not impersonating someone else. To mitigate coercion and vote-buying, the protocol allows voters to overwrite their vote any number of times during the voting phase.  

    2.   *Vote batching*. During this phase, sequencers collect encrypted votes from multiple voters along with their corresponding proofs, and verify the validity of these submissions. That is, sequencers verify the signatures, to ensure the votes were cast by legitimate voters; they verify the proof of compliance, confirming that each vote adheres to the polling rules, and the census membership proofs against the commitment to the census data that was originally registered in the process management smart contract. Once the sequencers have processed and verified all votes, they must prove that these verifications were performed correctly. Instead of submitting individual verifications for each vote, they generate a single ZK proof that attests to the correctness of all verifications. Additionally, the sequencers reencrypt the votes and generate a proof of the correct reencryption computation. While this process does not alter the final tally, it prevents voters from decrypting their original vote. This step mitigates vote selling or coercion, as voters are no longer able to prove their choice to third parties. Finally, sequencers submit the reencrypted votes along with their verification and reencryption proofs to the process management smart contract. The smart contract verifies all the proofs provided by the sequencers to check that they complied with the protocol.  

4.  *Decryption key generation*.  

5.  *Tally finalization*. At the end of the voting period, the smart contract ceases to accept new state updates, effectively finalizing the process. The organizer then computes the outcome of the election and submits both the results and a proof of correctness to the smart contract. The contract verifies the proof, ensuring that the tally has been derived faithfully from the final state. Once this verification succeeds, the results and the corresponding state root remain available on-chain, providing an immutable record of the election outcome that can be independently audited by anyone.

# Voting protocol

This section outlines the DAVINCI voting protocol. First, we introduce the parties involved in the process in Section . In Section , we describe the census data structures and in Section  the state Merkle trees. Then, in Section  we present the Ethereum smart contracts that rule the DAVINCI protocol. In Section , we present the ZK circuits used to enforce vote validity, authentication, aggregation, state transitions, and results computation. Finally, in Section , we detail the full protocol flow step by step, from the voting setup to the results validation and process finalization.

## Parties involved

An election involves four types of participants: organizer, key wardens, voters, and sequencers.

#### Organizer.

The organizer is the entity responsible for defining and setting up the election. Its key responsibilities include defining the voting parameters and gathering the census data. The organizer ensures that the election is structured correctly but does not participate in vote collection or tallying.

#### Key wardens.

Key wardens are a set of decentralized parties that collaboratively generate a public encryption key that voters use to encrypt their votes.

#### Voters.

Voters are the participants that belong the census and are allowed to cast their votes in the election.  

#### Sequencers.

Sequencers are a set of parties that during the voting period receive and verify encrypted ballots from voters, reencrypt votes to prevent coercion, and update the shared public state accordingly.

## Smart contracts

The DAVINCI protocol operates on an Ethereum-compatible network, which serves as the source of truth for the election. By leveraging an Ethereum virtual machine (EVM) blockchain, all election transitions become immutable and publicly verifiable. To coordinate and validate each phase of the process, DAVINCI deploys a set of smart contracts that enforce protocol rules, verify zero-knowledge proofs, and maintain on-chain commitments such as state roots, encryption keys, and final results. Together, these contracts provide a trustless execution environment that guarantees the correct and transparent progression of the election without relying on any centralized authority.

The <span id="\detokenize{{\sf{OrganizationRegistry}}}"></span> smart contract is used to create and manage organizations within the system. Each organization is identified by the Ethereum address of its creator and is associated with a name and a URL pointing to its metadata. At this stage, the contract serves only as a registration mechanism, but it lays the foundation for future extensions, such as managing multiple elections under the same organization.

The <span id="\detokenize{{\sf{CensusManagement}}}"></span> smart contract xxx.

The <span id="\detokenize{{\sf{KeyManagement}}}"></span> smart contract coordinates the <span acronym-label="DKG" acronym-form="singular+short">DKG</span> process among the key wardens. It records their contributions, verifies proofs of correct participation, and ensures that a valid encryption public key is produced once the <span acronym-label="DKG" acronym-form="singular+short">DKG</span> round is complete.

The <span id="\detokenize{{\sf{ElectionRegistry}}}"></span> manages the lifecycle of each election, from its creation to the registration of final results. It maintains the election’s current state and ensures that all transitions follow the protocol.

The <span id="\detokenize{{\sf{StateTransitionVerifier}}}"></span> is responsible for validating the proofs that attest to correct updates of the election state. It stores the verification key corresponding to the state transition circuit (see Section ) and checks that each submitted proof correctly links the previous and new state roots. Only transitions verified through this contract are accepted as valid updates by the process registry.

The <span id="\detokenize{{\sf{ResultsVerifier}}}"></span> contract validates the proof of correct tally computation. It contains the verification key for the results circuit (see Section ) and ensures that the final results submitted by the organizer match the commitments from the final state. Once verified, the results and their proof are permanently recorded on-chain, providing a tamper-proof reference for the election outcome.  

## Census

**INDEX is missing!**  
The census defines the set of eligible voters and their associated voting weights. At its core, a census is simply a dataset that, for each voter, contains a unique identifier (typically an Ethereum address), a voting weight, and a means to produce a membership proof that can be verified inside a <span acronym-label="ZK" acronym-form="singular+short">ZK</span> circuit. DAVINCI supports two mechanisms for generating such proofs:

- *Credential-based membership proofs*: eligibility is certified by a digital signature issued by a <span acronym-label="CSP" acronym-form="singular+short">CSP</span>.

- *Merkle-tree-based membership proofs*: the census is organized as an incremental Merkle tree (see Section ) and denoted by $\hypertarget{\detokenize{\sf{MT^{\texttt{census}}}}}{\sf{MT^{\texttt{census}}}}$. Each voter is assigned a sequential index in the tree, and their identifier and weight are stored in the corresponding leaf. Only the Merkle root is kept on-chain, and sequencers supply Merkle proofs to attest membership.

To support different census models, the [](#\detokenize{{\sf{ElectionRegistry}}}) smart contract stores the following three parameters:

- `censusOrigin`: the deployment model (off-chain static, off-chain dynamic, on-chain dynamic, or <span acronym-label="CSP" acronym-form="singular+short">CSP</span>).

- `censusURI`: a <span acronym-label="URI" acronym-form="singular+short">URI</span> pointing to an external reference (URL, GraphQL endpoint, CDN path, IPFS/IPNS, etc.) from which sequencers can download or query the census data.

- `censusRoot`: the on-chain commitment used for membership verification. Its interpretation depends on the `censusOrigin`. In the <span acronym-label="CSP" acronym-form="singular+short">CSP</span> model, this parameter corresponds to the **hash of the <span acronym-label="CSP" acronym-form="singular+short">CSP</span>’s public key**, and in the case of Merkle trees, it corresponds to a Merkle root (off-chain static/dynamic) or a census contract address (on-chain dynamic).

Organizers are free to construct the census from various data sources, such as private membership registries, self-sovereign identity credentials, or Ethereum-based tokens (e.g. ERC-20 or NFTs) whose balances define eligibility. This flexibility supports a broad range of use cases and governance scenarios. The supported census models are summarized in Table  and described in detail below.

#### Credential service provider.

Voter eligibility is certified by a digital signature issued by a <span acronym-label="CSP" acronym-form="singular+short">CSP</span>. A voter obtains a signed credential from the <span acronym-label="CSP" acronym-form="singular+short">CSP</span>, and sequencers verify the signature inside the <span acronym-label="ZK" acronym-form="singular+short">ZK</span> circuits. In this case, `censusRoot` stores the <span acronym-label="CSP" acronym-form="singular+short">CSP</span>’s public key, and `censusURI` specifies the endpoint where voters obtain their credential. This model is suitable when eligibility is managed externally through attested identities rather than by maintaining a Merkle-tree dataset.

#### Off-chain static census.

The organizer constructs a fixed census prior to the election. The Merkle tree is built locally, its root is stored in `censusRoot`, and `censusURI` specifies the endpoint from which sequencers can retrieve the full tree. Since the census is static, no updates occur during the voting period.

#### Off-chain dynamic census.

The Merkle tree remains off-chain, but the organizer may append new voters during the voting period (never deleting voters or modifying weights, as this would enable double voting). Each new insertion produces a new Merkle root, which the organizer must publish to the [](#\detokenize{{\sf{ElectionRegistry}}}) contract by updating the `censusRoot` parameter. As in the static model, `censusURI` provides the endpoint from which sequencers download the current version of the tree. Sequencers verify membership proofs against the most recently published root.

#### On-chain dynamic census.

In this configuration, the census is managed by a dedicated on-chain contract ([](#\detokenize{{\sf{CensusManagement}}})) that supports adding new members during the voting period. The address of this contract is stored in `censusRoot`, while `censusURI` points to an external representation of the tree. The [](#\detokenize{{\sf{CensusManagement}}}) contract maintains a history of valid Merkle roots. Sequencers may therefore generate membership proofs using older roots, and during state transitions the [](#\detokenize{{\sf{ElectionRegistry}}}) contract queries the [](#\detokenize{{\sf{CensusManagement}}}) contract to verify that the root used in the proof is still valid. As in all dynamic models, only additions to the census are permitted during the voting period.

## State tree

The state Merkle tree, denoted by $\hypertarget{\detokenize{\sf{MT^{\texttt{state}}}}}{\sf{MT^{\texttt{state}}}}$, represents the evolving global state of an election in DAVINCI. It is implemented as a <span acronym-label="SMT" acronym-form="singular+short">SMT</span> of fixed depth $D = 64$, as described in Section . The state tree acts as a cryptographic accumulator that compactly commits to all relevant election data, including configuration parameters, vote identifiers, and encrypted ballots. By organizing the election state in a single <span acronym-label="SMT" acronym-form="singular+short">SMT</span>, DAVINCI supports efficient membership and update proofs that can be verified inside <span acronym-label="ZK" acronym-form="singular+short">ZK</span> circuits, enabling succinct and verifiable state transitions.

The root of the state tree, denoted $\texttt{stateRoot}$, is committed on-chain and serves as the authoritative reference to the current election state. Each state transition performed by a sequencer updates the tree and produces a new root. The correctness of this update, namely, that it follows the protocol rules and correctly incorporates new votes, is attested by a <span acronym-label="ZK-SNARK" acronym-form="singular+short">ZK-SNARK</span> proof, which is verified by the $\hyperlink{\detokenize{{\sf{StateTransitionVerifier}}}}{{\sf{StateTransitionVerifier}}}$ smart contract before the new root is accepted.

#### Namespaced key space.

The state tree operates over keys in the range $[0, 2^{64}-1] \subset \mathbb{F}_p$ and uses a SNARK-friendly hash function (Poseidon, see Section ) to enable efficient in-circuit verification. To prevent collisions between different categories of data stored in the state, the 64-bit key space is partitioned into three disjoint numeric namespaces using a fixed thershold $N$. We define $$N = 3 \cdot 2^{D-2},$$ which splits the address space into a lower region for configuration parameters, followed by a region for vote identifiers, and an upper region for encrypted ballot storage. This strict separation ensures that configuration entries, vote identifiers, and ballots can never collide. The structure of the tree is depicted in Figure .

<figure id="fig:mt-state">
<embed src="docs/media/bb868084ffca79d0a90459b9562fa26661424b56.so" style="width:6.25in" />
<figcaption>Structure of the state Merkle tree. The first leaves are reserved for global election parameters while subsequent leaves store vote identifiers and encrypted ballots.</figcaption>
</figure>

#### Configuration namespace.

The lowest indices of the tree are reserved for fixed process parameters that define the election rules. These keys are deterministic and occupy a negligible portion of the address space. Typical entries include:

- `0x0`: the election identifier (`processID`).

- `0x1`: the census origin (`censusOrigin`).

- `0x2`: the ballot mode configuration, which is the set of rules for validating votes (`ballotMode`).

- `0x3`: the encryption public key used to encrypt the ballots (`encryptionKey`).

- `0x4`: an accumulator of the encrypted votes that need to be added to the tally (`resultsAdd`).

- `0x5`: an accumulator of the encrypted votes that have been overwritten (`resultsSub`).

Let $\texttt{configMax}$ denote the largest index reserved for configuration parameters.

#### Vote identifier namespace.

The interval $[\texttt{configMax}+ 1, N - 1]$ is reserved for *vote identifiers* (`voteID`), which allows voters to verify that their vote has been included in the election state, without revealing or linking to the corresponding encrypted ballot. Vote identifiers are derived by hashing the process identifier, the voter’s address, and fresh randomness, and then mapping the result into the allowed range via modular reduction: $$\texttt{voteID}= \texttt{voteIDMin} + \bigl(\text{Hash}(\texttt{processID},\texttt{address},k) \bmod (N - \texttt{voteIDMin})\bigr),$$ where $\texttt{voteIDMin} = \texttt{configMax} + 1$. The [](#\detokenize{{\sf{StateTransitionCircuit}}}) recomputes this derivation and enforces that $\texttt{voteIDMin} \le \texttt{voteID}< N$, guaranteeing that vote identifiers cannot overlap with configuration entries or ballot storage.

Unlike classical nullifiers, vote identifiers are not used to prevent duplicate voting directly. Instead, correctness is enforced at the circuit level: the state transition circuit guarantees that a vote identifier can only be inserted if the corresponding leaf in the state tree is empty. This emptiness check is enforced inside the ZK circuit. Since the vote identifier depends on a fresh random value $k$, if a collision occurs (i.e., the computed leaf is already occupied), the circuit will reject the transition. In that case, the voter must resample $k$ and recompute a new vote identifier until an unused leaf is obtained. As a result, collisions do not compromise correctness or liveness, but merely require retrying the identifier derivation.

Note that the maximum number of vote identifiers that can be stored is bounded by the size of this namespace ($\approx 3\cdot 2^{62}$), which upper-bounds the total number of votes and overwrites that can be processed throughout the election. This capacity is orders of magnitude larger than any realistic election workload: historical elections peak at $\approx 10^{9}$ votes (Reuters 2024), ensuring that identifier exhaustion is practically impossible.

#### Encrypted ballot namespace.

The upper portion of the tree, $[N,\,2^{64}-1]$, is reserved for storing encrypted ballots. In contrast to vote identifiers, ballot storage locations are deterministic and derived from the voter’s position in the census. Let $\texttt{idx}$ denote the voter’s census index, proven via a census membership proof. The storage path for the encrypted ballot is computed as $$\text{encPath} = N + 1 + \bigl(\texttt{idx}\cdot 2^{16} + (\texttt{address}\bmod 2^{16})\bigr).$$ This construction assigns each eligible voter a unique, reserved leaf in the state tree. Because the index $\texttt{idx}$ is authenticated by the census, a voter can only write to their own slot. This enables efficient *last-vote-wins* semantics: if a voter overwrites their ballot, the new ciphertext replaces the previous one at the same path, while the tally is updated by subtracting the old contribution and adding the new one.

Together, the state tree provides a compact and tamper-proof commitment to the current status of the election. At the end of the election, the final state root together with the on-chain verification of all transitions serves as a complete cryptographic record of the election, encapsulating both the tally and the integrity of the entire voting procedure.

## Circuits

At the core of DAVINCI lie a set of arithmetic circuits that enforce the correctness of every step of the election. Each circuit corresponds to a distinct task and, taken together, they guarantee that all protocol rules are satisfied without revealing any private information. Specifically, the *ballot circuit* (Section ) ensures that encrypted votes are valid and well-formed, the *verifier circuit* (Section ) verifies the voter’s proof; the *aggregation circuit* (Section ) combines multiple authenticated votes into a single proof; the *state transition circuit* (Section ) updates the global state root and produces the <span acronym-label="ZK-SNARK" acronym-form="singular+short">ZK-SNARK</span> proof that is verified on-chain; and the *results circuit* (Section ) proves that the election results were computed correctly. The flow of these circuits and their interactions is shown in Figure .

<figure id="fig:circuits-flow">
<embed src="docs/media/fc5087291dbc2a1a3dd342dbe00dc4f9ed53aa99.pdf" />
<figcaption> Overview of the circuit flow in DAVINCI. <span><em>Results circuit</em> is missing.</span></figcaption>
</figure>

For clarity, the circuits are described in this section with their full set of public inputs explicitly listed. In the actual implementation, however, we apply an optimization: rather than exposing all public inputs ${\sf{PI}}$ individually, we compute a single commitment $h = \hyperlink{\detokenize{{\sf{MiMC}}}}{{\sf{MiMC}}}({\sf{PI}})$ and use $h$ as the only public input. The proof verifier then checks that $\hyperlink{\detokenize{{\sf{MiMC}}}}{{\sf{MiMC}}}({\sf{PI}}) = h$, ensuring that the original public inputs are consistent while reducing both proof size and verification cost. Note that this optimization does not alter the semantics of the circuits but significantly reduces verifier complexity and on-chain verification costs. Other implementation aspects such as the exact number of constraints and the proving frameworks used are deferred to Section .

The ballot circuit (<span id="\detokenize{{\sf{BallotCircuit}}}"></span>), illustrated in Figure , is generated locally by the voter at the time of casting a ballot. Its purpose is twofold: first, to prove that the encrypted ballot is valid and complies with the protocol rules defined by the organizer; and second, to prove that the vote identifier (`voteID`) has been correctly derived. The correctness of this circuit is attested by a <span acronym-label="ZK" acronym-form="singular+short">ZK</span> proof generated using the <span acronym-label="ZK-SNARK" acronym-form="singular+short">ZK-SNARK</span> protocol described in Section , instantiated over the BN254 curve. We call the resulting proof *ballot proof* and denote it as $\hypertarget{\detokenize{\texttt{ballotProof}}}{\texttt{ballotProof}}$. We detail below the inputs and constraints of the ballot circuit.

<figure id="fig:circuit-ballot">
<embed src="docs/media/c5555cb7bf4005f85d7ce964c0e13feaefadb855.pdf" style="width:5.27778in" />
<figcaption>Ballot circuit. All public values are framed in green.</figcaption>
</figure>

The verifier circuit (<span id="\detokenize{{\sf{VerifierCircuit}}}"></span>), illustrated in Figure , is generated by the sequencer when processing a vote. This circuit verifies the ballot’s proof generated by the voter and the correctness of their digital signature. The correctness of this circuit is attested by a ZK proof generated using the ZK-SNARK protocol described in Section , instantiated over the BLS12-377 curve. We call the resulting proof the *authentication proof* and denote it as $\hypertarget{\detokenize{\texttt{authenticationProof}}}{\texttt{authenticationProof}}$. We detail below the inputs and constraints of this circuit. – Authentication of verification proof?

<figure id="fig:circuit-verifier">
<embed src="docs/media/9c47fc203425db47dba2ace630d43c84765fdd04.pdf" style="width:6.25in" />
<figcaption>Authentication circuit. All public values are framed in green.</figcaption>
</figure>

The aggregation circuit (<span id="\detokenize{{\sf{AggregationCircuit}}}"></span>), illustrated in Figure , is generated by the sequencer to combine multiple authenticated votes into a single proof. Its purpose is to reduce verification overhead by recursively aggregating individual authentication proofs, while ensuring that all aggregated votes belong to the same election. The batch size ($\texttt{batchSize}$), i.e., the maximum number of proofs aggregated in a single execution, is a fixed parameter (currently set to 60). If fewer proofs are available, the sequencer pads the batch with dummy proofs so that the circuit always operates on a fixed-size input. The correctness of this circuit is attested by a ZK proof generated using the <span acronym-label="ZK-SNARK" acronym-form="singular+short">ZK-SNARK</span> protocol described in Section , instantiated over the BW6-761 curve. We call the resulting proof the *aggregation proof* and denote it as $\hypertarget{\detokenize{\texttt{aggregationProof}}}{\texttt{aggregationProof}}$. We detail below the inputs and constraints of the aggregation circuit.

<figure id="fig:circuit-aggregate">
<embed src="docs/media/7d5d36e5c8b7502478134756460040a241d92680.pdf" style="width:5.55556in" />
<figcaption>Aggregation circuit. All public values are framed in green.</figcaption>
</figure>

The state transition circuit (<span id="\detokenize{{\sf{StateTransitionCircuit}}}"></span>), illustrated in Figure , is generated by the sequencer to update the global state of the election. Its purpose is to verify that a batch of aggregated votes has been correctly incorporated into the state Merkle tree, that overwrites and vote identifiers are handled consistently, that the accumulators of encrypted results are updated accordingly, that each included vote corresponds to an eligible voter included in the census, and that the state transition data used by the sequencer matches the data made available through Ethereum data blobs. The correctness of this circuit is attested by a <span acronym-label="ZK" acronym-form="singular+short">ZK</span> proof generated using the <span acronym-label="ZK-SNARK" acronym-form="singular+short">ZK-SNARK</span> protocol described in Section , instantiated over the BN254 curve, which is supported by Ethereum’s native precompiles for proof verification. We call the resulting proof the *state proof* and denote it as $\hypertarget{\detokenize{\texttt{stateProof}}}{\texttt{stateProof}}$. This proof is submitted on-chain and verified by the process management smart contract, ensuring that every accepted state transition complies with the protocol rules.

To formalize the setting, let the sequencer collect a batch of $N$ votes ($N\leq60$), of which $n$ are new vote submissions and $m = N-n$ are overwrites of previously cast ballots. Without loss of generality, we assume that the batch is ordered such that the first $n$ votes correspond to new submissions, and the remaining $m$ votes correspond to overwrites. In the following, we describe the inputs and constraints of the state transition circuit in detail.

The results circuit (<span id="\detokenize{{\sf{ResultsCircuit}}}"></span>) proves that... .

<figure id="fig:circuit-results">
<embed src="docs/media/2c0033ab1121d1fa6c77f1e221c55118f5a10fd0.pdf" style="width:5.55556in" />
<figcaption>Aggregation circuit. All public values are framed in green. Circuit is not correct.</figcaption>
</figure>

## Protocol flow

In this section we describe the overall flow of the DAVINCI voting protocol. An election is structured into five main phases: election setup, encryption key generation, voting period, decryption key generation, and tally finalization. Each phase specifies the interactions between the organizer, key wardens, voters, sequencers, and the smart contracts that coordinate the election. An overview of the complete process is shown in Figure .

In this phase, sequencers register and the organizer sets the election up.  

For each new election, the organizer performs the following steps:

1.  Prepare the census data `censusData` and generate the census Merkle tree $\sf{MT^{\texttt{census}}}$ with that data.

2.  Compute the census commitment $\texttt{censusRoot}= \sf{MT^{\texttt{census}}}.\hyperlink{\detokenize{\sf{Root}}}{\sf{Root}}()$.

3.  Prepare the voting form (ballot / set of questions), upload it to IPFS, compute commitment.

4.  Define the election details, including duration, options, and the ballot rules $\texttt{ballotMode}$ (see Section ).

5.  Compute a unique process identifier $\texttt{processID}$, which is a 32-byte number derived from the organizer’s Ethereum address, nonce, and the chain ID.

6.  Set security parameters for the <span acronym-label="DKG" acronym-form="singular+short">DKG</span> ceremony (e.g., timeout, minimum number of sequencers).

7.  Submit all this information in a transaction to the [](#\detokenize{{\sf{ElectionRegistry}}}) smart contract (pay tx fees): $$tx_{org} = (\texttt{censusRoot}, ballotCommitment, \texttt{ballotMode}, electionMetadata, \texttt{processID}, dkgParameters).$$

In this phase, key wardens collectively generate the public encryption key.  
Key wardens fetch the process parameters ($\texttt{processID}$, $\texttt{ballotMode}$, $\texttt{censusRoot}$) from the process management smart contract and participate in a <span acronym-label="DKG" acronym-form="singular+short">DKG</span> protocol before the timeout set by the organizer expires. If the minimum number of contributions is reached, the public encryption key $\texttt{encryptionKey}$ is derived and made available on-chain. This ensures that no single party controls the secret key, and that decryption later requires threshold participation (give more details).  

In this phase, voters cast their ballots and send them to the sequencers, who collect and process them.  
**(a) Vote casting.** To cast a ballot, a voter does the following:

1.  Select a sequencer.

2.  Retrieve their census membership proof $\texttt{censusProof}$ to prove eligibility.

3.  Fetch parameters $\texttt{encryptionKey}$, $\texttt{ballotMode}$, and $\texttt{processID}$ from the [](#\detokenize{{\sf{ElectionRegistry}}}) smart contract.

4.  Select their ballot choice $\texttt{ballot}$ according to the rules of $\texttt{ballotMode}$.

5.  Sample fresh randomness $k \in \ensuremath{\mathbb{F}}$ and encrypt the ballot using $\texttt{encryptionKey}$: $$\label{eq-ciphertext}
                \texttt{encryptedBallot}= \hyperlink{\detokenize{{\sf{Enc}}}}{{\sf{Enc}}}_{\texttt{encryptionKey}}(\texttt{ballot}; k).$$

6.  Use their Ethereum address $\texttt{address}$ and the previous $k$ to compute a unique vote identifier: $$\label{eq-voteid}
                \texttt{voteID}= \hyperlink{\detokenize{{\sf{MultiMiMC7}}}}{{\sf{MultiMiMC7}}}(\texttt{processID}\:||\:\texttt{address}\:||\:k).$$

7.  Use the from Section  to generate a ZK-SNARK proof to prove that Eqs.  are correctly computed and that $\texttt{ballot}$ satisfies the ballot protocol rules according to $\texttt{ballotMode}$: $$\begin{aligned}
            \texttt{voteProof}= & \hyperlink{\detokenize{{\sf{P.Prove}}}}{{\sf{P.Prove}}}(
                \hyperlink{\detokenize{{\sf{BallotCircuit}}}}{{\sf{BallotCircuit}}},
                {\sf{witness}}= (\texttt{ballot}, k), 
                {\sf{PI}}= (\texttt{processID}, \texttt{ballotMode},\\
                &\texttt{encryptionKey}, \texttt{address}, \texttt{weight}, \texttt{encryptedBallot}, \texttt{voteID})).
            
    \end{aligned}$$

8.  Sign the vote identifier with their Ethereum secret key ${\sf{sk}^{}}$ to authenticate the vote and ensure that was cast by a legitimate voter: $$\texttt{signature}= \hyperlink{\detokenize{{\sf{S.Sign}}}}{{\sf{S.Sign}}}_{{\sf{sk}^{}}}(\texttt{voteID}).$$

9.  Submit the package $$\texttt{vote}= [\texttt{processID}, \texttt{voteID}, \texttt{encryptedBallot}, \texttt{censusProof}, \texttt{voteProof}, \texttt{signature}]$$ to the chosen sequencer.

**(b) Vote batching.** Upon receiving votes, a sequencer does the following:

1.  Retrieve election identifier $\texttt{processID}$, current state root $\texttt{stateRoot}$, and census root $\texttt{censusRoot}$ from the [](#\detokenize{{\sf{ElectionRegistry}}}) smart contract and the associated data from the Ethereum data blobs.

2.  Upon receiving a vote $$\texttt{vote}_i = [\texttt{processID}, \texttt{voteID}, \texttt{encryptedBallot}, \texttt{censusProof}, \texttt{voteProof}, \texttt{signature}],$$ extract the voter’s public key ${\sf{pk}^{}}_i = \hyperlink{\detokenize{{\sf{S.ExtractPublicKey}}}}{{\sf{S.ExtractPublicKey}}}(\texttt{signature})$.

3.  For each $\texttt{vote}_i$ received, use from Section  to generate a proof $$\begin{aligned}
            \texttt{authenticationProof}_i = & \hyperlink{\detokenize{{\sf{P.Prove}}}}{{\sf{P.Prove}}}(\hyperlink{\detokenize{{\sf{VerifierCircuit}}}}{{\sf{VerifierCircuit}}}, 
            {\sf{witness}}= (\texttt{ballotProof}, \texttt{weight}, \texttt{censusProof}, \texttt{signature}),\\
            & {\sf{PI}}= (\texttt{processID}, \texttt{ballotMode}, \texttt{encryptionKey}, \texttt{encryptedBallot}, \texttt{voteID}, \\
            & \texttt{censusRoot}, {\sf{pk}^{}})).
        
    \end{aligned}$$ This proof ensures that the voter’s `voteProof`, the `signature`, and the `censusProof` are all valid.

4.  Batch a set of $n$ proofs $\{\texttt{authenticationProof}_i\}_{i = 1}^n$ and batch verify them together using from Section : $$\begin{aligned}
            \texttt{aggregationProof}= &\hyperlink{\detokenize{{\sf{P.Prove}}}}{{\sf{P.Prove}}}(\hyperlink{\detokenize{{\sf{AggregationCircuit}}}}{{\sf{AggregationCircuit}}}, 
                            {\sf{witness}}= (\{\texttt{authenticationProof}_i\}_{i = 1}^n),\\
                            &{\sf{PI}}= (\texttt{encryptedBallot}, \{\texttt{voteID}_i\}_{i = 1}^n),
                            \{{\sf{pk}^{}}_i\}_{i = 1}^n,
                            \texttt{processID},
                            \texttt{ballotMode},\\
                            &
                            \texttt{encryptionKey},
                            \texttt{censusRoot}
                            ).
        
    \end{aligned}$$ This proof ensures that the public inputs corresponding to the global process parameters ($\texttt{processID}$, $\texttt{ballotMode}$, $\texttt{encryptionKey}$, $\texttt{censusRoot}$) are correct and that all $\texttt{authenticationProof}_i$ are valid.

5.  Prepare the state transition data that will be stored in an Ethereum blob: pack votes/results into a 4096-cell blob .

    - Compute data commitment ${\sf{blobCommitment}}= \hyperlink{\detokenize{{\sf{C.Commit}}}}{{\sf{C.Commit}}}({\sf{blobData}})$.

    - Derive evaluation point ${\sf{evalPoint}}= \hyperlink{\detokenize{{\sf{Poseidon}}}}{{\sf{Poseidon}}}(\texttt{processID}, oldRoot, {\sf{blobCommitment}}).$

    - Prepare polynomial $P$ from ${\sf{blobData}}$.

    - Evaluate $y = P({\sf{evalPoint}})$.

    - Generate opening proof ${\sf{openingProof}}$ from $...$.

    - The following step (circuit) will prove that $y = P({\sf{evalPoint}})$.

6.  Before doing state transitions, we need to prepare the data that will be stored on chain as a blob. Hence, collect xxxx, create commitment. In circuit (next step), we will prove that... .

7.  Finally, prove that all transitions are correct .... with circuit from Section . consistency between data blobs and the on-chain state:

    $$\begin{aligned}
            \texttt{stateProof}= \hyperlink{\detokenize{{\sf{P.Prove}}}}{{\sf{P.Prove}}}(\hyperlink{\detokenize{{\sf{StateTransitionCircuit}}}}{{\sf{StateTransitionCircuit}}}, 
            {\sf{witness}}= (), {\sf{PI}}= ()). 
        
    \end{aligned}$$

8.  Verify each $\texttt{vote}$ submission received by generating a state transition proof (see Section ), ensuring:

    - correct accumulation of encrypted votes via ElGamal’s homomorphic properties,

    - eligibility of voters (via census Merkle proofs),

    - absence of double voting (or correct handling of overwrites via nullifiers),

9.  Submit the updated state root to the smart contract, while the full data are stored in Ethereum blobs.

Sequencers repeat this process until the voting deadline set by the organizer.

Upon receiving a valid transaction, the smart contract does the following checks:

After the voting period expires, $t$ out of $n$ sequencers publish their decryption shares of the election private key. Once the threshold is reached, the election secret key can be reconstructed (on-chain or off-chain), enabling the decryption of the aggregated tally.

Rewards and penalties for sequencers are managed according to their correct participation: sequencers are rewarded proportionally to the number of votes sequenced, and may be slashed for failing to provide a valid decryption share (see Seciton  for details on incentivation mechanisms.)

In this final phase, the organizer/a sequencer computes the tally and publishes the result, together with a proof of its correct computation, on-chain.

1.  Retrieve $\texttt{decryptionKey}$ from ….

2.  ...

3.  Use from Section  to generate a proof $$\begin{aligned}
            \texttt{resultsProof}=  \hyperlink{\detokenize{{\sf{P.Prove}}}}{{\sf{P.Prove}}}(\hyperlink{\detokenize{{\sf{ResultsCircuit}}}}{{\sf{ResultsCircuit}}}, 
            {\sf{witness}}= (...), 
            {\sf{PI}}= (...)).
        
    \end{aligned}$$

The election is considered finalized once the decrypted tally is available on-chain. At this stage, both the election results and the complete integrity of the process are permanently recorded and publicly auditable.

Note that, anyone can verify the correctness of the final results by checking the <span acronym-label="ZK-SNARK" acronym-form="singular+short">ZK-SNARK</span> state proofs and on-chain commitments. Moreover, the combination of the final state root, the decryption of the accumulators, and the publicly verifiable <span acronym-label="ZK-SNARK" acronym-form="singular+short">ZK-SNARK</span> proofs guarantees the integrity of the entire election.

<figure id="fig:protocol-flow">
<embed src="docs/media/00bb4b54d2f53b206d9b064ca9720a4e6a8378c9.pdf" style="width:5.13889in" />
<figcaption>Vocdoni voting process overview. <span>Figure is OUTDATED.</span></figcaption>
</figure>

# Ballot protocol

The ballot protocol provides a unified and parametric way to represent a wide range of voting systems within DAVINCI. Instead of designing a separate circuit for each voting rule, the protocol defines ballots as fixed-length arrays of integers, subject to a small set of configurable parameters. These parameters constrain the values that can appear in each field of the ballot and the aggregate properties of the ballot as a whole. By adjusting these parameters, the same circuit can implement approval voting, ranking, quadratic voting, multiple choice, and many other schemes. In the protocol we refer to the different configurations as the *ballot mode* ($\texttt{ballotMode}$). This abstraction has two key advantages. First, it allows a broad variety of voting systems to be supported with a minimal circuit design, avoiding conditional logic that would otherwise increase constraint counts. Second, it provides a common interface for tallying, since all ballots are aggregated into a single results array regardless of the voting mode.

#### Definition of parameters.

Each ballot is defined as an array of integer values subject to a set of configurable parameters, illustrated in Figure . These parameters are defined as follows:

- `numFields`: the maximum number of fields (i.e., options) in the ballot.

- `minValue`: the minimum value that each field in the ballot can take.

- `maxValue`: the maximum value that each field in the ballot can take.

- `uniqueValues`: a Boolean flag indicating whether all field values must be different (as in ranking systems).

- `costExponent`: the exponent applied when computing the cost of casting votes in a field. This parameter enables quadratic or higher-order voting rules.

- `minValueSum`: the minimum allowed total sum of a ballot, computed as $\sum_{i=1}^{\texttt{numFields}} v_i^{\texttt{costExponent}}$, where $v_i$ are the field values.

- `maxValueSum`: the maximum allowed total sum of a ballot, computed as $\sum_{i=1}^{\texttt{numFields}} v_i^{\texttt{costExponent}}$, where $v_i$ are the field values (e.g., to enforce a budget of credits).

<figure id="fig:ballot-variables">
<embed src="docs/media/00fdfbda18dd1d6607357e31cc0f8f4fac56bbfa.pdf" />
<figcaption>Schematic representation of the parameters that define a ballot in DAVINCI.</figcaption>
</figure>

#### Definition of constraints.

Given a ballot with $n$ fields and each field filled with a value $v_i$ for $i = 1, \dots, n$, we enforce the following constraints (captured in Figure ):

- $\texttt{numFields}= n$,

- If $\texttt{uniqueValues}= \texttt{true}$, then $v_i \neq v_j$ for all $i\neq j$.

- $\texttt{minValue}\leq v_i \leq \texttt{maxValue}$ for all $i\in\{1, \dots, n\}$.

- $\texttt{minValueSum}\leq \sum_{i=1}^n v_i^{\texttt{costExponent}} \leq \texttt{maxValueSum}$.

#### General mechanism.

A ballot is valid if and only if all the above constraints are satisfied. Invalid ballots are rejected at the circuit level and do not contribute to the tally. Valid ballots are aggregated into a results array, where each entry is the sum of all votes cast for the corresponding field across all voters. Voter weights, defined in the census tree (see Section ), are taken into account when computing these sums. By default, all voters have the same weight, but the protocol also supports weighted voting, where different participants may contribute proportionally to their assigned voting power. In this case, `maxValueSum` reflects the maximum weight assigned to each voter, and the ballot and verifier circuits enforce that the correct weight is being used (see Sections  and  for further details).

#### Ballot modes.

Ballot modes correspond to different voting systems, each adjusted with the variables above ballot configurations. For usability, the organizer does not need to set every parameter manually: instead, they simply select one of the predefined ballot modes (e.g., quadratic voting, ranking, approval), each corresponding to a fixed parameter configuration. Some representative modes are shown in Figure , which illustrate the expressiveness of the ballot protocol. For example, in *approval voting*, each field is binary and voters can approve or reject multiple options simultaneously. In *ranking*, fields must form a permutation of the integers from $1$ to $N$, enforcing uniqueness of values. In *quadratic voting*, voters allocate credits across options, and the cost is quadratic in the number of credits used, captured by setting `costExponent`$=2$. Other systems such as single-choice or multiple-choice elections are special cases of the same framework. The figure also illustrates examples of voters’ ballots, with the last column indicating whether each ballot is valid or invalid under the rules of the selected mode.

<figure id="fig:ballot-modes">
<img src="docs/media/2b6d33a21f1fecbb8657ed7053b63abbcd216b95.png" />
<figcaption>Table showing various voting models using different ballot configurations. Each row corresponds to a voting system specified by a fixed configuration of the ballot parameters (<code>numFields</code>, <code>minValue</code>, <code>maxValue</code>, <code>uniqueValues</code>, <code>costExponent</code>, <code>minValueSum</code>, <code>maxValueSum</code>). The table also includes example ballots for each mode, illustrating how the constraints are enforced in practice. The last column indicates whether a ballot is valid (1) or invalid (0) under the rules of the selected mode.</figcaption>
</figure>

# Incentive mechanisms

In this section, we describe/propose incentive mechanisms. However, this is not the only way. Additionally, we should change the word sequencer by key warden wherever applicable.

## The Vodoni token

DAVINCI introduces the Vocdoni token (VOC) as a key element of its decentralized voting ecosystem, playing a crucial role in the protocol’s sustainability. The token serves multiple utility functions that align the incentives of all participants (organizer, key wardens, voters, and sequencers), ensuring the integrity, efficiency, and security of the system. In particular, the token has the following roles.

- *Collateral for sequencers.* Sequencers must stake VOC tokens as collateral to participate. This serves as a safeguard to ensure responsible participation. Misbehavior or failure to meet obligations can result in penalties, including partial or total loss of the stake.

- *Incentive mechanism.* Sequencers earn rewards in VOC tokens based on their contribution to processing valid votes and maintaining the network. Rewards are proportional to the number of valid votes successfully added to the shared state.

- *Payment for elections.* Organizers pay fees in VOC tokens to create and manage elections. These fees depend on factors such as registry size, voting duration, and desired security level.

- *Governance.* Token holders can participate in the decentralized governance of the project, influencing protocol upgrades, ecosystem development, and other initiatives. This ensures that the project evolves in a transparent, community-driven manner.

## Economics for organizers

Organizers cover the costs of elections in VOC tokens. The total cost combines four components: $${\sf{totalCost}}= {\sf{baseCost}}+ {\sf{capacityCost}}+ {\sf{durationCost}}+ {\sf{securityCost}},$$ where

- ${\sf{baseCost}}$ is a fixed setup fee, independent of the election duration or security level. It is calculated as $${\sf{baseCost}}= {\sf{fixedCost}}+ {\sf{maxVotes}}\cdot p,$$ where ${\sf{fixedCost}}$ is a protocol-defined fee, ${\sf{maxVotes}}$ the maximum number of votes, and $p$ a linear factor. This portion is not reimbursable and always rewarded to sequencers.

- ${\sf{capacityCost}}$ accounts for limited sequencer capacity. That is, is models the cost of reserving space for voting events relative to the number of available sequencers, number of voting events running, and the maximum number of voters. Costs rise non-linearly as available capacity decreases as $$k_1 \cdot \left( \frac{{\sf{totalVotingProcesses}}}{{\sf{totalSequencers}}- {\sf{usedSequencers}}+ \epsilon} \cdot {\sf{maxVotes}}\right)^a$$ with $k_1$ a scaling factor, ${\sf{totalVotingProcesses}}$ the number of elections running, ${\sf{totalSequencers}}$ the number of registered sequencers, ${\sf{usedSequencers}}$ the number of sequencers handling other elections, $\epsilon$ a small constant to avoid division by zero, and $a$ an exponent controlling non-linearity.

- ${\sf{durationCost}}$ grows with the length of the voting period, scaled non-linearly with the formula $$k_2 \cdot {\sf{processDuration}}^b,$$ where ${\sf{processDuration}}$ is measured in hours, $k_2$ is a scaling factor, and $b$ controls non-linear growth. Shorter elections are cost-efficient, while longer ones become increasingly expensive.

- ${\sf{securityCost}}$ models the number of sequencers used, growing exponentially with diminishing returns: $$k_3 \cdot e^{c \left( \frac{{\sf{numSequencers}}}{{\sf{totalSequencers}}} \right)^d},$$ where $k_3$ is a scaling factor, $c$ controls the steepness, ${\sf{numSequencers}}$ is the number of sequencers needed in the election, ${\sf{totalSequencers}}$ the number of available sequencers, and $d$ adjusts the non-linearity as the number of sequencers increases.  
  Before ${\sf{totalSequencers}}$ was defined as the number of *registered* sequencers and here it means the number of *available* sequencers. Is it assumed to always be the same?

To avoid impractical scenarios, the following two constraints are enforced:

- If ${\sf{processDuration}}> {\sf{maxDuration}}$, then ${\sf{totalCost}}= \infty$.

- If ${\sf{numSequencers}}> {\sf{totalSequencers}}$, then ${\sf{totalCost}}= \infty$.

#### Reimbursements.

Organizers initially reserve resources for all eligible voters, assuming maximum turnout. Since this rarely occurs, unused portions may be reimbursed. The reimbursement is defined as $${\sf{reimbursement}}= {\sf{totalCost}}- {\sf{totalReward}}- {\sf{baseCost}},$$ where ${\sf{totalReward}}$ is the actual amount distributed to sequencers based on their participation. This mechanism ensures organizers do not overpay for unused capacity, while sequencers are still compensated for committed resources.

## Economics for sequencers

Sequencers must stake VOC in the sequencer registry smart contract to participate. Rewards are based on:

- The number of votes included in the shared state.

- The number of vote rewrites (either overwrites or re-encryptions). Rewrites enhance receipt-freeness and are incentivized, though limited by protocol constants.

- The ratio of processed to non-processed votes relative to the maximum allowed voters.

The reward function for the $i$-th sequencer is $${\sf{sequencerReward}}_i = R \cdot \left( \frac{{\sf{votes}}_i}{{\sf{maxVotes}}} \right) + W \cdot \left( \frac{{\sf{voteRewrites}}_i}{{\sf{totalRewrites}}} \right),$$ subject to the constraints $$\frac{{\sf{voteRewrites}}_i}{{\sf{votes}}_i} \leq T, \quad {\sf{totalReward}}= R + W, \quad R > W,$$ where $T$ is the maximum allowed ratio of rewrites to votes. Rewards prioritize new votes over rewrites, ensuring sequencers cannot maximize profits by simply re-encrypting existing ballots.

#### Penalties.

Sequencers failing to provide required decryption shares or misbehaving face slashing penalties as $${\sf{slashedAmount}}_i = s \cdot {\sf{stakedCollateral}}_i,$$ where $0 \leq s \leq 1$ is a slashing coefficient. This ensures accountability and discourages free-riding.

## Summary and remarks

The cost model combines four components: base, capacity, duration, and security. It ensures small elections are cost-efficient, large or resource-intensive elections incur higher costs, and impractical setups are excluded. Organizers aim to minimize costs, while sequencers seek to maximize rewards — a natural tension that can be modeled as a strategic game. Analyzing this equilibrium is left for future work. Move this to Section ?

# Analysis

The DAVINCI protocol was designed according to a set of guiding principles: cryptography is the sole source of truth; no single entity must be trusted; the system should be modular, open source, and resilient; and it should remain scalable, automated, and accessible to a wide range of users. Building on these principles, we now discuss the concrete security properties of the protocol, followed by implementation details and performance results. – This whole section is still \[WIP\].  

## Security discussion

Based on the above principles, the protocol provides a number of concrete security properties that ensure the integrity, confidentiality, and verifiability of voting events. In what follows we discuss how DAVINCI achieves these properties, with particular emphasis on receipt-freeness, privacy, unlinkability, and robustness against quantum threats.

#### Receipt-freeness.

Receipt-freeness prevents voters from proving to others how they voted, thereby mitigating coercion and vote-buying. In DAVINCI this is achieved through re-encryption, ballot overwrites, and randomized state updates.

- *Ballot re-encryption*: since our encryption scheme supports re-randomization, that is, a ciphertext can be refreshed with new randomness without changing the underlying message, sequencers exploit this by re-encrypting the received ballots before committing them to the state Merkle tree, making it computationally infeasible to link a submitted ciphertext with the stored one (give details of what does *computationally infeasible* mean here).

- *Handling receipts*: because ballots are re-randomized, voters cannot generate a receipt by revealing the randomness $r$ used in encryption, since the ciphertext on-chain no longer corresponds to their $r$. This blocks vote-selling and coercion.

- *Overwrites*: voters may cast a new ballot at any time, replacing their earlier submission. This ensures that even if coercion occurs, a voter can subsequently change their vote as many times as desired, preserving their ability to express their true choice. When an overwrite occurs, the sequencer substracts the previous ballot from the subtractive accumulator, adds the new ballot to the additive accumulator, and re-encrypts the updated ballot before storing it in the state tree.

- *Concealing overwrites*: to prevent observers from distinguishing overwrites from routine re-randomizations, sequencers periodically re-encrypt a random subset of stored ballots. This obfuscation ensures that overwrites remain indistinguishable from normal re-randomizations, strengthening receipt-freeness.

#### Privacy.

Ballots remain secret even though encrypted ballots are publicly stored and processed. Ballot secrecy is preserved through ElGamal encryption, which allows votes to be aggregated without decryption. Encrypted ballots are stored in public repositories (e.g., Ethereum blobs). Because of <span acronym-label="DKG" acronym-form="singular+short">DKG</span> sequencers cannot decrypt individual ballots themselves. The protocol does not reveal the ballot but it does reveal if someone has voted or not.

#### Quantum resistance.

Quantum computers threaten discrete-logarithm-based cryptography such as ECDSA and ElGamal. For this reason, DAVINCI is designed in a modular way that would allow to migrate to post-quantum primitives in the longer term. For example,use CRYSTALS-Dilithium, Falcon, or Rainbow, for signature schemes, Brakerski-Gentry-Vaikuntanathan (BGV) or Brakerski/Fan-Vercauteren (BFV) which are lattice-based homomorphic encryption schemes, and ZK-STARKs for post-quantum zero-knowledge proofs. Add citations to protocols.

#### Data availability.

Ballots and state updates are stored in Ethereum blobs. Since these blobs may eventually be pruned from the blockchain, ensuring long-term data availability is an open problem. Possible solutions include decentralized storage networks or dedicated data-availability layers. This remains an active area of research.

#### End-to-end verifiability.

Voters can check that their own ballot was included correctly, while anyone can audit the entire process to verify the final tally. Every voter can verify their ballot from casting to result computation (individual verifiability). Additionally, any third party can audit the election data to confirm results (universal verifiability) and verify that each vote comes from a uniquely registered voter (eligibility verifiability). Transparent cryptographic mechanisms make this possible.

## Implementation

The system is modular, consisting of interchangeable components that can be rearranged or integrated with external systems via adaptable interfaces. This allows for redundancy, flexibility, and seamless integration with third-party applications, exemplified by our voting-as-a-service APIs. Vocdoni’s voting platform (App) is open source, universally available and user-friendly. The interface is intuitive for all users, including those less familiar with technology, and accommodates voters that use assistive technologies like screen readers. By releasing our code openly, we invite anyone to audit and contribute, enhancing security and fostering community engagement. Transparency prevents security through obscurity and accelerates innovation. We minimize human intervention through smart contracts and cryptographic protocols, reducing costs and human error. Automation ensures consistent operation and frees resources for voter support and auditing. Add link to repositories and details of the software used.

#### Circuits.

- Circuit 1: circom/snarkJS, $\sim 53.000$ constraints.

- Circuit 2: gnark, $\sim 3.1$ million constraints.

- Circuit 3: gnark, 40.000 $\times$ (number of votes) constraints.

- Circuit 4: gnark, $\sim 16$ million constraints.

#### MPC for CRS.

Explain the trusted setup ceremony.

## Performance evaluation

Work in progress.

# Conclusions

# Future work

- Voter: they do circuit1 + circuit2 themselves (instead of the sequencer doing circuit2).

- Post-quantum.

- Support to xxx.

# Acknowledgments

The authors would like to thank the following reviewers and contributors for their valuable feedback and support: all team members from the Vocdoni association, Jordi Baylina (Iden3 and Polygon), Adrià Massanet (Privacy Scaling Explorations, Ethereum Foundation), Arnaucube (0xPARC), Alex Kampa (AZKR), Javier Herranz (Polytechnic University of Catalonia), Jordi Puiggali (Secrets Vault), and Carla Ràfols (Pompeu Fabra University).

# Cryptographic primitives

In this section, we present the cryptographic primitives used in the protocol described in Section . We first introduce elliptic curves as the underlying algebraic setting, and then describe the following building blocks, each tied to a specific role in the system: hash functions and Merkle trees for commitments to structured data; digital signatures for voter authentication; encryption schemes for ballot confidentiality; <span acronym-label="DKG" acronym-form="singular+short">DKG</span> for decentralizing trust in the election keys; and zero-knowledge proofs (<span acronym-label="ZK-SNARK" acronym-form="plural+short">ZK-SNARKs</span>) for verifiability of computations. For each primitive, we also specify the concrete choice of parameters used.

## Elliptic curves

DAVINCI relies on multiple elliptic curves to ensure interoperability with Ethereum, compatibility with available cryptographic primitives, and efficient in-circuit operations. On the one hand, SECP256K1 (Brown 2010) is used because Ethereum public keys are elements of this curve. As DAVINCI assumes each voter holds a standard Ethereum address, cryptographic operations such as digital signatures and identity verification rely on SECP256K1 to match the Ethereum ecosystem. On the other hand, BN254 (Wood et al. 2014) is chosen because it is the curve supported by Ethereum’s precompiled contracts for ZK proof verification, which makes it the optimal choice for verifying SNARK proofs on-chain with minimal gas cost. Then, BabyJubjub (Bellés-Muñoz et al. 2021) is used as an inner curve for elliptic curve operations within arithmetic circuits. Finally, BLS12-377 (Bowe et al. 2020) and BW6-761 (El Housni and Guillevic 2020) are used to enable recursive proof composition. More specifically, BLS12-377 acts as the inner curve for constructing proofs, while BW6-761 serves as the outer curve that verifies those proofs within larger ZK-SNARK circuits. This pairing enables succinct verification and composability of ZK-SNARKs within other ZK-SNARKs, which we use for DAVINCI’s aggregation and state transition logic. Below, we give the details of these curves.

#### Parameters.

- $p = \tt{\hspace{0.04cm}0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f}$ (256-bit prime).

- $q = \tt{\hspace{0.01cm}0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141}$ (256-bit prime).

- $r = \tt{0x30644e72e131a029b85045b68181585d97816a916871ca8d3c208c16d87cfd47}$ (254-bit prime).

- $s = \tt{\hspace{0.03cm}0x30644e72e131a029b85045b68181585d2833e84879b9709143e1f593f0000001}$ (254-bit prime).

- $t = \tt{\hspace{0.07cm}0x60c89ce5c263405370a08b6d0302b0bab3eedb83920ee0a677297dc392126f1}$ (251-bit prime).

- $u = \tt{0x122e824fb83ce0ad187c94004faff3eb926186a81d14688528275ef8087be41707ba638e584e9190}$

- $\tt{3cebaff25b423048689c8ed12f9fd9071dcd3dc73ebff2e98a116c25667a8f8160cf8aeeaf0a437e69}$

- $\tt{13e6870000082f49d00000000008b}$ (761-bit prime).

- $v = \tt{0x01ae3a4617c510eac63b05c06ca1493b1a22d9f300f5138f1ef3622fba094800170b5d4430000000}$

- $\tt{8508c00000000001}$ (377-bit prime).

- $w = \tt{0x12ab655e9a2ca55660b44d1e5c37b00159aa76fed00000010a11800000000001}$ (253-bit prime).

#### Elliptic curve groups.

- SECP256K1 curve: $\ensuremath{{E}^{\text{\tiny \sf SEC}}}/\ensuremath{\mathbb{F}}_p$ defined by equation $\ensuremath{{E}^{\text{\tiny \sf SEC}}}: y^2 = x^3 + 7$, with group $\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf SEC}}}$ of prime order $q$.

- BN254 curve: $\ensuremath{{E}^{\text{\tiny \sf BN}}}/\ensuremath{\mathbb{F}}_r$ defined by equation $\ensuremath{{E}^{\text{\tiny \sf BN}}}: y^2 = x^3 + 3$, with subgroups $\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BN}}}_1, \ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BN}}}_2$ of prime order $s$, and an efficiently computable pairing $e:\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BN}}}_1\times\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BN}}}_2 \rightarrow \ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BN}}}_T,$ where $\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BN}}}_T \subset \ensuremath{\mathbb{F}}_{s^{12}}$ and has order $s$.

- BabyJubjub curve: $\ensuremath{{E}^{\text{\tiny \sf BJ}}}/\ensuremath{\mathbb{F}}_s$ defined by equation $\ensuremath{{E}^{\text{\tiny \sf BJ}}}: 168700 x^2 + y^2 = 1 + 168696 x^2y^2$, with subgroup $\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BJ}}}$ of prime order $t$.

- BW6-761 curve: $\ensuremath{{E}^{\text{\tiny \sf BW}}}/\ensuremath{\mathbb{F}}_u$ defined by equation $\ensuremath{{E}^{\text{\tiny \sf BW}}}: y^2 = x^3 - 1$, with subgroups $\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BW}}}_1, \ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BW}}}_2$ of prime order $v$, and an efficiently computable pairing ${e}:\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BW}}}_1\times\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BW}}}_2 \rightarrow \ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BW}}}_T,$ where $\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BW}}}_T \subset \ensuremath{\mathbb{F}}_{v^{6}}$ and has order $v$ as well.

- BLS12-377 curve: $\ensuremath{{E}^{\text{\tiny \sf BLS}}}/\ensuremath{\mathbb{F}}_v$ defined by equation $\ensuremath{{E}^{\text{\tiny \sf BLS}}}: y^2 = x^3 + 1,$ with subgroups $\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BLS}}}_1, \ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BLS}}}_2$ of prime order $w$, and an efficiently computable pairing ${e}:\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BLS}}}_1\times\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BLS}}}_2 \rightarrow \ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BLS}}}_T,$ where $\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BLS}}}_T \subset \ensuremath{\mathbb{F}}_{w^{12}}$ and has order $w$.

#### Finite fields.

- $\ensuremath{\mathbb{F}}_p$: base field of the SECP256K1 curve.

- $\ensuremath{\mathbb{F}}_q$: scalar field of $\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf SEC}}}$.

- $\ensuremath{\mathbb{F}}_r$: base field of the BN254 curve.

- $\ensuremath{\mathbb{F}}_s$: scalar field of $\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BN}}}_1, \ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BN}}}_2, \ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BN}}}_T$ and base field of the BabyJubjub curve.

- $\ensuremath{\mathbb{F}}_t$: scalar field of $\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BJ}}}$.

- $\ensuremath{\mathbb{F}}_u$: base field of the BW6-761 curve.

- $\ensuremath{\mathbb{F}}_v$: scalar field of $\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BW}}}_1, \ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BW}}}_2, \ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BW}}}_T$ and base field of the BLS12-377 curve.

- $\ensuremath{\mathbb{F}}_w$: scalar field of $\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BLS}}}_1, \ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BLS}}}_2, \ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BLS}}}_T$.

#### Generators.

  
We denote by $\hyperlink{\detokenize{\ensuremath{{G}^{\text{\tiny \sf SEC}}}}}{\ensuremath{{G}^{\text{\tiny \sf SEC}}}}$ the generator of $\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf SEC}}}$ as defined in (Brown 2010), $\hyperlink{\detokenize{\ensuremath{{G}^{\text{\tiny \sf BN}}}}}{\ensuremath{{G}^{\text{\tiny \sf BN}}}}$ the generator of $\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BN}}}_1$ as defined in (Wood et al. 2014), $\hyperlink{\detokenize{\ensuremath{{G}^{\text{\tiny \sf BJ}}}}}{\ensuremath{{G}^{\text{\tiny \sf BJ}}}}$ the generator of $\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BJ}}}$ as defined in (WhiteHat, Bellés, and Baylina 2020), $\hyperlink{\detokenize{\ensuremath{{G}^{\text{\tiny \sf BW}}}}}{\ensuremath{{G}^{\text{\tiny \sf BW}}}}$ the generator of $\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BW}}}_1$ as defined in (Housni, Connor, and Guillevic 2020), and $\hyperlink{\detokenize{\ensuremath{{G}^{\text{\tiny \sf BLS}}}}}{\ensuremath{{G}^{\text{\tiny \sf BLS}}}}$ the generator of $\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BLS}}}_1$ as defined in (Vlasov and hujw77 2020).

- $\hypertarget{\detokenize{\ensuremath{{G}^{\text{\tiny \sf SEC}}}}}{\ensuremath{{G}^{\text{\tiny \sf SEC}}}} = 
          (\tt{0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798,0x483ada7726} \allowbreak
          \rule{1.37cm}{0pt}
          \tt{a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8}).$

- $\hypertarget{\detokenize{\ensuremath{{G}^{\text{\tiny \sf BN}}}}}{\ensuremath{{G}^{\text{\tiny \sf BN}}}}\hspace{0.14cm} = \: (\tt{0x01}, \tt{0x02}).$

- $\hypertarget{\detokenize{\ensuremath{{G}^{\text{\tiny \sf BJ}}}}}{\ensuremath{{G}^{\text{\tiny \sf BJ}}}}\hspace{0.18cm} = 
          \hspace{0.09cm} (\tt{0x0b9feffffffffaaabfffffffffffffffeffffffffffffffffffffffffffffff}, 
          \tt{0x17fffffffff} \\
          \rule{1.37cm}{0pt}
          \tt{ffffffffffffffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141}).$

- $\hypertarget{\detokenize{\ensuremath{{G}^{\text{\tiny \sf BW}}}}}{\ensuremath{{G}^{\text{\tiny \sf BW}}}}\hspace{0.085cm} = 
          \hspace{0.09cm} (\tt{0x1075b020ea190c8b277ce98a477beaee6a0cfb7551b27f0ee05c54b85f56fc779017ffac15520}\\
          \rule{1.37cm}{0pt}
          \tt{ac11dbfcd294c2e746a17a54ce47729b905bd71fa0c9ea097103758f9a280ca27f6750dd0356133}\\
          \rule{1.37cm}{0pt}      
          \tt{e82055928aca6af603f4088f3af66e5b43d, 0x58b84e0a6fc574e6fd637b45cc2a420f952589884} \\
          \rule{1.37cm}{0pt}
          \tt{c9ec61a7348d2a2e573a3265909f1af7e0dbac5b8fa1771b5b806cc685d31717a4c55be3fb90b6f} \\
          \rule{1.37cm}{0pt}
          \tt{c2cdd49f9df141b3053253b2b08119cad0fb93ad1cb2be0b20d2a1bafc8f2db4e95363)}.$

- $\hypertarget{\detokenize{\ensuremath{{G}^{\text{\tiny \sf BLS}}}}}{\ensuremath{{G}^{\text{\tiny \sf BLS}}}}\hspace{0.07cm} = 
          \hspace{0.06cm}(\tt{0x008848defe740a67c8fc6225bf87ff5485951e2caa9d41bb188282c8bd37cb5cd5481512ffcd3} \\
          \rule{1.37cm}{0pt}
          \tt{94eeab9b16eb21be9ef,0x01914a69c5102eff1f674f5d30afeec4bd7fb348ca3e52d96d182ad44} \\
          \rule{1.37cm}{0pt}
          \tt{fb82305c2fe3d3634a9591afd82de55559c8ea6}).$

## Hash functions

DAVINCI uses different hash functions. On the one side, we use Keccak256 (Bertoni et al. 2011) for Ethereum address derivation, and Poseidon (Grassi et al. 2021), MiMC and MiMC-7 (Albrecht et al. 2016) for arithmetic circuits within zero-knowledge proofs.

#### Keccak256.

Keccak256 is the standard hash function used by Ethereum and is employed in DAVINCI to compress messages for signing and deriving Ethereum addresses from public keys over $\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf SEC}}}$. Keccak256 takes arbitrary-length bitstrings and outputs 256-bit digests: $\hypertarget{\detokenize{{\sf{Keccak}}}}{{\sf{Keccak}}} : \{0,1\}^* \rightarrow \{0,1\}^{256}$. This function is not SNARK-friendly and it is used exclusively in the authentication circuit, where the verification of Ethereum-compatible signatures requires reproducing the original message hash computed by Ethereum clients (see Section ).

#### Poseidon.

Poseidon is a SNARK-optimized hash function designed for efficient implementation inside arithmetic circuits. It is used in DAVINCI for computing commitments, nullifiers, and the state Merkle tree roots. Poseidon is used as $\hypertarget{\detokenize{{\sf{Poseidon}}}}{{\sf{Poseidon}}} : \mathfrak{F}_s \rightarrow \ensuremath{\mathbb{F}}_s$, where $\mathfrak{F}_s$ is the set of tuples of $\ensuremath{\mathbb{F}}_s$-elements of any length, and $\ensuremath{\mathbb{F}}_s$ is the field described in Section .

#### MiMC-7.

Finally, we use functions from the MiMC family. On the one side, MiMC-7 hash function $\hypertarget{\detokenize{{\sf{MiMC}}}}{{\sf{MiMC}}} : \ensuremath{\mathbb{F}}_p \rightarrow \ensuremath{\mathbb{F}}_p$, where $\ensuremath{\mathbb{F}}_p$ is the set of tuples of $\ensuremath{\mathbb{F}}_p$-elements of any length, and $\ensuremath{\mathbb{F}}_p$ is the field described in Section . This hash is used to hash the public inputs of the different circuits and verify the associated proofs more efficiently (see Section  for further details). On the other side, $\hypertarget{\detokenize{{\sf{MultiMiMC7}}}}{{\sf{MultiMiMC7}}}$. Different curves.

For the sake of clarity, in our notation we admit anything as an input of the above hash functions, although it might not be parsed as a sequence of field elements. Any bitstring can be converted to a tuple of field elements, so this does not change the actual working of the hash computation. In this document, it is implied that the proper conversion happens before feeding the input into the actual hash function.

## Merkle trees

**TODO**: Add description of Incremental Merkle trees.  
The DAVINCI protocol uses sparse Merkle Trees (SMTs) as its primary data structure for maintaining off-chain state. Following the construction in (Baylina and Bellés 2019), these are full binary trees of fixed depth in which each leaf encodes a key-value pair and empty leaves are explicitly represented, allowing for both inclusion and non-inclusion proofs. A key property of SMTs is that the hash of each key determines a unique traversal path from the root to the leaf, regardless of insertion order. When inserting a new key, the tree descends until it encounters either an empty node or a leaf. In case of a path collision, the algorithm splits at the first differing bit, creating intermediate nodes accordingly.

In DAVINCI, SMTs are used to represent two core data structures: the census tree, which encodes the list of eligible voters along with their respective voting weights, and the state tree, which encodes the current status of submitted votes. Both trees have fixed depth 64. The census tree is instantiated with the MiMC hash function over the BLS12-377 scalar field, while the state tree uses Poseidon over the BN254 scalar field. Only the root hash of each tree is published on-chain, ensuring verifiability with minimal on-chain storage. To support state transitions and circuit verification, each tree $\sf{MT}^{\sf{}}$ has the following functions associated:

- $\sf{MT}^{\sf{}}.\hypertarget{\detokenize{\sf{Root}}}{\sf{Root}}()$: it returns the current Merkle root of the tree.

- $\sf{MT}^{\sf{}}.\hypertarget{\detokenize{\sf{Insert}}}{\sf{Insert}}(path, \sf{leaf})$: it inserts a new leaf $\sf{leaf}$ at the position defined by the given path.

- $\sf{MT}^{\sf{}}.\hypertarget{\detokenize{\sf{Update}}}{\sf{Update}}(\sf{leaf}_{old}, \sf{leaf})$: it updates an existing leaf in the tree.

- $\sf{MT}^{\sf{}}.\hypertarget{\detokenize{\sf{MembershipProof}}}{\sf{MembershipProof}}(\sf{leaf})$: it returns a Merkle proof of inclusion for the given leaf.

- $\sf{MT}^{\sf{}}.\hypertarget{\detokenize{\sf{NonMembershipProof}}}{\sf{NonMembershipProof}}(\sf{leaf})$: it returns a proof that the given leaf is not included in the tree.

- $\sf{MT}^{\sf{}}.\hypertarget{\detokenize{\sf{Verify}}}{\sf{Verify}}(\sf{leaf}, proof, root)$: it verifies that the given proof corresponds to the claimed root and leaf.

These functions are used by sequencers to construct proofs that certify the validity of state transitions. In particular, they allow for off-chain state evolution that is independently verifiable on-chain and within ZK circuits. Additional details on the structure of the census and state trees, as well as the encoding of their leaves, are provided in Sections  and .

## Commitment schemes

Description of KZG (Kate, Zaverucha, and Goldberg 2010) with SRS **\[add link to Ethereum’s BLS12-381 SRS\]**, $\hypertarget{\detokenize{{\sf{C.Commit}}}}{{\sf{C.Commit}}}()$, and $\hypertarget{\detokenize{{\sf{C.Verify}}}}{{\sf{C.Verify}}}()$.  
Original methods: <span id="\detokenize{{\sf{C.Setup}}}"></span>, <span id="\detokenize{{\sf{C.Open}}}"></span>, <span id="\detokenize{{\sf{C.VerifyPoly}}}"></span>, <span id="\detokenize{{\sf{C.CreateWitness}}}"></span>, <span id="\detokenize{{\sf{C.VerifyEval}}}"></span>, <span id="\detokenize{{\sf{C.Prove}}}"></span>, <span id="\detokenize{{\sf{C.Verify}}}"></span>.

## Digital signature schemes

  
DAVINCI uses the elliptic curve digital signature algorithm (ECDSA) (Johnson, Menezes, and Vanstone 2001) over the SECP256K1 curve to ensure compatibility with standard Ethereum wallets. Verification of ECDSA signatures is performed inside zero-knowledge proofs using a specialized circuit that emulates SECP256K1 arithmetic. This approach is necessary because SECP256K1 is defined over a 256-bit prime field that differs from the native field used in the ZK-SNARK circuit (see Section for more details). Below, we describe the algorithms, which follow the standard ECDSA protocol. (The output of the hash does not match – check where variables live.)

## Encryption schemes

To preserve ballot secrecy while enabling tallying, DAVINCI employs a threshold variant of the ElGamal cryptosystem instantiated over the BabyJubjub curve (Sutikno, Surya, and Effendi 1998). This scheme offers two properties crucial for the protocol: *additive homomorphism*, which allows the aggregation of encrypted votes without decryption, and *re-encryption*, which enables ciphertext randomization without altering the underlying plaintext. Together, these properties allow sequencers to tally votes while preventing voters from producing receipts that could be used for coercion or vote selling. The corresponding public key is generated collectively by the sequencers via the distributed key generation protocol described in Section , ensuring that no single entity can decrypt ballots unilaterally.

#### Encryption and decryption.

Given a message $m$, the ElGamal encryption algorithm maps it into a group element $M$ of $\ensuremath{{\ensuremath{\mathbb{G}}}^{\text{\tiny \sf BJ}}}$ and outputs a ciphertext as follows:

Since the plaintext message space is typically small, recovering $m$ from $M$ is efficient: although the mapping $m \mapsto M$ is not generally invertible, it can be reversed by brute-force search or optimized techniques such as baby-step giant-step (Blake, Seroussi, and Smart 1999).

#### Homomorphic addition and reencryption.

ElGamal encryption is additively homomorphic. Given two ciphertexts $(C_1, C_2)$ and $(C_1', C_2')$, their component-wise addition yields another valid ciphertext $(C_1 + C_1',\, C_2 + C_2')$. The resulting ciphertext decrypts to the sum of the two underlying messages. This property allows sequencers to aggregate encrypted ballots directly. Moreover, to prevent linkability and ensure receipt-freeness, sequencers also re-randomize ciphertexts. Re-encryption exploits this property by adding to a ciphertext an encryption of zero. This operation yields a fresh ciphertext of the same message under new randomness, making it computationally infeasible to link the re-encrypted ballot with the original submission.

In the protocol, re-encryption is applied not only to newly submitted ballots but also to ballots already stored in the state tree. By refreshing the randomness of both new and existing ciphertexts, sequencers ensure that it is indistinguishable whether a ballot has been overwritten or merely re-randomized. This mechanism is essential for guaranteeing receipt-freeness: voters cannot produce a verifiable receipt of their choice, and adversaries cannot detect or prove whether a particular vote has been replaced (see Section ).

## Key generation schemes

To ensure that no single entity controls the decryption key, DAVINCI employs a <span acronym-label="DKG" acronym-form="singular+short">DKG</span> protocol to jointly derive the ElGamal encryption key pair used for ballots encryption (**todocitaton?**). Participants who contribute to the <span acronym-label="DKG" acronym-form="singular+short">DKG</span> ceremony are called *key wardens*, and they are each identified by a unique index $i$. The outcome is a collective public key (`encryptionKey`) that is published on-chain and used by voters to encrypt their ballots, while the corresponding private key is secret-shared among the key wardens. Only a threshold number $t$ out of $n$ key wardens can later collaborate to decrypt the tally. Unlike classical <span acronym-label="DKG" acronym-form="singular+short">DKG</span> protocols where shares are exchanged in the clear, our construction uses encrypted shares and <span acronym-label="ZK-SNARK" acronym-form="singular+short">ZK-SNARK</span> proofs of correctness. This allows the Ethereum smart contract to verify compliance without learning any of the underlying secrets, ensuring both security and verifiability in a fully decentralized setting.

Let $t$ be the threshold parameter and $n$ the number of key wardens, with $t\leq n$. Let $G$ be a generator of the elliptic curve group of order $q$. Each participant $P_i$ runs the following procedure.

The smart contract verifies the encrypted shares.

After collecting valid encrypted shares, each participant $P_j$ can recover their secret share $s_j$ by decrypting all contributions addressed to them:

This approach ensures that the encryption public key is securely generated in a decentralized way, that each key warden learns only their own secret share, and that the correctness of the entire <span acronym-label="DKG" acronym-form="singular+short">DKG</span> procedure is verifiable on-chain. Misbehavior, such as submitting invalid shares, can be detected and penalized through the slashing mechanism enforced by the smart contract (see Section ).

## Zero-knowledge proof systems

Zero-knowledge succinct non-interactive arguments of knowledge (ZK-SNARKs) are a crucial component in ensuring the integrity of the election. Voters generate ZK-SNARK proofs to demonstrate that their encrypted ballots comply with the rules and constraints defined by the election parameters, without revealing any information about their choices. Similarly, sequencers produce proofs to certify the correctness of vote aggregation and state transitions throughout the protocol. <span id="\detokenize{{\sf{P.Prove}}}"></span>(), <span id="\detokenize{{\sf{P.Verify}}}"></span>(proof, PI) – pkey, vkey.

All ZK circuits in DAVINCI are compiled using the Groth16 proof system (Groth 2016), a widely adopted ZK-SNARK construction known for its succinctness, efficient verification, and minimal proof size. Although all circuits rely on the same proving system, they are instantiated with different elliptic curves depending on the cryptographic requirements of each phase. Specifically, the vote validity circuit is compiled over the BN254 curve, the census-related circuit uses BLS12-377, and the aggregation circuit is instantiated over BW6-761. Finally, the last circuit used by the sequencer—responsible for generating the final proof of correct tallying and result—is compiled over BN254 as well, since this is the proof that is verified on-chain by the smart contract using Ethereum’s native precompiles. Further details on the circuits are provided in Section  and a summary of the instantiations can be found in Figure .

<div id="refs" class="references csl-bib-body hanging-indent">

<div id="ref-todocitation" class="csl-entry">

AAAATODOauthor. 9999. “TODOtitle.” [TODOurl](https://TODOurl).

</div>

<div id="ref-albrecht2016mimc" class="csl-entry">

Albrecht, Martin, Lorenzo Grassi, Christian Rechberger, Arnab Roy, and Tyge Tiessen. 2016. “MiMC: Efficient Encryption and Cryptographic Hashing with Minimal Multiplicative Complexity.” In *Advances in Cryptology – ASIACRYPT 2016*, edited by Jung Hee Cheon and Tsuyoshi Takagi, 191–219. Berlin, Heidelberg: Springer Berlin Heidelberg.

</div>

<div id="ref-baylina2019sparse" class="csl-entry">

Baylina, Jordi, and Marta Bellés. 2019. “Sparse Merkle Trees.” <https://docs.iden3.io/publications/pdfs/Merkle-Tree.pdf>.

</div>

<div id="ref-belles2021twisted" class="csl-entry">

Bellés-Muñoz, Marta, Barry Whitehat, Jordi Baylina, Vanesa Daza, and Jose Luis Muñoz-Tapia. 2021. “Twisted Edwards Elliptic Curves for Zero-Knowledge Circuits.” *Mathematics* 9 (23). <https://doi.org/10.3390/math9233022>.

</div>

<div id="ref-bertoni2011keccak" class="csl-entry">

Bertoni, Guido, Joan Daemen, Michal Peeters, and Gilles Van Assche. 2011. “The KECCAK SHA-3 Submission.” <https://keccak.team/files/Keccak-submission-3.pdf>.

</div>

<div id="ref-blake1995elliptic" class="csl-entry">

Blake, Ian F., G. Seroussi, and N. P. Smart. 1999. *Elliptic Curves in Cryptography*. USA: Cambridge University Press.

</div>

<div id="ref-bowe2020zexe" class="csl-entry">

Bowe, Sean, Alessandro Chiesa, Matthew Green, Ian Miers, Pratyush Mishra, and Howard Wu. 2020. “ZEXE: Enabling Decentralized Private Computation.” In *2020 IEEE Symposium on Security and Privacy, SP 2020, San Francisco, CA, USA, May 18-21, 2020*, 947–64. IEEE. <https://doi.org/10.1109/SP40000.2020.00050>.

</div>

<div id="ref-brown2010sec" class="csl-entry">

Brown, Daniel R. L. 2010. “SEC 2: Recommended Elliptic Curve Domain Parameters. In: Standards for Efficient Cryptography 2 (SEC 2).” <https://www.secg.org/sec2-v2.pdf>.

</div>

<div id="ref-eip4844" class="csl-entry">

Buterin, Vitalik, Dankrad Feist, Diederik Loerakker, George Kadianakis, Matt Garnett, Mofi Taiwo, and Ansgar Dietrichs. 2022. “EIP-4844: Shard Blob Transactions, Ethereum Improvement Proposals, No. 4844, \[Online Serial\].” <https://eips.ethereum.org/EIPS/eip-4844>.

</div>

<div id="ref-canetti2001universally" class="csl-entry">

Canetti, Ran. 2001. “Universally Composable Security: A New Paradigm for Cryptographic Protocols.” In *Proceedings 42nd IEEE Symposium on Foundations of Computer Science*, 136–45. <https://doi.org/10.1109/SFCS.2001.959888>.

</div>

<div id="ref-elhousni2020optimized" class="csl-entry">

El Housni, Youssef, and Aurore Guillevic. 2020. “Optimized and Secure Pairing-Friendly Elliptic Curves Suitable for One Layer Proof Composition.” In *Cryptology and Network Security*, edited by Stephan Krenn, Haya Shulman, and Serge Vaudenay, 259–79. Cham: Springer International Publishing.

</div>

<div id="ref-gennaro2013quadratic" class="csl-entry">

Gennaro, Rosario, Craig Gentry, Bryan Parno, and Mariana Raykova. 2013. “Quadratic Span Programs and Succinct NIZKs Without PCPs.” In *Annual International Conference on the Theory and Applications of Cryptographic Techniques*, 626–45. Springer.

</div>

<div id="ref-grassi2021poseidon" class="csl-entry">

Grassi, Lorenzo, Dmitry Khovratovich, Christian Rechberger, Arnab Roy, and Markus Schofnegger. 2021. “Poseidon: A New Hash Function for Zero-Knowledge Proof Systems.” In *30th USENIX Security Symposium (USENIX Security 21)*, 519–35.

</div>

<div id="ref-groth2016size" class="csl-entry">

Groth, Jens. 2016. “On the Size of Pairing-Based Non-Interactive Arguments.” In *Annual International Conference on the Theory and Applications of Cryptographic Techniques*, 305–26. Springer.

</div>

<div id="ref-eip3026" class="csl-entry">

Housni, Youssef El, Michael Connor, and Aurore Guillevic. 2020. “EIP-3026: BW6-761 Curve Operations \[DRAFT\], Ethereum Improvement Proposals, No. 3026, \[Online Serial\].” <https://eips.ethereum.org/EIPS/eip-3026>.

</div>

<div id="ref-johnson2001ecdsa" class="csl-entry">

Johnson, Don, Alfred Menezes, and Scott Vanstone. 2001. “The Elliptic Curve Digital Signature Algorithm (ECDSA).” *Int. J. Inf. Secur.* 1 (1): 36–63. <https://doi.org/10.1007/s102070100002>.

</div>

<div id="ref-kate2010constant" class="csl-entry">

Kate, Aniket, Gregory M Zaverucha, and Ian Goldberg. 2010. “Constant-Size Commitments to Polynomials and Their Applications.” In *International Conference on the Theory and Application of Cryptology and Information Security*, 177–94. Springer.

</div>

<div id="ref-merkle1987digital" class="csl-entry">

Merkle, Ralph C. 1987. “A Digital Signature Based on a Conventional Encryption Function.” In *Conference on the Theory and Application of Cryptographic Techniques*, 369–78. Springer.

</div>

<div id="ref-reuters2024india" class="csl-entry">

Reuters. 2024. “India’s 2024 General Election Sees Record Participation with 642 Million Votes Cast.” <https://www.reuters.com/world/india/india-poll-panel-says-642-mln-voters-cast-ballots-general-election-2024-06-03/>.

</div>

<div id="ref-sutikno1998implementation" class="csl-entry">

Sutikno, S., A. Surya, and R. Effendi. 1998. “An Implementation of ElGamal Elliptic Curves Cryptosystems.” In *IEEE. APCCAS 1998. 1998 IEEE Asia-Pacific Conference on Circuits and Systems. Microelectronics and Integrating Systems. Proceedings (Cat. No.98EX242)*, 483–86. <https://doi.org/10.1109/APCCAS.1998.743829>.

</div>

<div id="ref-eip2539" class="csl-entry">

Vlasov, Alex, and hujw77. 2020. “EIP-2539: BLS12-377 Curve Operations \[DRAFT\], Ethereum Improvement Proposals, No. 2539, \[Online Serial\].” <https://eips.ethereum.org/EIPS/eip-2539>.

</div>

<div id="ref-erc2494" class="csl-entry">

WhiteHat, Barry, Marta Bellés, and Jordi Baylina. 2020. “ERC-2494: Baby Jubjub Elliptic Curve \[DRAFT\], Ethereum Improvement Proposals, No. 2494, \[Online Serial\].” <https://eips.ethereum.org/EIPS/eip-2494>.

</div>

<div id="ref-wood2014ethereum" class="csl-entry">

Wood, Gavin et al. 2014. “Ethereum: A Secure Decentralised Generalised Transaction Ledger.” *Ethereum Project Yellow Paper* 151 (2014): 1–32.

</div>

</div>
