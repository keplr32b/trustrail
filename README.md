## TrustRail - Reusable AI-Arbitration Infrastructure for GenLayer.

Every project that needs a dispute resolved - did this freelancer's work meet the brief, did this insurance claim's evidence hold up, was this bounty actually completed - ends up writing the same thing from scratch: fetch some
evidence, prompt an LLM, wire up `eq_principle` for consensus, handle fund custody and settlement.

TrustRail is that logic, built once, as a reusable
primitive any builder can deploy against their own case instead of reinventing it.

**Live contracts (GenLayer Studio) - two deployed case instances proving reuse across domains:**
- Bounty verification (fixed EOA-transfer version): `0x9E5Cd00B9f2E1dfe1bE097E033e9d5a08f2e79c9`
- Insurance claim verification (fixed EOA-transfer version): `0x9805fc524368bdEFbB2D95366C1beaFCb3dB23F8`

**Note on a fixed bug:** an earlier version of this contract sent settlement value to EOA wallet addresses using `gl.get_contract_at(...)`, which the GenLayer docs specify is for Intelligent-Contract-to-Intelligent-Contract transfers only. 

Sending to a plain wallet requires the `@gl.evm.contract_
interface` pattern instead. This has been fixed and verified on-chain: see transaction `0x1ca75cf50387a5a112b38cde035a85346b86a4b8a66dbfaa4a8272d5f7d3b636`, a `Send` transaction of 1 GEN from the contract directly to the initiator's EOA wallet, confirmed `FINALIZED`.

**Accounts used in the live demo:**
- **Initiator:** `0xCa44BB8223A7d15e1B3777Bac319f03f9aEC9D91`
- **Respondent:** `0x870f1c2e54c04494263eC01C23565DaB29c8f038`

## What makes this different from a single-purpose escrow

FairEscrow-style contracts hardcode one domain: "does this deliverable match this brief." TrustRail takes the **case description** and **evaluation criteria** as constructor arguments instead of hardcoding them, so the same
contract pattern works for:

- Freelance work verification
- Open-source bounty completion
- Insurance claim evidence review
- SLA / uptime compliance checks
- Warranty and product-defect claims
- Any dispute where one party makes a claim and the other submits evidence

A builder deploys their own instance with their own domain-specific criteria text - they don't write a single line of arbitration or consensus code.

## How it works

1. **Deploy:** - a case is created with an initiator, a respondent, a plain-language case description, domain-specific evaluation criteria, and an optional stake amount.

2. **Fund:** *(optional)* - if a stake amount is set, the initiator deposits it via `fund_case()`, a payable method. The contract holds it in custody.

3. **Submit evidence:** - the respondent submits a public URL supporting their side of the case.

4. **Resolve:** - either party triggers resolution. GenLayer validators independently fetch the evidence, evaluate it against the case's own criteria text (not a hardcoded prompt), and reach consensus via `prompt_non_comparative` - validators agree on the verdict, not on identical wording.

5. **Settle:** - if a stake was funded, the contract calls `gl.get_contract_at(...).emit_transfer(...)` to split the stake between initiator and respondent according to the AI's `percent_to_respondent` verdict, in the same transaction. If no funds were involved, it just records the verdict on-chain as a verifiable outcome.

## Why this needs GenLayer

Reading live evidence and judging whether it satisfies open-ended, domain-specific criteria isn't something a traditional smart contract can do - there's no oracle for "is this good enough."

GenLayer's Intelligent Contracts make that judgment possible, with decentralized validators reaching real consensus on a subjective call, while the settlement itself stays fully deterministic in code.

## Project structure

```
trustrail/
├── contracts/
│   └── trustrail_case.py       # the reusable Intelligent
├── docs/
│   └── incident-report.txt      # sample evidence used in the insurance-claim demo case
├── tests/
│   └── test_trustrail_e2e.py    # automated gltest suite
├── README.md
└── index.html                    # standalone frontend (no build step needed)
```

## How to run the frontend

Open `index.html` in a browser - it imports `genlayer-js` directly from a CDN via ES modules, so no `npm install` or build step is required. It's already wired to the deployed contract address above. This repo's live demo is hosted via GitHub Pages.

The frontend supports importing a real private key for an authorized party, or generating a fresh one for a new case - see "Connecting as an authorized party" below for details.

If you're deploying your own case, edit the `CONTRACT_ADDRESS` constant near the top of the `<script>` block in `index.html` (or use the `?contract=` URL parameter), and provide your own `case_description` / `criteria_text` at deploy time - no code changes needed for a new domain.

## Known scope limitations (being upfront about this)

- Each case is its own deployed contract instance. There's no on-chain factory yet to spin up new cases without redeploying - a natural next step for wider adoption would be a factory contract that other dApps call directly to create cases.

- Only a single evidence URL is supported per case right now. Multi-source evidence (like cross-referencing several URLs) is a reasonable extension.

- No appeal mechanism yet - resolution is final once `resolve()` is called.

## Reusability proof - same contract, two unrelated domains

To prove this is genuinely reusable and not a relabeled single-purpose escrow, the **exact same contract code** was deployed twice for two unrelated domains, with no code changes - only different constructor arguments:

