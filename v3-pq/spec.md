# DAVINCI v3-PQ — Post-Quantum Protocol Specification

**Status:** draft v1.2 · 2026-10-20 · **unified Blake3 profile** (supersedes v1.0's
mixed Poseidon2/SHA-256/Blake3 profile) · incorporates the first external design review ·
v2 remains the deployed protocol. Reviewed: three adversarial soundness rounds (protocol
reviewer) + audience-representative sign-off + one external design review; a final
consolidated review gates implementation (Phase 0 of the migration plan).
**Audience:** engineers who already know [DAVINCI v2](https://spec.davinci.vote). This document only
specifies what *changes*. Everything not mentioned here (settlement flow, grace window, blob
verification via the point-evaluation precompile, census origins, sequencer lifecycle, process
registry mechanics) works exactly as in v2 [DAV2].

---

## 1. Why v3, in one paragraph

Every ballot DAVINCI v2 publishes in Ethereum blobs [EIP4844] is an ElGamal ciphertext over
BabyJubjub. Published blob data can be archived by anyone indefinitely, and ElGamal falls to
Shor's algorithm — so a future quantum computer decrypts **past elections retroactively**
("harvest now, decrypt later"). Integrity is less urgent (a settled chain cannot be rewritten
under Ethereum's finality assumptions), but **ballot privacy must be post-quantum today**.
v3-PQ removes the quantum-vulnerable primitives from the ballot *confidentiality* path: no
shared-key homomorphic encryption, no pairings, no DKG, no Groth16. Ballot secrecy rests on
polynomial secret sharing, hashes, STARKs, and one NIST-standardized KEM (a post-quantum
"public-key lockbox" — all such terms are defined plainly in §2.4). The KEM is never
proven inside the voter's circuit (the batch guest performs encapsulations, and rare complaint
proofs perform decapsulations; see §8.5, §9.2). During the hybrid period voter authentication
still *also* uses ECDSA (§11), and the settlement wrapper and KZG blob commitments remain
inherited non-PQ dependencies (§12.5).

### Changes at a glance

| Component | v2 | v3-PQ |
|---|---|---|
| Ballot confidentiality | ElGamal over BabyJubjub (threshold key) | Shamir shares + PRF masks over KEM transport (§3) |
| Ballot proof | Groth16 over BN254 (circom, trusted setup) | Plonky3 STARK over Goldilocks, browser WASM (§6) |
| Election key | DKG / council ceremony (BabyJubjub) | **None.** Wardens register ML-KEM keys (§4) |
| Tally | Threshold decryption + BSGS search | Lagrange interpolation of θ proven warden sums (§10) |
| Running tally | Homomorphic ciphertext accumulator | Padded plain-sum accumulator over Goldilocks (§8.4) |
| Silent revoting | Re-encryption of stored ciphertexts | Hash-chained opaque slot leaves (§7) + padded accumulator |
| Revotes | Slot overwrite + ciphertext subtraction | One-live-chain packages + revocation nullifiers (§5.3) |
| Voter authentication | ECDSA (secp256k1) | Hash-preimage proof in-STARK; `hybrid` verifies **both**; `hybrid-legacy` admits unenrolled voters on ECDSA (§11) |
| CSP credentials | ECDSA | SLH-DSA (SPHINCS+) [FIPS 205] |
| Batch proof | ZisK, verifies Groth16 (BN254 precompiles) | ZisK [ZISK], verifies ballot STARKs (Blake3 precompile) |
| Protocol hash | Poseidon (circuits) + SHA-256 (state) + Keccak (Ethereum) | **Blake3 everywhere the protocol chooses** (§2); keccak/SHAKE/SHA-2 survive only as fixed islands |
| Tally bound | maxValue·maxVoters ≤ 10^12 (BSGS limit) | ≤ 2^61 (field headroom; no search) |

![What changes from v2 to v3-PQ](figures/architecture-delta.svg)

---

## Protocol intuition — read this first

*A plain-English walkthrough of a v3 election, phase by phase, mapped onto the v2 flow you
already know. Every term used loosely here gets a precise definition from §2 onward; the
jargon cheat-sheet is §2.4.*

**Setup.** The organizer creates the election exactly as in v2 — census, ballot rules,
duration. One thing changed: instead of waiting for a key ceremony, the organizer points at a
committee of ν key wardens (say 5, or 16), each of which has already published a post-quantum
"lockbox" public key: anyone can lock a small secret so that only that warden can open it.
There is **no election encryption key** — nothing is generated jointly, and v2's whole DKG
phase is simply gone.

**Casting.** The voter's browser takes each ballot value and splits it into ν puzzle pieces,
one per warden, using the Shamir trick: any θ pieces (the *threshold* — e.g. 3 of 5) fit
together to reconstruct the value, while θ−1 or fewer are pure noise that says nothing at
all. The browser then hides each piece under a one-time mask (a random-looking number added
to it), locks each mask key into the matching warden's lockbox, and attaches a STARK proof —
generated right there in the browser — that the whole construction is consistent: the pieces
encode one valid ballot that follows the election rules, the masks match their commitments,
and the voter is who they claim to be. The published vote (a *package*) is just masked
pieces + locked boxes + commitments. Everything visible is noise; nothing about the choice
can be read from it, now or ever, by anything short of θ wardens cooperating.

**Voting period.** Sequencers collect packages and settle batches with a zkVM proof, as in
v2. The chain maintains one new object: a public **running total** — for each warden, the sum
of all masked pieces addressed to it. Adding masked numbers keeps them masked, so the running
total is public yet unreadable. A revote cancels the voter's previous package through an
unlinkable **nullifier** (same idea as Tornado/Semaphore nullifiers), and the batch proof
subtracts the old package's pieces from the running total. Meanwhile, refreshes keep
re-hashing slot entries so an outside observer still cannot tell who revoted — v2's "silent
revoting", achieved by different means.

**End of election.** After the grace window come two short new phases: first a
**complaint window**, where any warden that finds a broken package — a lockbox that doesn't
open to what was promised — can prove that on-chain and have the package excluded; then the
exclusion list freezes.

![Election timeline: the two new phases before results](figures/timeline.svg)

**Results.** Any θ wardens now each do one job: open all their lockboxes, strip their own
masks off their column of the frozen running total, and publish the resulting **partial
sum** — with a proof that they did exactly that and nothing else. The punchline: those θ
partial sums are θ points on a single polynomial, and that polynomial's value at zero *is*
the exact election result. The smart contract draws the unique curve through the θ points and
reads it at zero — ordinary integer math, done on-chain. No shared-key decryption ever
happens — there is no shared key to decrypt with (each warden only ever opens its own
lockboxes).

![How the tally emerges from θ partial sums](figures/tally-algebra.svg)

What this buys you:
- **There is no *shared* election decryption key.** (Threshold-shared *batch-payload* keys do exist and are reconstructed at tally — §8.5/§10.4 — but no key ever decrypts the ballot aggregate.) Not distributed as an election key, that is —
  it does not exist, and neither does the key-generation ceremony that managed it in v2
  (wardens keep ordinary per-warden lockbox keys, and tally time still has its own
  coordinated ceremony — §10).
- **Harvest-now-decrypt-later is dead below θ wardens.** The published pieces are
  information-theoretic noise; the only cryptography protecting them is the lockboxes
  (ML-KEM) and hashes — both post-quantum.
- **Every step is proof-checked** — browser proof, batch proof, warden proofs — so voters,
  sequencers and wardens are checked, not trusted, for correctness.
- **The tally is exact integer arithmetic.** No decryption failures, no noise budgets, no
  brute-force search at the end.

---

## 2. Notation, parameters and encodings

- $\mathbb{F}$ — the **Goldilocks field**, $p = 2^{64} - 2^{32} + 1$ (the Plonky3 [P3] and ZisK
  native field). All shares, masks and tally arithmetic live here. Canonical encoding of an
  element: 8 bytes little-endian, value < $p$.
- $\nu$ — number of **key wardens**; $\theta$ — tally threshold. **v3.0 supports
  $1 \le \theta \le \nu \le 8$**, enforced at creation and in the pinned profile (DA and
  in-circuit cost are linear in ν — ν=8 halves both vs 16; the protocol structures support
  up to 16, which returns as a future profile once DA/verification optimizations land;
  committee size is unrelated to the 16 *ballot fields*, which stay). Size rosters with the
  availability margin in mind: tolerating $f$ unavailable or faulty wardens through the
  complaint window and tally ceremony needs $f < \theta \le \nu - f$ — an 8-of-8 election
  tolerates none — and ceremony replacements come from the pinned committee, with blinding
  still requiring ≥ 1 honest *accepted dealer*. The complaint-capacity bound (§9.2) depends
  on admitted casts, not ν: fewer wardens means less aggregate proving/archival redundancy,
  so deadlines and hardware budgets must be revalidated per roster size.
- `nf` — active ballot fields, 1..16, as in v2. A ballot is a vector $b_1..b_{16}$; fields
  beyond `nf` are **inactive and MUST be 0** (enforced by the ballot proof; their shares are
  shares of 0).
- **KEM** — ML-KEM-768 [FIPS 203] (ct 1088 B) by default; ML-KEM-512 (ct 768 B) is an allowed
  profile for DA-sensitive deployments — note it still requires pinning a vetted browser
  implementation (the commonly cited WASM wrapper [KEMB] exposes ML-KEM-768 only). One
  *encapsulation* yields `(ct, K)` with a 32-byte shared secret `K`; arbitrary payloads are
  carried KEM-DEM style (encapsulate, derive a wrapping key from `K`, then DEM-encrypt —
  §2.1).
- **Blake3** — standard Blake3 [B3] is **the protocol hash, everywhere the protocol gets to
  choose**: the ballot STARK's Merkle trees and Fiat–Shamir challenger; all in-circuit
  hashing (PRF masks, commitments, voteID, nullifiers — via a re-laid Blake3 AIR section,
  §6); the census tree; the state SMT and the nullifier SMT; `pkgDigest`/`ctsDigest`; and
  every DEM/PRF/key-derivation role through Blake3's standard *keyed*, *derive_key* and
  *XOF* modes (§2.1). Digests are 32 bytes. Rationale: fastest software hash in the browser
  (~1.4 GB/s in WASM; measured on the prototype: proving 3.24 s → 0.69 s, proofs
  544 → 324 KB), a standard-conformant ZisK precompile (`blake3f`) for every guest
  recomputation, and a conservative, long-studied ARX design (§12.4). One hash = one
  implementation to audit on each platform (AIR, guest, browser, warden).
- **Hash islands the protocol cannot choose**, stated plainly: **keccak256** for values
  Solidity contracts must compute (blob evaluation points $z_b$, the v2 processID prefix,
  the origin-3 running registration commitment of §8.2) and for hybrid-mode Ethereum
  addresses; **SHAKE** inside ML-KEM and **SHA-2** inside SLH-DSA (FIPS-fixed internals of
  black-box primitives); **Poseidon2** inside ZisK's own prover (an inherited proof-system
  dependency — framing in §12.4; [POS2]). Poseidon2 and SHA-256 hold **no
  application-level role** in v3-PQ.
- **256-bit values in circuits** (DEM keys, Blake3 digests crossing into Goldilocks
  arithmetic): encoded as **eight 32-bit limbs**, each range-checked < 2^32. Never as four
  64-bit limbs (not injective: $p^4 < 2^{256}$), and never reduced mod $p$.

