"""
End-to-end tests for TrustRailCase (gltest / genlayer-test).

Covers:
  1. Fresh respondent can submit evidence and drive settlement
  2. Unauthorized account cannot submit evidence
  3. Unfunded case rejects evidence

Note: resolve() uses live LLM consensus. The mismatched-evidence path
expects a low award to the respondent; we assert outcome_percent == 0
only as the intended demo path — under rare LLM variance re-run the test.
"""

from pathlib import Path

from gltest import get_contract_factory, get_default_account, create_accounts
from gltest.assertions import tx_execution_succeeded

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
CASE_AMOUNT = 1_000_000_000_000_000_000  # 1 GEN wei-equivalent

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
    factory = get_contract_factory(
        contract_file_path=CONTRACTS_DIR / "trustrail_case.py"
    )
    return factory.build_contract(contract.address, account=account)


def test_fresh_party_authorization_evidence_and_settlement():
    initiator = get_default_account()
    fresh_respondent = create_accounts(1)[0]

    contract = _deploy_case(initiator, fresh_respondent)
    assert contract.get_status().call() == "awaiting_funding"

    fund_receipt = contract.fund_case().transact(value=CASE_AMOUNT)
    assert tx_execution_succeeded(fund_receipt)
    assert contract.get_status().call() == "open"
    assert contract.get_balance().call() == CASE_AMOUNT

    respondent_contract = _as(contract, fresh_respondent)
    submit_receipt = respondent_contract.submit_evidence(
        MISMATCHED_EVIDENCE_URL
    ).transact()
    assert tx_execution_succeeded(submit_receipt)
    assert contract.get_status().call() == "evidence_submitted"
    assert contract.get_evidence().call() == MISMATCHED_EVIDENCE_URL

    resolve_receipt = contract.resolve().transact(
        wait_interval=10000,
        wait_retries=30,
    )
    assert tx_execution_succeeded(resolve_receipt)

    final_status = contract.get_status().call()
    outcome_percent = int(contract.get_outcome_percent().call())
    final_balance = contract.get_balance().call()

    assert final_status in (
        "resolved_initiator",
        "resolved_respondent",
        "resolved_split",
    )
    assert final_balance == 0
    assert len(contract.get_verdict().call()) > 0
    assert outcome_percent == 0
    assert final_status == "resolved_initiator"


def test_unauthorized_account_cannot_submit_evidence():
    initiator = get_default_account()
    real_respondent, unrelated_third_party = create_accounts(2)

    contract = _deploy_case(initiator, real_respondent)
    fund_receipt = contract.fund_case().transact(value=CASE_AMOUNT)
    assert tx_execution_succeeded(fund_receipt)

    intruder_contract = _as(contract, unrelated_third_party)
    try:
        rejected_receipt = intruder_contract.submit_evidence(
            MISMATCHED_EVIDENCE_URL
        ).transact()
        assert not tx_execution_succeeded(rejected_receipt)
    except Exception:
        pass

    assert contract.get_status().call() == "open"
    assert contract.get_evidence().call() == ""


def test_unfunded_case_rejects_evidence():
    initiator = get_default_account()
    fresh_respondent = create_accounts(1)[0]

    contract = _deploy_case(initiator, fresh_respondent)
    respondent_contract = _as(contract, fresh_respondent)

    try:
        rejected_receipt = respondent_contract.submit_evidence(
            MISMATCHED_EVIDENCE_URL
        ).transact()
        assert not tx_execution_succeeded(rejected_receipt)
    except Exception:
        pass

    assert contract.get_status().call() == "awaiting_funding"