**Case 1: Open-source bounty verification**
`0x9E5Cd00B9f2E1dfe1bE097E033e9d5a08f2e79c9`
Evidence: a generic "Hello World" page with no relevant code.
Verdict: `0%` to respondent - correctly rejected, full refund sent to the initiator's actual EOA wallet, verified via transaction
`0x1ca75cf50387a5a112b38cde035a85346b86a4b8a66dbfaa4a8272d5f7d3b636`.

Live: `https://keplr32b.github.io/trustrail/?contract=0x9E5Cd00B9f2E1dfe1bE097E033e9d5a08f2e79c9`

**Case 2: Insurance claim verification**
`0x9805fc524368bdEFbB2D95366C1beaFCb3dB23F8`
Evidence: `a detailed incident report describing accidental laptop screen
damage with a professional repair assessment.`
Verdict: `100%` to respondent — correctly approved, full payment sent to
the respondent's actual EOA wallet `0x870f1c2e54c04494263eC01C23565DaB29c8f038`,
confirmed on-chain as a Send transaction of 1 GEN, FINALIZED.

Live: https://keplr32b.github.io/trustrail/?contract=0x9805fc524368bdEFbB2D95366C1beaFCb3dB23F8

Same contract, same consensus logic, opposite verdicts, both correctly reasoned against domain-specific criteria that were never hardcoded into the contract.

## Connecting as an authorized party

The frontend does **not** rely on a randomly-generated throwaway wallet to act as a case party. On first load it offers two options:

- **Import Private Key**: paste the private key of a real, pre-existing account that already holds the `initiator` or `respondent` role on a deployed case. This is how any genuine party to a dispute connects - the same way you'd import a wallet into MetaMask to interact with any other dApp.

- **"or generate a new identity"**: a secondary option for deploying and testing a *brand-new* case, where you control both the initiator and respondent addresses from the start.

The account persists in the browser's `localStorage` for convenience across reloads, but it is never auto-generated to "stand in" for an authorized party - the address used must already match the role assigned at deploy time.

## Fresh-user end-to-end test (reproducible from a clean browser)

This walks through the exact flow a brand-new user - with no prior connection to this repo - can follow to deploy a case, act as respondent, submit evidence, and trigger resolution, entirely from the app:

1. Generate a fresh keypair (e.g. open `index.html` in a private/incognito window, click **"or generate a new identity"**, then use the **full address** shown under the wallet badge - tap it to reveal the complete value).

2. In GenLayer Studio, deploy `contracts/trustrail_case.py` with that address as the `respondent`, any `initiator` address you control, your own `case_description` / `criteria_text`, and an `amount` (or `0` for a no-stake case).

3. If `amount > 0`, call `fund_case` from the `initiator` address in Studio, sending the exact agreed amount as the transaction value.

4. Back in the same incognito browser session (so the generated key is still in `localStorage`), open `index.html?contract=<your new address>`. The wallet badge should already show the respondent address from step 1 - no re-import needed, since it's the same browser session.

5. Go to **Submit Evidence**, paste any public URL, and submit - this is signed by the respondent key generated in step 1.

6. Go to **Resolve & Verdict** and click **Resolve** - either party can call this. Wait for consensus; the verdict and, if funded, the actual GEN settlement will appear.

This is exactly how **Case 2 (insurance claim)** documented below was produced, end-to-end, from the live app.

## Automated tests

`tests/test_trustrail_e2e.py` uses `genlayer-test` (`gltest`) to exercise the contract programmatically rather than only via manual steps:

- **Fresh-party authorization + full settlement**: a brand-new account, created inside the test itself (never hardcoded anywhere in the repo), is assigned the respondent role, submits evidence, and the case is resolved - with the final `status`, `outcome_percent`, and `balance` asserted on-chain.

- **Unauthorized rejection**: an unrelated third account is confirmed to be rejected when attempting to submit evidence, and case state is confirmed unchanged.

- **Unfunded rejection**: evidence submission is confirmed to fail if the case was never funded.

Run with:
```bash
pip install genlayer-test
gltest tests/test_trustrail_e2e.py
```

## Testing it end-to-end

1. Deploy `contracts/trustrail_case.py` in GenLayer Studio with your initiator, respondent, case description, criteria text, and amount (in wei-equivalent units, or `0` for a verdict-only case with no funds).

2. If `amount > 0`, call `fund_case` from the **initiator** address, sending exactly the agreed amount as the transaction value.

3. Call `submit_evidence` from the **respondent** address with a public URL.

4. Call `resolve` from either party. This fetches the evidence, gets an AI verdict against your own criteria text, and — if funded - transfers GEN accordingly.

5. Call `get_status` / `get_verdict` / `get_outcome_percent` / `get_balance` to see the outcome and reasoning.

This was tested using a bounty-verification case (case description:
implement binary search with edge-case handling and tests) against a deliberately mismatched evidence URL - the AI correctly returned `0%` to the respondent with reasoning explaining the evidence contained no relevant code, and the full staked amount was returned to the initiator on-chain.