### 2.1 DEM (authenticated encryption for warden payloads)

Built from Blake3's standard modes, normative for **every protocol payload** (voter→warden is
pure KEM+PRF and needs no DEM; this DEM covers batch payloads, batch-key share wrapping, and
ceremony deliveries):
- **Key separation**: `k_enc = Blake3.derive_key("davinci v3-pq DEM enc key", K)` and
  `k_mac = Blake3.derive_key("davinci v3-pq DEM mac key", K)` — fixed application context
  strings, exactly the standard derive_key mode. `derive_key` creates *separation, not
  entropy*: `K` must be a ≥256-bit KEM secret or CSPRNG secret.
- **Keystream**: keyed-Blake3 **XOF** — `keystream = Blake3.keyed(k_enc, nonce ‖ AAD).xof()`,
  with the counter being the XOF output offset (bounded: payloads < 2^32 blocks, no offset
  wraparound); ciphertext = plaintext ⊕ keystream. An XOF is a seekable output stream, not
  repeated hashing of previous output.
- **Authentication**: encrypt-then-MAC — `tag = Blake3.keyed(k_mac, nonce ‖ AAD ‖ ciphertext)`;
  receivers verify the **full 32-byte tag before releasing any plaintext**.
- **Uniqueness**: `nonce = Blake3(AAD)`; the AAD is the canonical, length-unambiguous
  serialization of a **DEM context** that always includes a purpose tag, the election
  context, the **batch number or ceremony (session, attempt) identifier**, sender and
  recipient — unique per encryption *including retries* (a ceremony restart is a new attempt
  id ⇒ fresh masks, keys and nonces; the same derived key and nonce never encrypt two
  different plaintexts).

Honest label: these are standard Blake3 modes, but their composition is a
**protocol-specific authenticated-encryption construction — not a standardized AEAD**; the
needed assumption is keyed-Blake3's PRF security (§12.4). AES-256-GCM may be used by clients
for unrelated local storage/transport, never as a substitute encoding of protocol payloads.

### 2.2 Domain-separated contexts

Every derived value uses a purpose-tagged context; nothing is derived without one. Purpose
tags map to Blake3 `derive_key` context strings; the tuple itself is serialized canonically
(fixed order, length-prefixed variable fields).

| Purpose | Context contents |
|---|---|
| `pkgCtx` — the package context tuple | `(protocolVersion, chainID, registry, processID, wardenEpoch, voteID)` — the common prefix below |
| `streamCtx(i)` — mask stream for masked shares | `("v3/mask", pkgCtx, recipient i)` — **one keyed XOF stream per (package, warden)**, no field index: `stream_i = Blake3.keyed(K_i, streamCtx(i)).xof()`, 256 bytes of output; field $f$ uses bytes $[16(f{-}1), 16f)$ via the LE128-mod-$p$ rule below. This is a **normative masking definition** — browser, ballot AIR, batch guest and warden implementations must match it bit-exactly (test vectors required) |
| `hCtx(i)` — share/pad commitment | `("v3/hcommit", pkgCtx, recipient i)` |
| `commitCtx` — package commitment | `("v3/pkgcommit", pkgCtx)` — the `ctx` argument of `pkgCommit` (§5.1) |
| `nullCtx` — revocation nullifier | `("v3/null", protocolVersion, chainID, registry, processID)` — **predecessor-only**: `NULL = Blake3(nullCtx ‖ sk ‖ prevPkgDigest)` with `sk` the voter's census-bound secret or `sk_pkg` (§11). Never depends on the successor package, batch, or recipients. |
| `slotCtx` / `refreshCtx` — slot leaves | `"davinci-slot-v3"` / `"davinci-refresh-v3"` (§7) |

The package's mask nonce is its **voteID** — public, unique per package, authenticated, and
independent of the masked values (it derives from the secret `k`, §5.2, before any masking),
so wardens can recompute every `streamCtx` from public data with no circularity. (Earlier
drafts derived one PRF output per *field*; that definition contradicted the in-AIR cost
estimates — ≥16 final keyed computations per warden, 256 at ν=16 — and was replaced by the
single per-warden stream above, which needs only one context block plus four 64-byte XOF
output blocks per warden.)

**Byte→field mapping (normative).** Blake3 outputs bytes; masks and other derived field
elements are obtained as **LE128 of 16 XOF bytes, reduced mod $p$** — statistical distance
from uniform ≈ $2^{-96}$ *per element* (pseudorandom/nearly uniform — not exact uniformity, and not a whole-election bound). Never `LE64(8 bytes) mod p`: its distance is
≈ $2^{-32}$, which is not.

### 2.3 Protocol parameters

