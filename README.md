## TrustRail — Reusable AI-Arbitration Infrastructure for GenLayer

Every project that needs a dispute resolved - did this freelancer's work meet the brief, did this insurance claim's evidence hold up, was this bounty actually completed - ends up writing the same thing from scratch: fetch some evidence, prompt an LLM, wire up `eq_principle` for consensus, handle fund custody and settlement.

TrustRail is that logic, built once, as a reusable primitive any builder can deploy against their own case instead of reinventing it.

**Live contracts (GenLayer Studio): two deployed case instances proving reuse across domains:**
- Bounty verification: `0x0eF43B8D60c41c89E8B14Ca8D9Fee8B750601188`
- Insurance claim verification: `0x92565ebB0a44BF69669390A79CDF56010a84c63B`

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

1. **Deploy** - a case is created with an initiator, a respondent, a plain-language case description, domain-specific evaluation criteria, and an optional stake amount.
2. **Fund** *(optional)* - if a stake amount is set, the initiator deposits it via `fund_case()`, a payable method. The contract holds it in custody.
3. **Submit evidence** - the respondent submits a public URL supporting their side of the case.
4. **Resolve** - either party triggers resolution. GenLayer validators independently fetch the evidence, evaluate it against the case's own criteria text (not a hardcoded prompt), and reach consensus via `prompt_non_comparative` - validators agree on the verdict, not on identical wording.
5. **Settle** - if a stake was funded, the contract calls `gl.get_contract_at(...).emit_transfer(...)` to split the stake between initiator and respondent according to the AI's `percent_to_respondent` verdict, in the same transaction. If no funds were involved, it just records the verdict on-chain as a verifiable outcome.

## Why this needs GenLayer

Reading live evidence and judging whether it satisfies open-ended, domain-specific criteria isn't something a traditional smart contract can do - there's no oracle for "is this good enough." GenLayer's Intelligent Contracts make that judgment possible, with decentralized validators reaching real consensus on a subjective call, while the settlement itself
stays fully deterministic in code.

## Project structure

```
trustrail/
├── contracts/
│   └── trustrail_case.py     # the reusable Intelligent Contract
├── docs/
│   └── incident-report.txt    # sample evidence used in the insurance-claim demo case
└── index.html                  # standalone frontend (no build step needed)
```

## How to run the frontend

Open `index.html` in a browser - it imports `genlayer-js` directly from a CDN via ES modules, so no `npm install` or build step is required. It's already wired to the deployed contract address above. This repo's live demo is hosted via GitHub Pages.

The frontend generates and persists a throwaway private key in the browser's `localStorage` on first "Connect Wallet" - in this deployment that generated address is the **respondent** account listed above, so `submit_evidence` and `resolve` can be called directly from the frontend.

`fund_case` is initiator-only and was executed from the initiator account via GenLayer Studio - both are real, independently controlled accounts matching the configuration documented above.

If you're deploying your own case, edit the `CONTRACT_ADDRESS` constant near the top of the `<script>` block in `index.html`, and provide your own `case_description` / `criteria_text` at deploy time - no code changes needed for a new domain.

## Known scope limitations (being upfront about this)

- Each case is its own deployed contract instance. There's no on-chain factory yet to spin up new cases without redeploying - a natural next step for wider adoption would be a factory contract that other dApps call directly to create cases.

- Only a single evidence URL is supported per case right now. Multi-source evidence (like cross-referencing several URLs) is a reasonable extension.

- No appeal mechanism yet — resolution is final once `resolve()` is called.

## Reusability proof - same contract, two unrelated domains

To prove this is genuinely reusable and not a relabeled single-purpose escrow, the **exact same contract code** was deployed twice for two unrelated domains, with no code changes - only different constructor
arguments:

**Case 1 — Open-source bounty verification**
`0x0eF43B8D60c41c89E8B14Ca8D9Fee8B750601188`
Evidence: a generic "Hello World" page with no relevant code.
Verdict: `0%` to respondent — correctly rejected, full refund to initiator.

Live: `https://keplr32b.github.io/trustrail/?contract=0x0eF43B8D60c41c89E8B14Ca8D9Fee8B750601188`

**Case 2 - Insurance claim verification**
`0x92565ebB0a44BF69669390A79CDF56010a84c63B`
Evidence: a detailed incident report describing accidental laptop screen damage with a professional repair assessment.
Verdict: `100%` to respondent - correctly approved, full payment released.

Live: `https://keplr32b.github.io/trustrail/`

Same contract, same consensus logic, opposite verdicts, both correctly reasoned against domain-specific criteria that were never hardcoded into the contract.

## Testing it end-to-end

1. Deploy `contracts/trustrail_case.py` in GenLayer Studio with your initiator, respondent, case description, criteria text, and amount (in wei-equivalent units, or `0` for a verdict-only case with no funds).

2. If `amount > 0`, call `fund_case` from the **initiator** address, sending exactly the agreed amount as the transaction value.

3. Call `submit_evidence` from the **respondent** address with a public URL.

4. Call `resolve` from either party. This fetches the evidence, gets an AI verdict against your own criteria text, and — if funded - transfers GEN accordingly.

5. Call `get_status` / `get_verdict` / `get_outcome_percent` / `get_balance` to see the outcome and reasoning.

This was tested using a bounty-verification case (case description:
implement binary search with edge-case handling and tests) against a deliberately mismatched evidence URL — the AI correctly returned `0%` to the respondent with reasoning explaining the evidence contained no relevant code, and the full staked amount was returned to the initiator on-chain.
