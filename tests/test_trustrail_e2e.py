"""
End-to-end test for TrustRailCase.

Covers exactly what a fresh party interacting with a freshly deployed case
would experience:
  1. A brand-new respondent account (not hardcoded, not pre-arranged) is
     created and used to submit evidence -- proving the contract authorizes
     based on the address assigned at deploy time, not on any special
     wallet setup.
  2. An unrelated third account is rejected when it tries to act as the
     respondent -- proving authorization is actually enforced, not just
     assumed.
  3. Resolution is triggered and the final settlement state (status,
     outcome percentage, and contract balance) is asserted on-chain.

Run with:
    pip install genlayer-test
    gltest tests/test_trustrail_e2e.py
(configure the target network in gltest's config first -- see the
genlayer-test docs for localnet/studionet/testnet setup)
"""

from pathlib import Path

from gltest import get_contract_factory, get_default_account, create_accounts

CONTRACTS_DIR = Path(__file__).parent.parent / "contracts"

CASE_DESCRIPTION = (
    "This case verifies completion of a small coding bounty: implement a "
    "working binary search function in Python with edge-case handling and "
    "at least one unit test."
)
CRITERIA_TEXT = (
    "Award full payment only if the evidence contains actual working "
    "Python code implementing binary search, with visible edge-case "
    "handling and at least one test. Award zero credit if the evidence "
    "contains no relevant code at all, or is unrelated to the task "
    "described."
)
CASE_AMOUNT = 1_000_000_000_000_000_000  # 1 GEN, wei-equivalent

# Deliberately mismatched evidence -- content unrelated to the case, so the
# expected on-chain verdict is deterministic: 0% to the respondent.
MISMATCHED_EVIDENCE_URL = (
    "https://raw.githubusercontent.com/octocat/Hello-World/master/README"
)


def _deploy_case(initiator, respondent, amount=CASE_AMOUNT):
    factory = get_contract_factory(
        contract_file_path=CONTRACTS_DIR / "trustrail_case.py"
    )
    return factory.deploy(
        account=initiator,
        args=[
            initiator.address,
            respondent.address,
            CASE_DESCRIPTION,
            CRITERIA_TEXT,
            amount,
        ],
    )


def _as(contract, account):
    """Return a handle to the same deployed contract, acting as `account`."""
    factory = get_contract_factory(
        contract_file_path=CONTRACTS_DIR / "trustrail_case.py"
    )
    return factory.build_contract(contract.address, account=account)


def test_fresh_party_authorization_evidence_and_settlement():
    """
    A brand-new respondent account (created fresh in this test, never
    referenced anywhere else in the repo) should be able to:
      - receive the respondent role at deploy time
      - submit evidence once the case is funded
      - have that evidence drive a real, on-chain settlement
    """
    initiator = get_default_account()
    fresh_respondent = create_accounts(1)[0]  # <-- the "fresh party"

    contract = _deploy_case(initiator, fresh_respondent)

    assert contract.get_status().call() == "awaiting_funding"

    # Initiator funds the case.
    fund_receipt = contract.fund_case().transact(value=CASE_AMOUNT)
    assert fund_receipt.status == "ACCEPTED"
    assert contract.get_status().call() == "open"
    assert contract.get_balance().call() == CASE_AMOUNT

    # The freshly created respondent submits evidence -- no pre-arranged
    # wallet, no hardcoded address, just the account assigned at deploy.
    respondent_contract = _as(contract, fresh_respondent)
    submit_receipt = respondent_contract.submit_evidence(
        MISMATCHED_EVIDENCE_URL
    ).transact()
    assert submit_receipt.status == "ACCEPTED"
    assert contract.get_status().call() == "evidence_submitted"
    assert contract.get_evidence().call() == MISMATCHED_EVIDENCE_URL

    # Either party can resolve; use the initiator here.
    resolve_receipt = contract.resolve().transact()
    assert resolve_receipt.status == "ACCEPTED"

    # Final settlement state, asserted on-chain.
    final_status = contract.get_status().call()
    outcome_percent = contract.get_outcome_percent().call()
    final_balance = contract.get_balance().call()

    assert final_status == "resolved_initiator"
    assert outcome_percent == 0
    assert final_balance == 0  # full amount settled, nothing left in custody
    assert len(contract.get_verdict().call()) > 0  # reasoning recorded


def test_unauthorized_account_cannot_submit_evidence():
    """
    An account with no relationship to the case -- not the respondent
    assigned at deploy time -- must be rejected when attempting to submit
    evidence. This is what makes the authorization real rather than
    assumed.
    """
    initiator = get_default_account()
    real_respondent, unrelated_third_party = create_accounts(2)

    contract = _deploy_case(initiator, real_respondent)
    contract.fund_case().transact(value=CASE_AMOUNT)

    # The unrelated account is NOT the respondent and must be rejected.
    intruder_contract = _as(contract, unrelated_third_party)
    rejected_receipt = intruder_contract.submit_evidence(
        MISMATCHED_EVIDENCE_URL
    ).transact()
    assert rejected_receipt.status != "ACCEPTED"

    # State must be unchanged -- still open, no evidence recorded.
    assert contract.get_status().call() == "open"
    assert contract.get_evidence().call() == ""


def test_unfunded_case_rejects_evidence():
    """
    If the initiator never funds the case, the respondent should not be
    able to submit evidence.
    """
    initiator = get_default_account()
    fresh_respondent = create_accounts(1)[0]

    contract = _deploy_case(initiator, fresh_respondent)

    # No fund_case call here -- case stays in "awaiting_funding".
    respondent_contract = _as(contract, fresh_respondent)
    rejected_receipt = respondent_contract.submit_evidence(
        MISMATCHED_EVIDENCE_URL
    ).transact()
    assert rejected_receipt.status != "ACCEPTED"
    assert contract.get_status().call() == "awaiting_funding"