| Parameter | Value | Why |
|---|---|---|
| Share/tally field | Goldilocks $p$ | native in the ballot AIR and ~native u64 in ZisK guests |
| Registry tally cap | `maxValue · maxVoters ≤ 2^61` | per-field tally stays below $p$ with headroom (weights don't change this: each field is individually bounded by `maxValue`) |
| **Integer-cost profile (enforced)** | `nf · maxValue^costExponent < 2^61`, checked by the registry at creation **and** recomputed overflow-safe in the ballot proof | the cost sum must not wrap mod $p$ (e.g. `costExponent=192` would give $2^{192} \equiv 1$); v2 only *advised* this profile — v3 enforces it |
| Warden evaluation points | $x_i = i$, $i \in 1..\nu$ | Shamir positions, pairwise distinct, nonzero |
| Max votes per batch | profile-dependent (§8.6) | in-guest verification cost + the 32-blob batch cap inherited from v2's batch program (see §8.6) |
| Max refreshed slots per batch | 2048, rule as v2 | unchanged |
| `maxRevotesPerVoter` | immutable election parameter | **per-voter revote bound, enforced in-proof** via the private chain counter (§5.3); prevents any single voter from consuming other voters' casting capacity |
| Global admitted-cast capacity | `maxVoters × (1 + maxRevotesPerVoter)` | sizes the complaint budget (§9.2); the `+1` is the initial vote — a revote bound alone is not a cast bound |
| Nullifier tree | Blake3 SMT, depth 256 | full-width nullifiers (no truncation into the 64-bit key space) |
| Ballot STARK profile | Goldilocks, **blowup 32, 18 FRI queries + 16-bit query grinding**, hiding PCS, **Blake3 everywhere** (Merkle/challenger AND the in-AIR hashing section) | ≈106-bit conjectured FRI soundness (§12.4, same heuristic dial as before); chosen verifier-side: −35% in-guest steps and −39% proof size vs blowup-8/34-queries, for ~2.7× prover cost — measured (§8.1). Fallback if browser benchmarks disappoint: blowup 16 / 26 queries. Profile pinned in full by `ballotVKHash`; grinding makes the wasm32 challenger fix (§6) strictly mandatory |
| Commitments | **salted unkeyed Blake3**, domain-separated | hiding from an independent 256-bit CSPRNG salt (or the secret inputs); binding from collision resistance. Keyed-Blake3 is reserved for MACs/PRFs — a MAC is not automatically a hiding/binding commitment |

### 2.4 Terminology for software engineers

Plain definitions, anchored in things an Ethereum engineer already knows. Skim once; the rest
of the document assumes them.

- **KEM** (Key Encapsulation Mechanism; here **ML-KEM**, the standardized Kyber) — a
  public-key *lockbox*: anyone can "encapsulate" against your public key and obtain a fresh
  32-byte shared secret plus a ciphertext; only you (with the private key) can recover that
  secret from the ciphertext. Think of it as the post-quantum replacement for ECDH key
  exchange — except there is no shared-curve math and the two parties never need to be online
  together.
- **PRF** (pseudorandom function) — a keyed hash used as a deterministic random-number
  generator: same key + input ⇒ same output, and without the key the outputs are
  indistinguishable from random. Mentally: `keccak256(key, input)` used the way you'd use a
  seeded RNG. Here PRFs expand a KEM secret into the masks that hide shares.
- **Shamir secret sharing** — split a value into ν pieces by choosing a random polynomial of
  degree θ−1 whose value at x=0 is the secret, and handing out its values at x=1..ν. Any θ
  pieces determine the polynomial (and hence the secret); any θ−1 pieces are statistically
  independent of it — noise, not "hard to crack".
- **Threshold θ-of-ν** — ν parties hold pieces; any θ of them suffice to act (here: tally);
  fewer than θ learn nothing and can block nothing except by being too few.
- **Lagrange interpolation** — given θ points, there is exactly one polynomial of degree
  ≤ θ−1 through them; evaluating it at x=0 recovers a Shamir secret. "Draw the unique curve
  through the points, read it at zero." A few multiplications and additions — cheap even in
  Solidity.
- **STARK** — a zero-knowledge proof system built only from hashes (no trusted setup, no
  elliptic curves, post-quantum). Bigger proofs than Groth16 (hundreds of KB), but
  browser-provable and cheap to verify.
- **AIR** — the constraint system of a STARK: its "circuit".
- **FRI** — the polynomial-checking engine inside a STARK; the reason STARK verification is
  mostly hashing.
- **Hiding PCS** — the polynomial commitment inside the STARK is randomized so the proof
  leaks nothing about private inputs; this is what makes the proof *zero-knowledge* rather
  than merely succinct.
- **Witness** — the prover's private inputs (the ballot, the shares, the keys). Never leaves
  the prover.
- **Nullifier** — a one-way tag published to mark something as spent without revealing what;
  exactly the Tornado Cash / Semaphore pattern. Here: marks a vote package as replaced.
- **Accumulator** (as used here) — just a running sum vector of field elements maintained by
  the batch program. *Not* an RSA or Merkle accumulator.
- **Blake3** — a modern general-purpose hash: ARX design (add–rotate–xor, the ChaCha/BLAKE/
  BLAKE2 lineage; BLAKE was a SHA-3 finalist), extremely fast in software, with standard
  built-in modes for keyed hashing (MAC), key derivation (`derive_key`) and arbitrary-length
  output (XOF). v3's single protocol hash.
- **DEM / AEAD** — symmetric authenticated encryption (ciphertext + tamper-proof tag), the
  AES-GCM role; v3 instantiates it from Blake3's keyed + XOF modes so one hash covers it and
  zk-proofs about it stay cheap (§2.1).
- **Domain separation** — namespacing every hash/PRF input with a purpose tag and context so
  a value from one context can never be replayed in another — the same reason EIP-712 typed
  signing exists (§2.2).
- **Dealer** — a party that generates a secret and distributes shares of it (used in the
  tally ceremony, §10.3).
- **CSPRNG** — a cryptographically secure random generator (`crypto.getRandomValues`,
  `/dev/urandom`); "fresh CSPRNG randomness" means sampled from this, never derived.

---

## 3. The core idea: tally without a shared decryption key

v2 hides a ballot inside a ciphertext and adds ciphertexts homomorphically. v3 hides a ballot
inside **polynomials** and adds polynomials. If you know Lagrange interpolation, you know the
whole trick:

1. For each ballot field value $b$, the voter picks a random polynomial $f$ of degree
   $\theta-1$ with $f(0) = b$, and computes one **share** per warden: $s_i = f(i)$. Any
   $\theta$ shares reconstruct $b$; any $\theta-1$ shares are statistically independent of
   $b$. Plain Shamir [Sha79]: no curves, just polynomial evaluation in $\mathbb{F}$.
2. Shares are never published in the clear. The voter publishes **masked shares**
   $e_i = s_i + \mathrm{mask}_i$, where the masks are sliced from one keyed Blake3 XOF
   stream per warden (§2.2) and the stream key $K_i$ travels to warden $i$ inside an ML-KEM
   ciphertext. To everyone except warden $i$, $e_i$ is a uniformly random field element.
3. Polynomials add: the per-field sum of every active voter's polynomial is itself a
   degree-$(\theta-1)$ polynomial whose value at 0 is the **tally**. So the protocol only
   ever needs to add public field elements. The batch program maintains a public
   **accumulator** $A \in \mathbb{F}^{\nu \times 16}$: coordinate $(i, f)$ is the running
   sum of the masked shares addressed to warden $i$ for field $f$ (plus batch pads, §8.4).
4. At the end, each participating warden decapsulates its KEM ciphertexts, subtracts its pads
   from its row, and publishes its **sum-share** $S_i$ — with a ZisK proof that it did exactly
   that against on-chain-committed data. Lagrange interpolation of any $\theta$ published
   sum-shares at $x=0$ **is** the tally. Exact field arithmetic: no decryption of any
   aggregate, no noise, no discrete-log search.

![How the tally emerges without a shared decryption key](figures/tally-algebra.svg)

(*This section is the intuition; the full computation also handles the exclusion set, batch
pads, and a blinding term — §9–§10.*)

The ballot STARK (§6) makes steps 1–2 trustworthy, the batch proof (§8) step 3, the warden
proofs (§10) step 4. **The zkVM proof chain replaces the homomorphic algebra** — the
structural difference from academic PQ voting designs ([TEV], [PQK]), which obtain the same
guarantee from lattice commitments. (Some public-key encryption is unavoidable for ballots
addressed to offline wardens [IR89]; v3 confines it to KEM transport. Threshold *lattice*
decryption — the known hard part of lattice voting [NOAH] — is avoided entirely: the
threshold lives at the plaintext layer.)

Privacy in one sentence: below $\theta$ colluding wardens, shares are information-theoretically
useless in isolation, and the computational assumptions protecting ballots are ML-KEM, the
PRF/hash, and the zero-knowledge of the STARKs — all post-quantum (full leakage model: §12).

---

## 4. Roles: what changed

- **Organizer, sequencers, provers, observers** — unchanged from v2.
- **Key wardens** no longer run a DKG or hold shares of a secret key. Per *epoch*, each warden
  generates an ML-KEM keypair and calls the **WardenRegistry** contract with: `H(pk)`, a URI
  where the full public key is served (IPFS or HTTPS), and a ZisK **well-formedness proof**
  (the key pair derives from a committed seed and passes an encaps/decaps self-test). The
  registry verifies the proof on-chain. An election pins its committee in `wardenSetHash`
  (config leaf `0x3`, §7): `(ν, θ, epoch, the ν registered H(pk) values)`. A voter's client
  fetches the ν public keys (from their URIs or any sequencer), recomputes each `H(pk)` and
  the set hash, and verifies it against the on-chain value before casting; it refuses to cast
  otherwise. The registry refuses to create an election whose warden set is not fully
  registered. During the election a warden has one standing duty: **continuously archive the
  election's blobs** — EIP-4844 blobs are pruned after ≈18 days, so for any longer election a
  warden that waits until the end cannot expect ordinary Ethereum nodes to still serve the
  history, and missing payload history prevents the tally from completing (§9.3). Wardens MAY
  process incrementally during the voting period (decapsulation and share recovery don't need
  to wait for the end); at the end they run the complaint scan and one tally ceremony
  (§9–§10).
- **Key modes.** *Committee* (lottery over registered operators) and *council*
  (organizer-invited set) map 1:1 from v2 — they only select *which* registered warden keys
  form the set. *Sequencer mode* is the degenerate $\nu = \theta = 1$ case (the sequencer is
  the only warden; ~1 KB per ballot — cheaper than v2). **Locked mode is deferred**: it
  requires an organizer-side share column and a separately reviewed extension of the tally
  equations; it is not part of v3.0.

---

## 5. The ballot package

A vote is one **package**. Its public part goes into blobs; its private part exists only in
the voter's browser — except the *revote metadata* the chosen sequencer needs (§5.4).

![Building a ballot package in the browser](figures/ballot-package.svg)

### 5.1 Public package contents and CanonicalPackage

| # | Field | Size (ν=16, ML-KEM-768) | Description |
|---|---|---|---|
| 1 | `version` | 1 B (`0x03`) | package format version |
| 2 | `processID` | 31 B | as v2 |
| 3 | `voteID` | 8 B LE | §5.2; also the package's mask nonce (§2.2) |
| 4 | `E` | ν·16·8 B = 2,048 B | masked shares, row-major (warden-major, field-minor), canonical LE |
| 5 | `cts` | ν·1,088 B = 17,408 B | ML-KEM ciphertexts, warden order 1..ν |
| 6 | `h` | ν·32 B = 512 B | commitments $h_i = \mathrm{Blake3}(hCtx(i) \,\|\, s_{i,1..16} \,\|\, K_i)$ — salted unkeyed Blake3 per §2.3 (the secret $K_i$ and shares are the hiding material here) |
| 7 | `pkgCommit` | 32 B | $\mathrm{Blake3}(\mathrm{commitCtx} \,\|\, slot \,\|\, pk_{\text{voter}} \,\|\, \mathrm{prevPkgDigest} \,\|\, \mathrm{sharesDigest} \,\|\, t \,\|\, \mathrm{salt})$ — hiding comes from `salt`, an independent **256-bit CSPRNG commitment salt** kept in the package opening (share entropy alone is NOT enough: given θ−1 shares and a candidate ballot, the whole polynomial is determined); `prevPkgDigest = 0^{32}` for a first vote; `t` is the **private chain counter** (§5.3) |
| 8 | `hybridSig` | 65 B or absent | hybrid mode only: ECDSA over `pkgDigest`, Ethereum personal-message format (§11); travels voter→sequencer→batch guest only — **never published** (§5.4) |

`CanonicalPackage` = the concatenation of fields 1–7 exactly as listed (fixed order, fixed
sizes, no framing). **`pkgDigest = Blake3(CanonicalPackage)`** is the package's chain
identity: it is the value stored at the vote-ID leaf, the input to revocation nullifiers, and
what complaints reference. **`sharesDigest = Blake3(h_1 ‖ … ‖ h_ν)`** — despite the name it
binds the shares *through* the per-warden commitments $h_i$ (each AIR-bound to the exact
$(s_i, K_i)$ used in masking, fixed order and count), which is equivalent binding at an
eighth of the in-circuit hashing cost. The ballot STARK (~195 KB at the pinned profile) accompanies the package to
the sequencer but is **not** published in blobs.

### 5.2 Construction (browser, pseudocode)

```text
k         = fresh random scalar (or PRF(sk, "v3/k", processID, counter) in recovery mode)
voteID    = N + trunc63(Blake3("v3/voteid" || processID || address || k))
                                                                 # trunc63 = lowest 63 bits;
                                                                 # N = 2^63 (v2's namespace offset)
for f in 1..nf:
    poly_f = random polynomial, degree θ-1, poly_f(0) = ballot[f]
for f in nf+1..16:  poly_f = random polynomial with poly_f(0) = 0  # inactive fields: shares of 0
s[i][f]   = poly_f(i)                                            # ν shares per field
for i in 1..ν:
    (ct[i], K[i]) = MLKEM.Encaps(pk_warden[i])                   # fresh randomness per package, NEVER reused
    stream = Blake3.keyed(K[i], streamCtx(i)).xof(256 bytes)     # ONE mask stream per warden (§2.2)
    for f in 1..16: e[i][f] = s[i][f] + LE128(stream[16(f-1)..16f]) mod p
    h[i]  = Blake3(hCtx(i) || s[i][1..16] || K[i])
t           = 0 for a first vote; prev.t + 1 for a revote       # private chain counter, ≤ maxRevotesPerVoter
salt        = fresh 256-bit CSPRNG value                         # hiding salt, kept in the opening
sharesDigest = Blake3(h[1] || .. || h[ν])
pkgCommit   = Blake3(commitCtx || slot || pk_voter || prevPkgDigest || sharesDigest || t || salt)
ctsDigest   = Blake3(ct[1] || .. || ct[ν])                       # binds the ciphertext bytes (§6)
proof       = BallotSTARK.prove(...)                             # §6
```

ML-KEM encapsulation costs ~1–2 ms per warden in browser WASM [KEMB]; the dominant client
cost is the STARK (§6). **Freshness warning:** encapsulations are fresh per package and per
attempt — including candidate packages that are never admitted. Reused KEM randomness yields
identical ciphertexts (publicly linkable); actual *pad* reuse (same key AND same stream
context) would publish the difference of two sharings, which interpolates to the ballot
difference. Distinct voteIDs give distinct stream contexts for admitted packages, but
clients must keep freshness across retries and rejected submissions too.

**Client state.** Default: `k`, the polynomials and the KEM randomness are **independent
CSPRNG randomness**, and the client stores the package opening — including the commitment
salt — (needed to revote). Optional *recovery mode* derives them **and the salt** as
`PRF(sk_voter, purpose, processID, counter)` with distinct purpose tags (salt included:
`"v3/salt"`). Any device holding `sk` can then reconstruct past packages. The documented
trade-off: whoever later obtains `sk` can also reconstruct that voter's own historical
ballots. Counter recovery, in the only order that actually works (`pkgDigest` depends on
ballot-dependent data, so it cannot be derived from `sk` and a counter alone): the client
trial-derives `k` and hence `voteID` for counters 0, 1, 2, …; looks each `voteID` up
on-chain (the vote-ID leaf yields the admitted `pkgDigest`); fetches that package's bytes
from the blob archive; re-derives the salt and KEM randomness from the counter's seeds, and
recovers the shares by unmasking the fetched package's public E with the re-derived pad
keys (shares are not derivable from seeds alone); checks the result against the package's
commitments; and checks the nullifier tree to find which package is still live. Gaps from
collision-resamples (§14) are skipped naturally.

### 5.3 Revoting: the one-live-chain rule

v2 overwrote the voter's slot and subtracted the stored ciphertext. v3 has no stored
ciphertext, so the *voter's proof* identifies what to remove:

![Revote lifecycle: the one-live-chain rule](figures/revote-lifecycle.svg)

- Each voter has, per election, a chain of packages $P_0 \to P_1 \to \dots$; exactly one is
  **live**. A revote package $P_{t+1}$ consumes $P_t$: the STARK proves knowledge of $P_t$'s
  opening (same slot, same key) and the nullifier derivation
  $\mathrm{NULL}_t = \mathrm{Blake3}(\mathrm{nullCtx} \,\|\, sk \,\|\, \mathrm{pkgDigest}_t)$, where
  `sk` is the voter's census-bound secret (or the self-chosen `sk_pkg` for unenrolled hybrid
  voters — §11).
- The batch program checks $P_t$ **was admitted and is settled**: an inclusion proof of
  `voteID_t → pkgDigest_t` under the current root (consequently, a predecessor cast in the
  *same* batch cannot be consumed yet — §14). It inserts $\mathrm{NULL}_t$ into the nullifier
  tree (insert-once: double consumption is impossible), subtracts $P_t$'s public `E` from the
  accumulator, and adds $P_{t+1}$'s.
- Invariants enforced by the batch program: an **empty slot admits exactly one initial
  package**; a package for an **occupied slot must consume exactly one admitted, unconsumed
  predecessor of the same owner and slot**; refreshes never create occupancy.
- **Per-voter cast budget (the chain counter).** Each package opening carries a private
  counter `t`, bound inside `pkgCommit` (§5.1): a first package proves `t = 0`; a revote
  proves `t_new = t_prev + 1` against the predecessor's opening and
  `t_new ≤ maxRevotesPerVoter` (an immutable election parameter, §2.3). The counter is
  **private** — publishing it would leak revote patterns — and the ballot STARK enforces it,
  with `maxRevotesPerVoter` authenticated from the immutable election parameters and all
  counter/capacity arithmetic in bounded integers (no wraparound). `t` is distinct from the
  recovery-mode randomness counter (§5.2): a voteID-collision retry advances randomness
  allocation, not the number of admitted predecessors.
  Why it exists: with only a global cast capacity, one eligible voter could legally consume
  it all (e.g. a 100-slot election with a 200-cast budget: one voter casts once, then revotes
  199 times, each with a valid proof and fresh nullifier — and no other voter can cast a
  first ballot). The per-voter bound makes that impossible, and the global capacity
  `maxVoters × (1 + maxRevotesPerVoter)` then holds by construction rather than by racing.

Nullifiers are unlinkable to packages for third parties (they depend on `sk`). The coercion
consequences are stated in §12.3.

### 5.4 Submission interface (voter → sequencer)

The voter submits to one sequencer, over an encrypted channel as in v2:
`{CanonicalPackage, hybridSig?, ballotProof, censusProof?, and — for a revote — the
predecessor reference (voteID_t, pkgDigest_t) with its inclusion path}`. The sequencer (and
its prover) therefore **learns revote events and predecessor linkage for the votes it seals —
the same boundary as v2**, where the sealing sequencer learns which updates are overwrites.
It never learns ballots, shares, pads, or `sk`: those stay inside the STARK witness. The
batch program receives the predecessor's public data as ordinary host input; the STARK is
what makes it *authorized* (nullifier + ownership), and the chain is what makes it
*authentic* (vote-ID leaf).

**What never enters public data availability:** `hybridSig` (a recoverable signature would
link the package to its Ethereum address), the ballot proof, the inner proof's public
vector, and the predecessor/revote metadata all stop at the voter→sequencer→guest boundary.
Blobs carry only `CanonicalPackage` and the batch-level data of §8.6.

---

## 6. The ballot proof (Plonky3 STARK)

The Groth16 circuit is replaced by a STARK over Goldilocks, proven in the browser via WASM —
the production descendant of the davinci-stark prototype [DST], minus its elliptic-curve
section. No trusted setup.

**Public inputs: the raw public vector.** There is no binding hash (v1.0's `inputsHash` is
removed): the proof exposes the public statement **directly as a pinned, ordered vector of
Goldilocks elements/limbs** — at least: `version` · `processID` · `packedBallotMode` ·
`voteID` · the identity binding (`address` limbs and `pk_PQ` or the legacy branch's
`H(sk_pkg)`) · `slot` · `authMode` · `isRevote` · `weight` · all `E` coordinates (ν·16
elements) · all `h_i` (ν × 8×32-bit limbs) · `pkgCommit` limbs · `ctsDigest` limbs ·
`prevPkgDigest` limbs · `NULL` limbs — **≈ 420+ elements at ν=16**. The vector layout is
length-prefixed per ν and never truncates. `ctsDigest = Blake3(cts)` is computed *outside*
the circuit and enters as opaque limbs — this **binds** the ciphertext bytes without proving
anything about ML-KEM.

**Statement contract (normative).** The batch program **constructs the expected public
vector itself** — from the canonical package it admits, the authenticated election
parameters, the authenticated census data (§8.2), and the predecessor metadata — and
verifies the proof against *that* vector. It never verifies a supplied vector and then
processes different package data. Inside the AIR, every value used by ballot validation,
share generation, masking, commitments and nullifier derivation is constrained equal to
these publics, so an admitted package is byte-for-byte the one the voter's proof authorized.
`censusRoot` is **not** a ballot public input: membership is the batch program's job (§8.2).
Privacy note: the inner proof's public inputs live at the voter→sequencer/guest boundary —
they are **not** published in blobs beyond what the package itself already publishes.

**The proof shows:**
1. **Ballot validity** — v2's ballot protocol (ranges, uniqueness, cost sum vs
   `maxValueSum`/weight, `ballotMode` unpacking), with three normative strengthenings over
   the v2-era prototype: the weight bound is enforced when `maxValueSum = 0`; all comparisons
   use sound borrow-checked integer gadgets (no Goldilocks wraparound); and the cost sum is
   computed overflow-safe under the enforced integer-cost profile (§2.3).
2. **Share consistency** — for every field (including inactive ones, with constant term 0),
   the ν shares lie on one polynomial of degree ≤ θ−1 whose constant term is the ballot
   value. Cost: ν·16·(θ−1) ≈ 1.8k multiplications at ν=16, θ=8 — trivial for the AIR.
3. **Mask consistency** — $e_{i,f} = s_{i,f} + \mathrm{mask}_{i,f}$ where the 16 masks of
   warden $i$ are the LE128-mod-$p$ slices of the single keyed XOF stream
   $\mathrm{Blake3.keyed}(K_i, \mathrm{streamCtx}(i))$ (§2.2), with the same $(s_i, K_i)$
   committed in $h_i$.
4. **voteID derivation** from `(processID, address, k)` (Blake3, §5.2), with all of these
   bound in the public vector.
5. **Authentication** (§11): knowledge of `sk` with `H(sk) = pk_PQ`, where `pk_PQ` is a
   public input that the **batch program** binds to the authenticated census leaf (§8.2) —
   census membership itself is *not* proven in the ballot AIR. For an unenrolled hybrid
   voter (census `pk_PQ = 0` means "no enrolled key" — the proof never requires
   `H(sk_pkg) = 0`): knowledge of the self-chosen `sk_pkg` bound in the chain's first
   `pkgCommit` (§11), with identity resting on `hybridSig`. For a revote, additionally the
   predecessor opening (same slot, same key), the `NULL` derivation of §5.3, and the chain
   counter rule `t_new = t_prev + 1 ≤ maxRevotesPerVoter` (§5.3). Authentication relies on
   the proof system's **knowledge soundness**: the proof must establish that the prover
   *knows* the preimage/witness (bound to this entire authorized package), not merely that
   one exists.

**The in-AIR Blake3 section.** All in-circuit hashing runs in a **re-laid Blake3 section**
(~25–32 rows per compression at the circuit's width). Honest compression budget under the
§2.2 stream-masking definition: per warden ≈ 1 context block + 4 XOF output blocks for the
masks + ≥ 4 for $h_i$ (its input is ≥ 219 bytes: processID, registry, voteID, 16 shares,
$K_i$, before context fields); plus ≈ 12 for `pkgCommit`, `sharesDigest`, voteID, `NULL`
and the counter — **provisionally ≈ 57 compressions at ν=5, ≈ 156 at ν=16**, to be fixed by
instrumented counts of the exact canonical encodings for both admission paths (first vote
and revote). Earlier drafts said ~45/~110 against a per-field masking rule that would
actually have needed ≥ 80/256; the stream rule above is what makes counts this low possible.
It MUST constrain full standard-Blake3 semantics, not merely a compression gadget:
canonical input bytes, exact lengths and zero padding; correct IV / keyed / `derive_key`
initialization per mode; the full 7-round schedule with both feed-forward halves; the
64-byte-block and 1024-byte-chunk structure with correct counters and
`CHUNK_START`/`CHUNK_END`/`ROOT` flags; correct chaining between compressions; XOF
output-block counters (an XOF is a seekable stream, not repeated hashing); outputs
constrained equal to the values consumed elsewhere in the AIR; and selector/phase
constraints that cannot skip or disconnect any check. Negative test vectors regenerate
otherwise-correct traces with wrong flags, counters, lengths or chaining values.

What the proof deliberately does **not** show: that `ct_i` decapsulates to the committed
$K_i$. Proving ML-KEM in-circuit would drag SHAKE through the AIR. Instead, mismatched
transport is *harmless to integrity* (no tally proof ever runs Decaps — §10.2) and *publicly
excludable* (complaints — §9.2). A STARK-friendly verifiable encryption removing this
trade-off is the main tracked upgrade (§15).

**Indicative numbers.** Measured on the prototype [DST]: the Blake3 Merkle/challenger profile
proves in **0.69 s native** (vs 3.2 s for the old Poseidon2 profile) with **~324 KB proofs**;
a standalone Blake3 compression AIR costs ≈3.4 ms/compression at its wide layout. The
full-Blake3 ballot (re-laid in-AIR section) is a **projection, not a measurement**:
**~2–4 s native (ν-dependent; the blowup-32 profile costs ~2.7× the old blowup-8 prover time, bought back for the batch guest — §8.1)**, ~195 KB proofs — to be re-benchmarked once the
re-laid AIR exists (equal cell counts do not guarantee equal proving cost; the degree and
quotient profile must be recomputed). Browser proving is expected at a few × native (mobile
slower — to be benchmarked; the proof uploads once to one sequencer and is never stored
on-chain). Benchmark provenance: all prototype figures in this document come from internal
prototype commits; exact commits, hardware, compiler flags and proof settings will be
published with the reference implementation. Standing adoption gates (from review): fix the
vendored challenger's wasm32 query-sampler bug; production hiding CSPRNG; implement full
Blake3 chunk/tree semantics over the `blake3f` precompile with boundary-length test vectors
(0/63/64/65/1023/1024/1025 B); measure real browser and whole-batch guest costs before
deployment guarantees. Before `ballotVKHash` is pinned, the **complete proof profile** must
be fixed and published: the challenge extension field and its defining polynomial; trace
shapes, maximum constraint degree and quotient construction; FRI folding and final-polynomial
parameters; hiding dimensions and the blinding-randomness source; the complete Fiat–Shamir
transcript (observe/sample schedule, domain-separated initialization, the Merkle-commitment (MMCS) matrix layout and shape
checks, serialization); and the knowledge-soundness assumptions with the claimed quantum
security model.

---

## 7. State tree changes

Same sparse-Merkle-tree structure, depth 64, same namespaces as v2 — now hashed with
**Blake3** (leaf: `Blake3(key_LE8 ‖ value_32 ‖ 0x01)`, node: `Blake3(left ‖ right)`), plus
four changes:

![State tree v3 layout](figures/state-tree-v3.svg)

1. **Vote-ID leaves carry the package digest**: `voteID → pkgDigest` (v2 stored 0). This lets
   revotes and complaints authenticate a package *body* against the chain.
2. **Slot leaves are chained opaque digests** (no ballot data):
   - first vote / overwrite: `leaf = Blake3("davinci-slot-v3" ‖ pkgDigest ‖ s_batch)`
   - refresh: `leaf' = Blake3("davinci-refresh-v3" ‖ leaf ‖ s_batch)`
   with `s_batch` the sequencer's secret batch seed (proven in-guest, never published — the
   same trust class as v2's re-encryption seed). A refresh needs only the **public current
   leaf** plus the refresher's own secret, so **any sequencer can refresh any occupied slot**
   — permissionless sequencing is preserved and a vanished sequencer blocks nothing. Both
   update types produce fresh-looking 32-byte values; this plus the padded accumulator is
   what replaced re-encryption-based silent revoting.
3. **Config namespace**: `0x3` = `wardenSetHash` (§4) instead of an encryption key; `0x4` =
   `Blake3(A)` (the accumulator value itself is published in every batch's blobs); `0x5`
   (reserved in v2) = the root of the **nullifier tree**, a dedicated Blake3 SMT of depth
   256. A nullifier is a 32-byte Blake3 digest used directly as the 256-bit key; leaf
   value = 1.
4. **Genesis predicate replaces on-chain genesis computation.** The EVM has no Blake3
   precompile, so the registry no longer computes the genesis root itself. Instead it stores
   the election parameters and an **initialization flag**, and the **first transition's batch
   proof constructs the genesis tree deterministically in-guest** from the registry-supplied
   parameters — the canonical empty tree plus *exactly* the prescribed config leaves, the
   zero accumulator in its prescribed encoding, an empty nullifier tree, no slots, no
   packages, correct initial counters — and proves `oldRoot` equals that construction.
   Membership proofs under a prover-chosen root are **never** accepted as a substitute (they
   show presence, not absence of extra state). Registry rules: the genesis branch is
   selected by the stored initialization flag (never caller input); parameters come from
   registry storage, not calldata; the first transition and initialization are recorded
   atomically; thereafter `oldRoot == storedRoot` always, and re-initialization is
   impossible; the outer proof binds the full `(chainID, registry, processID)` (not just
   v2's 4-byte prefix); and an **initialization-only transition** (zero ballots) is an
   explicit path so empty elections can still finalize.

---

## 8. The batch program (ZisK guest)

In one line: the batch program is the referee — it re-checks every vote package, applies the
state updates, and maintains the masked running total.

Same role, same settlement flow, same public-output pattern (`ok`/`failMask`, old/new roots,
counters, census root, blobs digest) as v2. The constraint groups change as follows.

![Batch program v3 dataflow](figures/batch-flow.svg)

### 8.1 Ballot proof verification — measured cost, honest sizing
Verifies the n ballot STARKs **in-guest**. This cost has now been **measured on the real
emulator** (a ZisK guest running the Plonky3 verifier on an actual ballot proof; internal
prototype — exact commits/hardware/flags to be published with the reference
implementation, §6), and it is
the dominant cost of the v3 batch program — far above the earlier modeled figure, because
hashing turns out to be a minor component: at the pinned profile (§2.3) one verification
costs **≈14.5M guest steps** (22.1M at the former blowup-8/34-query profile), of which
hashing via the `blake3f` precompile is only ~1.5M (4,681 compressions); the rest is FRI
field arithmetic, Merkle path bookkeeping, the symbolic constraint rebuild (1.49M,
**amortized once per batch** since all proofs share one AIR), and proof deserialization.
Two further optimizations are **normative implementation requirements**: Goldilocks
inversions use ZisK `fcall` hints (hint + multiply check, replacing ~1.4k-step software
inversions — the mechanism ZisK already uses for secp256k1/BN254 inverses), and opened rows
are hashed as words, not per-byte streams. **GPU-measured** (RTX 5090,
cargo-zisk 1.3.0-alpha, this exact profile, after a reviewed no-precompile optimization
pass — per-batch setup hoisting, the existing `uint256_inv_mod` fcall as the Goldilocks
inverse hint, word-level hashing, and a differentially-tested fork of the FRI verifier
factoring query-independent sums): per-proof cost fell from 14.45M to **2.62M steps**
(−82%), and proving the verification of 1 / 8 / 32 proofs takes **10.4 / 12.5 / 19.8 s** —
a ≈10 s fixed pipeline plus **≈0.30 s marginal per verification**, i.e. ≈1.6
verifications/s at K=32 and a projected ≈2.7/s at K=128 per GPU. A 256-ballot batch's
verification layer proves in ≈1.5–2 minutes; the fixed pipeline cost, not per-ballot work,
now dominates.
With the amortization and inverse hints above (and a proposed upstream Goldilocks-ext²
precompile), ~1 verification/s/GPU is the modeled target. Practical batch sizes today:
32–128 ballots for v2-like latency, 256 where ~8-minute batches are acceptable; throughput
scales across provers as in v2 — the price of post-quantum ballots is paid in parallelizable
sequencer GPU time, not voter experience. The guest implements Blake3's chunk/tree layout
over the compression syscall; Merkle parents are `BLAKE3(left ‖ right)`. The ballot verifier
configuration (AIR identity, FRI profile, transcript and hash profile) is pinned via
`ballotVKHash` at config leaf `0x7`, as in v2, and the guest constructs each proof's expected
public vector per the §6 statement contract.

### 8.2 Census, authentication, binding
Census membership is verified **here**, as in v2 (not in the ballot AIR): the program
authenticates the census leaf `Blake3(address ‖ weight ‖ pk_PQ)` with a Merkle path under an
accepted root, derives the slot by the census-origin rule, and proves the **join equality**:

$$\text{ballot publics } (\text{identity key},\, weight,\, slot,\, authMode) \;=\; \text{authenticated census values and policy}$$

The census root it checks is bound in the **batch statement** and must be accepted under the
election's origin-specific registry policy — never chosen freely by the prover. `authMode` is
derived from the immutable election auth policy plus the creation-time enrollment snapshot
(§11) and compared against the proof's public input — never prover-chosen. Authentication
then follows the policy: `pq-only` relies on the in-STARK preimage proof alone; `hybrid`
*additionally* verifies `hybridSig` (ECDSA over `pkgDigest`, secp256k1 precompile, recovered
address = census address) for every package; `hybrid-legacy` dispatches per census leaf as
specified in §11. The program recomputes `ctsDigest` and `pkgDigest` from the package body
and constructs the proof's full expected public vector from that body (§6 statement
contract) — so an admitted package is byte-for-byte the one the voter's proof authorized.

**On-chain censuses and the PQKeyRegistry (origin 3).** Contracts cannot hash Blake3
cheaply, so on-chain censuses maintain an incremental **keccak256 running commitment** of
their authorized registrations (one `keccak256(prev, entry)` per registration — Solidity-
native). A permissionless **census-root conversion proof** — a small ZisK guest — attests
"running commitment `c` corresponds to Blake3 lean-IMT root `r`"; the registry verifies it
and stores the accepted `(c, r)` pair, and batches then use `r` under the origin-3 root
policy. No unauthenticated off-chain root ever enters the system.

### 8.3 State transitions
In fixed order, each proven against the previous root, as v2: (1) insert
`voteID → pkgDigest`; (2) insert revocation nullifiers with the one-live-chain checks of
§5.3 (predecessors must be settled under the starting root); (3) write slot leaves (votes +
overwrites), then refresh the sample $\mathcal{R}$ (§7.2; sample-size rule as v2); (4) update
`0x4` with the new accumulator digest and `0x5` with the new nullifier root.

### 8.4 Accumulator update and the batch pad
$$A' = A + \sum_{\text{new pkgs}} E \; - \sum_{\text{consumed pkgs}} E \; + \; B$$

In words: the new accumulator is the old one, plus the masked shares of every package this
batch adds, minus the masked shares of every package it revokes, plus a fresh secret pad $B$
whose only job is to hide *which* rows were subtracted.

Here $B \in \mathbb{F}^{\nu \times 16}$ is a fresh **uniform** batch pad derived in-guest
from the secret batch seed. Without $B$, the public batch delta minus the (public) new-package
sums would equal $-\sum_{\text{consumed}} E$, letting anyone identify revoked packages by
matching public `E` rows. $B$ is deliberately *unstructured* — a Shamir-codeword-shaped pad
would vanish under the code's public parity checks and leak the same information.

### 8.5 The warden payload (KEM-DEM, proven)
Per batch, the guest: derives a 256-bit batch key $k_b$ and the ML-KEM encapsulation
randomness from the secret batch seed (guest-internal derivation under the pinned program, so
it is as trustworthy as the proof itself); DEM-encrypts (§2.1)
`payload = (B ‖ consumed pkgDigests ‖ context)` under $k_b$; Shamir-shares $k_b$
**coordinate-wise over its 32-bit limbs** θ-of-ν; and for each warden $i$: one in-guest
ML-KEM encapsulation to $pk_i$ → wrapping secret → DEM-encrypts share $i$, and publishes a
salted Blake3 **commitment to each recipient's share** (opening salts travel inside the
respective DEM ciphertexts; these commitments are what lets tally participants validate
forwarded shares in §10.4 without decapsulating each other's ciphertexts). The proof binds
$B$ to the accumulator update, the consumed list to the nullifier insertions, every
ciphertext to its registered recipient key and context, and the share commitments to the
shared $k_b$. **Unlike voter transport, a malformed
batch payload is unprovable, not merely complainable** — it would hide an accepted
transition's revocations and pads from the tally. All of it is published in the batch's blobs.

### 8.6 Blob layout v3 and honest DA numbers
Blob cells carry 31 payload bytes each (a v3 codec choice — v2 packed typed values; v3 packs
an opaque byte stream per section), 4096 cells per blob ⇒ 126,976 B per blob. Sections, in
order: header · new packages (CanonicalPackage bytes) · slot-update list
(slot index 8 B + new leaf 32 B — so a refresh costs 40 B framed, vs ~1–2 KB in v2) ·
nullifiers (32 B each) · accumulator value $A'$ (ν·16·8 B) · warden payload (§8.5).
Byte-exact cell maps live in the davinci-zkvm normative docs, as in v2. One divergence from
v2's blob flow: the evaluation point becomes
$z_b = \mathrm{keccak256}(\text{processID} \,\|\, \text{stateRoot}^{old} \,\|\, \text{blobCommitment}_b) \bmod q_{BLS}$
— keccak because the **registry contract** computes it (Solidity-native; the guest recomputes
it via the keccak precompile, one call per blob — a §2 island).

Per-package size: `72 + ν·(160 + ct_len)` bytes (72 B fixed fields; per warden: 128 B of
masked shares + 32 B commitment + one ciphertext) ⇒ **20,040 B** at ν=16/ML-KEM-768;
14,920 B at ν=16/ML-KEM-512; 6,312 B at ν=5/768; 1,320 B at ν=1.

| Profile (256 votes + 256 refreshes) | batch bytes | blobs (126,976 B each) | vs v2 (~5 blobs) |
|---|---|---|---|
| **ν=8, ML-KEM-768 (v3.0 max)** | ≈ 2.6 MB | **≈ 21** | ~4× |
| ν=5, ML-KEM-768 | ≈ 1.7 MB | ≈ 14 | ~2.7× |
| ν=1 (sequencer mode) | ≈ 0.35 MB | ≈ 3 | ~0.7× — *cheaper than v2* |
| ν=16, ML-KEM-768 (future profile) | ≈ 5.2 MB | ≈ 41 — exceeds the 32-blob cap ⇒ ~195 votes/batch or ML-KEM-512 (≈31) | ~8× |

**The two settlement modes reach the same 32-blob cap — by different mechanisms.**
**L1-blob mode** posts blobs across multiple Ethereum transactions and proves their chain
inclusion on the rollup, as v2's OP-Stack path. **Native blob mode** is no longer limited
to one blob-carrying transaction (EIP-7594's 6 blobs): a state transition may be published
as a **sequence of blob transactions followed by the settlement call**. Each blob
transaction calls `registerBlobs(processID, batchSeq, index)` on the registry, which reads
its own transaction's versioned hashes via the `blobhash` opcode — the only trustworthy
on-chain binding between a versioned hash and an actually-published blob — and records them
— with the registration **block number** — keyed by `(processID, msg.sender, batchSeq,
index)` (never a caller-supplied identity). Rules, all reverting on violation (reviewed;
conditions incorporated):
- **Freshness.** A registration set snapshots the current state root; a root change
  invalidates it immediately (a lost race kills the set, not merely the next
  registration). Settlement must land within a **maximum registration age** safely inside
  the DA-retention window — stored hashes prove *historical publication*, not *present
  availability* — and wardens/observers collect pre-published blobs from registration
  time, not settlement time.
- **Exact manifest.** Indices are batch-global (0..nBlobs−1, ≤ 32), slots immutable and
  non-overlapping once written, `blobhash` values nonzero; the settlement transaction's
  own blobs fill the remaining indices in ascending order (one deterministic merge rule);
  every position the proof's blob count requires must be present in the exact proof-bound
  order — gaps, overlaps, reordering and partial settlement revert. `batchSeq` is per
  `(processID, sender)`, monotonic and non-wrapping; consumed sequence numbers are never
  reusable. Verification, root update and consumption are atomic.
- **Storage lifecycle.** One bounded active manifest per (sender, process); slots are
  reused or explicitly deleted; expired records are permissionlessly cleanable in bounded
  batches; registrants pay registration gas (≈640k gas of fresh SSTOREs for a full
  32-slot manifest), cleanup is deposit/bounty-funded, and no settlement or lifecycle
  path ever iterates over all registrants.
Per-sender keying prevents another sender from occupying this sender's registration slots
— it is not a general anti-griefing claim. For every manifest position the registry
preserves the full binding chain: stored versioned hash → commitment via the
point-evaluation precompile → `z_b = keccak(processID ‖ stateRoot_old ‖ commitment)` with
`stateRoot_old` required to equal the current root → the proof-bound ordered blob digest.
Cross-transaction publication therefore adds **no new KZG assumption**. The first 6 blobs
may still ride the settlement transaction itself; native mode supports every v3.0
profile, and small batches settle exactly as in v2 with zero extra transactions.

DA is v3's main cost regression and is linear in ν: size committees to the election's
stakes. Classic McEliece transport (96–128 B ciphertexts ⇒ 4.2–4.7 KB/package at ν=16 by the
same formula) is the tracked reduction path for large committees [MCE].

---

## 9. End of election: freeze, complaints, exclusions

The v2 timeline (end → grace window) gains two phases before results:

![Election timeline v3](figures/timeline.svg)

### 9.1 Casting freeze
When the grace window closes the registry stops accepting transitions (as v2) and the
accumulator freezes as $A_{\text{cast}}$, bound to the frozen final root.

### 9.2 Complaint window and the exclusion set X
During a scheduled window (an election parameter, like the grace bounds), **registered
wardens of the election** may submit complaints: `submitComplaint(processID, pkgDigest,
publicValues, proof)` where the ZisK proof shows `Decaps(sk_i, ct_i)` yields a key
inconsistent with the package's admitted $h_i$ (witness: the warden's registered key seed;
statement bound to the admitted `pkgDigest` and the frozen root). The registry verifies the
proof and appends the package to an **idempotent, append-only exclusion set $X$**. Complaints
**never touch the accumulator** — so no complaint needs to know whether its package was
already consumed, and ordering cannot matter. Submission is allow-listed to the election's ν
wardens; the submitter pays gas. **Capacity is sized to the workload, not an arbitrary cap**:
total admitted casts are bounded by `maxVoters × (1 + maxRevotesPerVoter)` (§2.3 — the
per-voter bound of §5.3 enforced in-proof, times the electorate), and the complaint window
length and the wardens' proving/fee budget must cover that bound in the worst case (an
adversary can make the complaint path linear in admitted casts — this is an explicit
liveness assumption, §9.3, not an exceptional path). At the
deadline $X$ freezes on-chain; every tally proof binds the frozen
$(\text{root}, A_{\text{cast}}, X)$ snapshot.

Semantics, stated plainly: a voter whose *live* package ends up in $X$ is not counted (their
earlier packages stay consumed) — a deliberately malformed revote is a provable
self-abstention, and a voter+warden coalition gains a bounded post-close withdrawal option
for that voter's own ballot. A package malformed toward warden $i$ that is *not* excluded
still tallies correctly from wardens that can open it (§10.2); warden $i$ either complains in
the window or sits out.

### 9.3 Liveness
The tally needs at least θ wardens (the tally threshold) that complete the archive scan (and any complaints) inside the
window, complete the ceremony (§10.3), and publish proven contributions — plus, as in v2,
timely inclusion of their transactions, **plus complaint capacity (proving + fees + window
length) provisioned for the election's admitted-cast bound in the worst case (§9.2)**,
**plus availability of the complete blob archive**: blobs prune after ≈18 days (§4), so for
elections longer than the retention window, continuous redundant archival by wardens (or
archivers they trust) is itself a tally-liveness assumption — missing payload history means
the tally cannot complete.
Fewer ⇒ results are lost, exactly as v2's "θ of ν wardens take part in decryption".

---

## 10. Tally: warden sums and Lagrange

In one line: this is where the masked running total becomes the election result — in public,
with proofs, and without any decryption key.

### 10.1 What each participating warden computes
After the exclusion freeze, each participating warden $i$:
1. holds the complete blob archive (continuously collected during the election — §4; work is
   linear in *total casts*, not final voters, and decapsulation/share recovery MAY run
   incrementally during the voting period);
2. decapsulates its per-package ciphertexts, regenerates each package's mask stream
   ($\mathrm{Blake3.keyed}(K_{v,i}, \mathrm{streamCtx}(i))$, §2.2), recovers shares
   $s_{v,i,f} = e_{v,i,f} - \mathrm{mask}_{v,i,f}$, and checks each against
   the admitted $h_{v,i}$;
3. joins the **tally ceremony**: the participants exchange batch-payload-key shares
   **privately** (§10.4 — never in public), reconstruct the per-batch payload
   keys (θ shares each), decrypt the payloads — obtaining every batch pad $B$ and the full
   consumed set $R$, verified against the batch proofs that committed them — and run the
   zero-blinding round producing $G_f$ (§10.3);
4. computes, over $\mathrm{Active} = \mathrm{Admitted} \setminus (R \cup X)$:

$$S_{i,f} = A_{\text{cast},i,f} - \sum_{v \in X \setminus R} e_{v,i,f} - \sum_{v \in \mathrm{Active}} \mathrm{mask}_{v,i,f} - \sum_{b} B_{b,i,f} + G_f(i)$$

In words: start from the frozen running total; remove the rows of excluded-but-never-revoked
packages; strip your own masks for every counted package; strip the batch pads; add your
blinding share.

One-line sanity check: $A_{\text{cast}}$ = (masked shares of all admitted-minus-consumed
packages) + (all batch pads); removing the still-present excluded rows, all pads, and all
batch pads leaves exactly $\sum_{\mathrm{Active}} s_{v,i,f}$; adding $G_f(i)$ with
$G_f(0)=0$ doesn't change the interpolation at 0.

5. publishes $S_i$ with a **ZisK proof** whose statement binds: the election, the frozen
   $(\text{root}, A_{\text{cast}}, X)$ snapshot, the complete archive commitment, its
   recipient index, and the accepted ceremony transcript (§10.3–§10.4) — and whose witness
   contains
   its KEM key seed (authenticating it as warden $i$ against the registered commitment), the
   per-package $(s, K)$ openings **for every counted active package** (each checked against
   its admitted $h_{v,i}$), the reconstructed payload keys and payload openings, and its
   blinding evaluations. The program enforces **complete, exactly-once processing** of every
   admitted package in the archive (counted, consumed, or excluded — nothing skipped) and
   that $R$ and $B$ are the values authenticated by the accepted batch payloads.
   **The complete archive commitment, concretely**: the **registry itself maintains the
   authenticated terminal checkpoint**: on every accepted transition it folds the batch into
   a contract-side running accumulator, `archiveAcc' = keccak256(archiveAcc ‖ batchNumber ‖
   stateRoot_new ‖ blobsDigest)` (keccak: it is contract-computed — the island rule), and
   stores `(archiveAcc, batchNumber)`. At the exclusion freeze this pair is frozen with the
   snapshot, and **every contribution proof must bind exactly that frozen pair** — a warden
   cannot supply its own batch list and commitment (consistency with a chosen list is not
   completeness). The proof re-folds the canonical ordered batch list (batch 0 = the genesis
   transition; every accepted batch including zero-ballot initialization transitions and
   their payloads) and must reach the frozen accumulator and count; every admitted package
   of every batch is processed exactly once. For scale, chunked proving authenticates its
   **continuation state** — progress index, the running accumulator AND the partial sums —
   between segments; carrying the hash alone does not certify earlier computation.
6. `submitTallyShare(processID, i, S_i, publicValues, proof)`; after θ verified shares,
   anyone calls `finalizeResults(processID)`: **the registry performs the Lagrange
   interpolation on-chain** (θ ≤ 16 points over Goldilocks — a few u64 mulmods per field),
   records the per-field results, and emits `ProcessResultsSet`.

Wardens run their **own provers**: the witness contains their secrets, and a shared proving
service used by θ wardens would itself hold reconstruction capability. Proving cost scales
with total casts, and "a few hashes per package" is **not** the honest model: rehashing each
`CanonicalPackage` for the archive-commitment check alone costs ≈99 input-block compressions
per package at ν=5/ML-KEM-768 (≈314 at ν=16) before Blake3 tree merges, mask regeneration,
commitment checks, payload and ceremony verification — so a million-cast tally job is on the
order of **10^8–3×10^8 compressions plus bookkeeping** (an **unvalidated projection**, to be
benchmarked with the v3 implementation before warden hardware guidance is given). A tracked
optimization (§15) is an authenticated per-warden view / preprocessing proof that avoids
re-hashing full packages in every warden's proof.

### 10.2 Why malformed voter transport cannot corrupt anything
**Decapsulation never appears in any tally proof** — contributions open the admitted
commitments $h$ instead, and under commitment binding every accepted $S_i$ lies on the same
aggregate polynomial. A voter publishing a bad `ct_i` only deprives warden $i$ of its opening
witness (warden $i$ complains or sits out; the voter could even re-supply the opening
out-of-band, which is safe — correctness is tied to $h$, not to the transport). Every clean
θ-subset interpolates the same tally, because the ballot STARK proved all ν shares lie on one
valid polynomial. Malformed transport is an availability lever against one warden, never an
integrity lever against the election.

### 10.3 The zero-blinding ceremony
In plain terms: before publishing their partial sums, the participating wardens jointly add
noise that cancels out exactly at the finish line (x = 0), so the published sums reveal the
result and nothing else. Why it's needed: published raw, θ sum-shares determine the aggregate
polynomial $F$; any single warden — participant or not — could evaluate it at its own index,
compare with the sum of its decoded per-package shares, and fingerprint the revoked set. The
ceremony prevents that:

1. A `tallySession` is recorded on-chain: session id = `H(processID ‖ root ‖ X ‖ roster ‖ attempt)`, where `attempt` is a **registry-controlled monotonic nonce** incremented on every restart (the id must change even with an identical roster and snapshot); the registry tracks exactly one active attempt, rejects messages and contributions bound to stale attempts, and fixes the point at which the dealer set becomes immutable,
   with the participant roster and dealer set fixed (dealers = the participants).
2. Each dealer $k$ samples a seed and derives, per field, blinding coefficients
   $c_{k,f,1..\theta-1}$, defining $g_{k,f}(x) = \sum_j c_{k,f,j} x^j$ — **the constant term
   is structurally absent, so $g_{k,f}(0) = 0$ by construction** (this is the
   "zero-certificate": the committed coefficient vector simply has no degree-0 entry).
3. Dealer $k$ publishes (in a session blob): a hiding commitment to its coefficients
   (salted unkeyed Blake3, §2.3); **per-recipient hiding evaluation commitments**
   $cm_{k,i} = \mathrm{Blake3}(g_{k,1..16}(i) \,\|\, r_{k,i})$; the KEM-DEM ciphertexts to each
   co-participant $i$ encrypting $(g_{k,1..16}(i), r_{k,i})$; and a **ZisK dealer proof**
   that the committed coefficients, the evaluation commitments, and the ciphertexts are all
   consistent, under the recipients' registered keys and this session's context.
4. Contributions use $G_f(i) = \sum_{k \in D} g_{k,f}(i)$ over the **accepted dealer set
   $D$** — fixed on-chain after the dealer deadline; every contribution proof binds the same
   $D$ and session id, and **opens the evaluation commitments $cm_{k,i}$** (the recipient
   learned the opening by decapsulating off-circuit — decapsulation still never enters any
   tally proof). A dealer whose proof is missing or invalid is excluded and the session
   restarts with fresh masks (roster must stay ≥ θ).

As long as one accepted dealer is honest, no one outside the ceremony — and no
non-participating warden — learns anything about $F$ beyond what the public tally
$F(0)$ itself reveals. Participants do jointly learn the
revoked set $R$; that is the documented θ-gated metadata leakage (§12.2).

### 10.4 The private batch-key exchange and the session state machine

The batch-payload keys $k_b$ (§8.5) are θ-of-ν shared; **reconstructing them must not leak
them**: publicly releasing enough shares of any $k_b$ reveals $B_b$ and the consumed-package
list — exactly the revocation metadata the batch pads exist to conceal. So the share
exchange is **private, pairwise and authenticated**, never part of the public transcript:

- Each participant sends its share of each needed $k_b$ to each co-participant via
  **pairwise KEM-DEM** (encapsulate to the recipient's registered warden key; DEM context
  bound to election, batch, session and attempt — §2.1), recipient-authenticated.
- A recipient **validates** every received share against the batch's published per-share
  commitments before using it. To make that possible, §8.5's payload includes, per
  recipient share, a salted Blake3 **share commitment** (bound in the batch proof); the
  sender's pairwise message carries the share value and the commitment's salt, so any
  recipient can check the opening without decapsulating the sender's ciphertext. An invalid
  opening proves the *message* bad — but KEM encryption authenticates the recipient, not the
  sender (anyone can encapsulate to a public key), so **the protocol does not claim
  cryptographic fault attribution**: a failed exchange (invalid or missing shares, from
  whatever cause) simply triggers a restart with a roster-policy-chosen replacement, and
  liveness assumes a successfully communicating honest roster. (Sender-authenticated
  transport via warden SLH-DSA keys is a tracked hardening, §15.) "Fresh masks" on restart
  means fresh ceremony blinding and transport randomness — settled batch keys and batch
  pads never change.
- Plaintext key shares and reconstructed keys never appear on-chain or in blobs; contribution
  proofs reference the payload *openings* (witness), not the keys.

**Session state machine** (contract-side): any registered warden of the election may open a
`tallySession` after the exclusion freeze; the roster is accepted when θ wardens have joined
by the roster deadline; the dealer set $D$ is fixed at that moment (dealers = participants);
dealer publications (§10.3) have their own deadline, after which $D$ freezes; a missing or
invalid dealer, or a failed share exchange, triggers **restart**: a new session id and
attempt id, fresh masks, and automatic **invalidation of all contributions bound to the
stale session**. `finalizeResults` accepts only θ distinct wardens' contributions **bound to
one accepted session and its frozen dealer set**. Honest framing: **removing the
election-key DKG does not remove coordinated cryptographic ceremonies — v3 replaces it with
different (smaller, tally-time-only) coordination work.**

---

## 11. Census and authentication

- **Census trees** migrate from Poseidon-BN254 to **Blake3** (a breaking format change; same
  lean-IMT structure; membership verified by the batch program, §8.2). Leaf encoding:
  `leaf = Blake3(address ‖ weight ‖ pk_PQ)` with `pk_PQ = H(sk)` for a CSPRNG-generated
  secret, or `pk_PQ = 0` for a not-yet-enrolled voter (hybrid-legacy censuses only).
- **PQ-key enrollment.** The Ethereum wallet signs an enrollment message binding
  `address ↔ pk_PQ`; the signature *authorizes* the binding and is never key entropy (a
  future ECDSA break must not reveal PQ secrets). Enrollment paths per census origin:
  off-chain censuses collect `pk_PQ` at census construction; on-chain/token censuses read a
  global **PQKeyRegistry** contract where voters register once (one transaction, reusable
  across all elections); CSP censuses include `pk_PQ` in the credential.
- **Election auth policy** (immutable registry parameter, fixed at creation):
  - `pq-only`: every leaf must carry `pk_PQ`; authentication is the in-STARK preimage proof
    alone; no ECDSA anywhere in the ballot path.
  - `hybrid`: every leaf must carry `pk_PQ`, and every package is verified on **both**
    authenticators — the in-STARK preimage proof *and* `hybridSig` (ECDSA over `pkgDigest`,
    verified by the batch program). No OR-downgrade exists in this mode.
  - `hybrid-legacy`: like `hybrid`, but leaves with `pk_PQ = 0` are admitted with identity
    resting on ECDSA alone; the STARK's auth clause (§6.5) switches to a **self-chosen
    package key**: the voter generates `sk_pkg` (CSPRNG; kept with the package opening). The
    first package binds `H(sk_pkg)` inside `pkgCommit`. Every later package in the chain
    proves knowledge of the *same* `sk_pkg` (predecessor opening) and derives its nullifier
    as `NULL = Blake3(nullCtx ‖ sk_pkg ‖ prevPkgDigest)`. The batch program dispatches per
    leaf: `pk_PQ ≠ 0` ⇒ both authenticators against the census key; `pk_PQ = 0` ⇒ mandatory
    `hybridSig` + the `sk_pkg` clause. Anyone can count the legacy-status census members
    (leaf contents are public census data) — though not, of course, which *final* packages
    are theirs beyond what slot-participation already reveals. Ballot *privacy* is fully PQ
    for these voters; the election's **integrity assumptions include ECDSA security for its
    legacy voters** (§12.1). This mode is what makes existing token censuses usable before
    universal enrollment.
- **Enrollment snapshot rule.** A voter's authentication status and key for an election are
  pinned at the election's **creation snapshot**: for on-chain/token censuses the registry
  records the PQKeyRegistry root at the creation block, and membership proofs must present
  the enrollment status under that snapshot regardless of which (newer) eligibility root the
  census contract later accepts. Enrolling *after* an election was created affects
  subsequent elections only — an existing package chain never changes keys mid-election.
- **CSP censuses**: credentials become SLH-DSA signatures [FIPS 205] over the v2 message
  format extended with `pk_PQ`; verification is pure hashing via the SHA-256 precompile
  (SLH-DSA's internal SHA-2 is a FIPS island, §2 — not an application-level hash choice).
- Slot derivation, participation visibility, census origins 1–4 mechanics: as v2, with the
  enrollment additions above. The v2 census invariants (slot uniqueness across the census;
  stable distinct CSP indexes) remain assumptions of integrity.

---

## 12. Security properties, stated plainly

### 12.1 What holds, under what

| Property | Holds if |
|---|---|
| **Tally integrity** | STARK/zkVM soundness (FRI + hashes), binding commitments, correct pinned programs, the settlement chain executes the registry, and the v2 census invariants (unique slots / stable CSP indexes). Then no coalition of voters, sequencers, provers or wardens can shift a tally — including via malformed KEM transport (§10.2). |
| **Ballot privacy** | fewer than θ warden keys compromised **over their whole lifetime** (not just the active epoch), ML-KEM IND-CCA, PRF/hash security, hiding STARKs, and honest voter devices. Below θ, shares in isolation are information-theoretically independent of the ballot. **Post-quantum computational privacy — not "everlasting"**: an unbounded adversary could attack archived KEM transcripts. |
| **Revote hiding (public data)** | hash security + the sealing sequencer/prover draws the batch seed *and the refresh set* from fresh randomness and keeps them secret (v2's exact trust statement). Public data reveals participation per slot, update counts/timing, `numOverwrites` — v2's leakage surface. |
| **Exact tally** | unconditional arithmetic (mod-$p$ sums, Lagrange). ML-KEM's residual decapsulation-failure probability (≈2^-139 per pair at ML-KEM-512, ≈2^-164 at -768; election-wide union bound over *all* encapsulations: per-ballot, batch shares, ceremony deliveries) is not zero even for proven-correct encapsulations. Each failure degrades gracefully: a per-ballot failure becomes a complaint; a batch-key *share* failure is tolerated provided at least θ valid shares remain available (with ν=θ, or only θ responsive wardens, one failed share means that payload cannot be reconstructed and the tally cannot complete — size ν above θ accordingly); a ceremony delivery failure excludes the dealer and restarts the session. Deliberately malformed batch transport is a different thing entirely — it is unprovable (§8.5), so it cannot appear in an accepted batch. |
| **Liveness** | ≥1 honest sequencer with proving capacity and timely inclusion (as v2), plus ≥θ wardens through the scan window and ceremony (§9.3), plus **continuous archival of the blob history** (blobs prune in ≈18 days; missing payload history prevents tally completion — §4, §9.3), plus complaint capacity sized to the admitted-cast bound (§9.2). |

### 12.2 What wardens and insiders learn
θ colluding wardens can reconstruct **every package's ballot** — exactly v2's boundary, where
θ wardens can decrypt every ballot. New, and narrower: the **tally participants** — a θ-sized set *per attempt*: if a session aborts after key reconstruction and restarts with a different roster, every participant of every attempt that reached reconstruction capability is in the leakage set (fresh blinding cannot revoke knowledge already obtained) — (a θ-sized
set) jointly learn the revoked-package set $R$ — metadata, not contents — and any one of them
can leak it onward; non-participating wardens and the public learn nothing about $R$ (batch
pads §8.4 + blinding §10.3 close those channels, given ≥1 honest accepted dealer). The
sequencer/prover that seals a vote learns its revote linkage (§5.4) — as in v2.

### 12.3 The honest coercion statement
v3 keeps v2's informal posture (no formal receipt-freeness; revotes hidden among refreshes)
with **one new residual, stated openly**: a coercer who obtains a package's *revocation
token* — by extracting the voter's identity key, **or** by demanding a ZK proof of the
token's derivation, **or** a valid unsubmitted revote authorization — can watch the public
nullifier tree and detect whether that package was later consumed. v2's re-encryption resists
even that (testing re-encryptions is a DDH-type problem). This is the main new
coercion-relevant difference from v2 (alongside the §12.2 participant metadata); mitigations
are Track-2 research (§15). Deployments for coercion-sensitive elections should weigh it.

### 12.4 Proof-system notes
The pinned ballot STARK profile targets **≈106-bit** *conjectured* FRI soundness (18 queries × log₂32 + 16 grinding bits; ethSTARK heuristic
[ETHS]) — an explicit engineering dial (queries × log-blowup + grinding), to be raised for
high-stakes deployments, and **not** claimed as 128-bit PQ security. The Blake3
Merkle/challenger layer uses **full** Blake3 (7 rounds is the standard, not a reduction) with
256-bit digests: ~128-bit classical collision resistance — adequate for the classical target
above — while generic *quantum* collision bounds on any 256-bit hash are ~2^85 query bounds
(BHT is the generic quantum collision-search algorithm — a query-count bound under heavy memory assumptions, not a practical attack cost); the profile is therefore justified against the
classical conjectured target, not claimed as ≥102-bit end-to-end quantum security (the same
caveat applies to a Poseidon2 profile). The ~2^85 figure concerns **collision resistance —
commitments and binding**; it does not mean 256-bit *keys* have 85-bit confidentiality
(generic quantum key search is the Grover ~2^128 regime). The v2-era prototype's
three known defects (weight-bound bypass at `maxValueSum=0`; wraparound-prone comparators;
weak hiding-PCS blinding RNG with a constant fallback seed) are normatively fixed in v3
(§6.1; 256-bit CSPRNG blinding seed, fail-closed).

**Where Poseidon2 still lives, honestly.** Blake3 replaces Poseidon2 in application hashing
and the ballot proof system. Poseidon2 remains an **inherited ZisK proof-system dependency**:
a break there may compromise accepted state transitions and tally integrity, and can thereby
compromise privacy *during protocol execution* (e.g. forged transitions could mark packages
consumed without authorization and mislead honest wardens into revealing a skewed aggregate).
Passive confidentiality of archived ballot transport and masking no longer relies on
application-level Poseidon2. "Repairable" means future executions can migrate to a repaired
verifier — not that past disclosures or finalized decisions can be undone. Why the move: the
Poseidon2 cryptanalysis landscape is young and moving — round-estimate revisions [TOSC25],
the EF Poseidon attack-reward program [PINIT], and the FreeLunch family of algebraic attacks
on arithmetization-oriented primitives [FL24] — while Blake3 carries long-standing ARX
analysis. This is a conservatism call, not a response to any full-round break.

**Every published proof must be hiding, not merely sound.** The ballot STARK is not the only
proof carrying secrets: batch proofs (batch seeds, pads, revocation data), complaint proofs
(warden key seeds), dealer proofs (blinding coefficients), warden contributions (KEM seeds,
shares, payload keys) and key-registration proofs all have sensitive witnesses. Each proof
profile must therefore be verified to be **zero-knowledge/hiding**, not only sound. Known
status: the BN254 PlonK wrapper applies explicit blinding; the hiding of ZisK's *native*
VADCOP-final STARK path (ZisK's last recursion stage, the proof the wrapper wraps) is **unverified** — which makes "drop the wrapper for direct STARK
verification" (§15) a **privacy question, not only a cost change**.

### 12.5 Out of scope / inherited
EIP-4844 KZG commitments (Ethereum's own PQ roadmap), organizer/sequencer Ethereum accounts,
hybrid-mode ECDSA (by construction), and the BN254 PlonK wrapper around ZisK proofs. These
classical dependencies are **integrity-critical — and an integrity failure during execution
can compromise privacy (§12.4)**; what they cannot do — provided the published proof paths
retain their required hiding and the KEM/PRF assumptions hold — is retroactively decrypt
archived ballots (breaking a proof system's *soundness* does not by itself recover
witnesses). The wrapper is replaceable by direct on-chain STARK verification (indicative public
data point: ~5–6 MGas for a WHIR/FRI verifier on the EVM [WHIR]; not a measured cost for ZisK
proofs; and a privacy-gated change, §12.4) — tracked as the final migration phase.

---

## 13. Cost summary

| Metric | v2 | v3-PQ (estimates unless marked measured) |
|---|---|---|
| Browser proving | seconds (Groth16, 35.5 MiB key download) | projected ~2–4 s native (ν-dependent, re-laid full-Blake3 AIR at the blowup-32 profile, §6 — needs recalculation/benchmark against the §2.2 stream-masking counts; no key download; the Blake3-trees prototype measured 0.69 s native at blowup 8) |
| Ballot upload to sequencer | ~2 KB | ~20 KB package + ~195 KB proof (proof not stored on-chain) |
| DA per ballot | ~2 KB | 1.7–20.5 KB depending on ν and KEM (§8.6 table) |
| DA per refresh | ~1–2 KB | 40 B (framed) |
| Batch proving | 2.3–4.0×10^8 steps | **+ ≈0.30 s GPU per ballot for in-guest STARK verification (measured on RTX 5090 after the optimization pass: 32 verifications proven in 19.8 s; 2.62M steps each, §8.1)** — 256-ballot batches ≈ 2–3 min total; state-tree hashing −30%/byte vs v2's SHA-256; commitment recomputations +13% vs a Poseidon2 precompile |
| Tally | θ partial decryptions of one accumulator + BSGS | archive-linear warden jobs (§10.1) + one ceremony + on-chain Lagrange |
| Registry tally cap | 10^12 | 2^61 |

---

## 14. Errors and edge cases (normative)

- **voteID collision** (admission finds the leaf occupied): resample `k` (recovery mode:
  bump the counter) and re-cast — as v2. Skipped counters are harmless (§5.2 recovery scan).
- **Unsettled predecessor**: a revote consuming a predecessor not yet settled under the
  batch's starting root is rejected at admission and retried by the sequencer in a later
  batch automatically; clients should submit revotes to the sequencer that holds their
  pending vote, as in v2.
- **Duplicate revocation race** (two sequencers hold revotes of the same package): the first
  settles; the loser's re-validation drops the vote at admission (nullifier present) and
  notifies the voter — the v2 "voteID already in state" pattern.
- **Live package excluded** ($P_t \in X$): the client detects it (public $X$) and informs
  the voter they are not counted; no recovery within the election (casting is closed when
  complaints run).
- **Warden key unavailable at cast time**: the client refuses to cast (it cannot build a
  complete package); election creation already requires all ν keys registered (§4).
- **Ceremony dealer failure**: dealer excluded, session restarted with fresh masks (§10.3);
  if the roster drops below θ, the tally is lost — counted under liveness (§9.3).

---

## 15. Tracked upgrades

1. **STARK-friendly verifiable encryption** (RLWE-LPR with a Blake3-based FO transform) to
   prove warden transport at admission — removes the complaint window entirely. Requires its
   own security review before adoption.
2. **PQ re-randomizable package representation** — would restore v2-grade resistance to
   revocation-token coercion (§12.3). Open research.
3. **Locked mode** as a separately specified and reviewed extension (§4).
4. Direct on-chain STARK verification (drop the PlonK wrapper) once rollup gas permits —
   **gated on establishing the native proof path's hiding, not only its cost** (§12.4).
5. Classic McEliece transport profile for large committees [MCE].
6. **Batched complaint proofs / proof-certified exclusion-root updates** for large elections
   (one proof excluding many packages, with precise completeness and deadline semantics) —
   the per-complaint path is O(admitted casts) in the worst case (§9.2).
7. **Authenticated per-warden views / preprocessing proofs** so warden contributions don't
   re-hash every full `CanonicalPackage` (§10.1 cost model).
8. **Per-election warden keys** as an operational-lifecycle option: the §12.1 *lifetime*
   key-compromise assumption means rotating epochs does not protect old ballots if old
   secrets survive; per-election keys plus specified destruction (including backups) make the
   retention story auditable.

**First implementation target (from the external design review).** A complete, reproducible
**3-of-5, ML-KEM-768 end-to-end election prototype** — browser casting through settlement,
complaints, exclusions, the private ceremony, warden proofs, and on-chain finalization —
with these measured gates: the complete 16-field ballot relation including the revote path,
production hiding randomness, the exact pinned proof profile verified inside ZisK, full
batch proving cost, complaint throughput under adversarial load, and the complete warden
tally job (archive authentication included). Browser latency/memory and deployment limits
(electorate sizes, committee sizes, deadlines, hardware) are derived from those measurements
— not from component benchmarks.

---

## 16. References

- [DAV2] Vocdoni, *DAVINCI protocol specification v2*. https://spec.davinci.vote
- [FIPS 203] NIST, *Module-Lattice-Based Key-Encapsulation Mechanism Standard (ML-KEM)*, 2024. https://doi.org/10.6028/NIST.FIPS.203
- [FIPS 205] NIST, *Stateless Hash-Based Digital Signature Standard (SLH-DSA)*, 2024. https://doi.org/10.6028/NIST.FIPS.205
- [Sha79] A. Shamir, *How to Share a Secret*, CACM 22(11), 1979.
- [DST] Vocdoni, *davinci-stark: Plonky3 ballot proof prototype*. https://github.com/vocdoni/davinci-stark
- [P3] Polygon Zero, *Plonky3*. https://github.com/Plonky3/Plonky3
- [ZISK] Polygon, *ZisK zkVM*. https://github.com/0xPolygonHermez/zisk
- [POS2] L. Grassi et al., *Poseidon2: A Faster Version of the Poseidon Hash Function*, ePrint 2023/323.
- [TOSC25] *Poseidon and Neptune: Gröbner Basis Cryptanalysis Exploiting Subspace Trails*, IACR ToSC. https://tosc.iacr.org/index.php/ToSC/article/view/12244
- [FL24] A. Bariant et al., *The Algebraic FreeLunch: Efficient Gröbner Basis Attacks Against Arithmetization-Oriented Primitives*, CRYPTO 2024 (ePrint 2024/347).
- [PINIT] Ethereum Foundation, *Poseidon Initiative — cryptanalysis attack reward program*. https://www.poseidon-initiative.info
- [B3] J. O'Connor, J.-P. Aumasson, S. Neves, Z. Wilcox-O'Hearn, *BLAKE3: one function, fast everywhere*. https://blake3.io
- [ETHS] StarkWare, *ethSTARK Documentation*, ePrint 2021/582.
- [EIP4844] V. Buterin et al., *EIP-4844: Shard Blob Transactions*, 2022.
- [IR89] R. Impagliazzo, S. Rudich, *Limits on the Provable Consequences of One-Way Permutations*, STOC 1989.
- [NOAH] M. Dahl et al., *Noah's Ark: Efficient Threshold-FHE Using Noise Flooding*, WAHC/CCS 2023.
- [TEV] J. Alizadeh, *Threshold Post-Quantum E-Voting from Lattice Commitments*, ePrint 2026/2500.
- [PQK] N. Huber et al., *PQKryvos: Post-Quantum Secure E-Voting With Flexible Ballot Formats and Public Tally-Hiding*, PoPETs 2026.
- [MCE] D. J. Bernstein et al., *Classic McEliece*. https://classic.mceliece.org
- [KEMB] *ML-KEM WebAssembly implementations and benchmarks*. https://github.com/dchest/mlkem-wasm
- [WHIR] *EVM Verification of WHIR over a 31-bit Field*, ethresear.ch, 2025.
