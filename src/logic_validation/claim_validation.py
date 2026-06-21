from __future__ import annotations

import re

from typing import Any

from .features import months_between, parse_datetime


STATUS_SUPPORTED = "supported"
STATUS_PARTIAL = "partially_supported"
STATUS_CONTRADICTED = "contradicted"
STATUS_UNSUPPORTED = "unsupported"
STATUS_NOT_CHECKABLE = "not_checkable"


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def lower(value: Any) -> str:
    return normalize_text(value).lower()


def approx_equal(left: Any, right: Any, tolerance: float = 1.0) -> bool:
    try:
        return abs(float(left) - float(right)) <= tolerance
    except (TypeError, ValueError):
        return False


def claim(
    claim_text: str,
    claim_type: str,
    status: str,
    evidence: list[str],
) -> dict[str, Any]:
    return {
        "claim": claim_text,
        "type": claim_type,
        "status": status,
        "evidence": evidence,
    }


def extract_approx_npr_amount(reason: str) -> float | None:
    match = re.search(r"NPR\s+([0-9][0-9,]*(?:\.\d+)?)", reason, re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def extract_transaction_count(reason: str) -> int | None:
    match = re.search(r"conducted\s+(\d+)\s+transaction", reason, re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def extract_named_counterparties(reason: str) -> str | None:
    match = re.search(
        r"principal counterparties observed were\s+([^\.]+)",
        reason,
        re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(1).strip()


def has_tenure_years_claim(reason: str) -> bool:
    return bool(
        re.search(
            r"\b(for\s+(some|several|many|multiple)\s+years|for\s+years|long[- ]standing)\b",
            reason,
            re.IGNORECASE,
        )
    )


def validate_account_holder(
    reason: str,
    current: dict[str, Any],
    account_kyc: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    match = re.search(r"account held by\s+(.+?)\s+after", reason, re.IGNORECASE)
    if not match:
        return []

    mentioned_name = match.group(1).strip()
    report_name = normalize_text(current.get("from_account_name"))
    kyc_name = normalize_text(account_kyc.get("name") if account_kyc else None)

    if lower(mentioned_name) == lower(report_name) == lower(kyc_name):
        status = STATUS_SUPPORTED
    elif lower(mentioned_name) in {lower(report_name), lower(kyc_name)}:
        status = STATUS_PARTIAL
    else:
        status = STATUS_CONTRADICTED

    return [
        claim(
            f"Account is held by {mentioned_name}",
            "account_holder",
            status,
            [
                f"reason.account_holder={mentioned_name}",
                f"str_reports.from_account_name={report_name or None}",
                f"accounts.name={kyc_name or None}",
            ],
        )
    ]


def validate_institution(
    reason: str,
    current: dict[str, Any],
    account_kyc: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    match = re.search(r"compliance desk at\s+([A-Z0-9_-]+)", reason, re.IGNORECASE)
    if not match:
        return []

    mentioned = match.group(1).strip()
    report_institution = normalize_text(current.get("from_institution"))
    kyc_institution = normalize_text(account_kyc.get("institution") if account_kyc else None)

    if lower(mentioned) == lower(report_institution) == lower(kyc_institution):
        status = STATUS_SUPPORTED
    elif lower(mentioned) in {lower(report_institution), lower(kyc_institution)}:
        status = STATUS_PARTIAL
    else:
        status = STATUS_CONTRADICTED

    return [
        claim(
            f"Compliance desk institution is {mentioned}",
            "institution",
            status,
            [
                f"reason.institution={mentioned}",
                f"str_reports.from_institution={report_institution or None}",
                f"accounts.institution={kyc_institution or None}",
            ],
        )
    ]


def validate_amount(reason: str, current: dict[str, Any], transaction: dict[str, Any] | None) -> list[dict[str, Any]]:
    amount = extract_approx_npr_amount(reason)
    if amount is None:
        return []

    str_amount = current.get("tx_amount_local")
    tx_amount = transaction.get("amount_local_npr") if transaction else None

    status = STATUS_SUPPORTED if approx_equal(amount, str_amount, tolerance=5) else STATUS_CONTRADICTED
    if status == STATUS_SUPPORTED and tx_amount is not None and not approx_equal(amount, tx_amount, tolerance=5):
        status = STATUS_PARTIAL

    return [
        claim(
            f"Transaction amount is approximately NPR {amount:,.0f}",
            "amount",
            status,
            [
                f"reason.amount_npr={amount:,.2f}",
                f"str_reports.tx_amount_local={str_amount}",
                f"transactions.amount_local_npr={tx_amount}",
            ],
        )
    ]


def validate_cross_border(reason: str, current: dict[str, Any], transaction: dict[str, Any] | None, ml_features: dict[str, Any] | None) -> list[dict[str, Any]]:
    if "cross-border" not in lower(reason):
        return []

    from_country = current.get("from_country")
    to_country = current.get("to_country")
    str_cross_border = bool(from_country and to_country and str(from_country).upper() != str(to_country).upper())
    tx_cross_border = transaction.get("cross_border_flag") if transaction else None
    ml_cross_border = ml_features.get("cross_border_flag") if ml_features else None

    if str_cross_border and tx_cross_border in (1, True, None) and ml_cross_border in (1, True, None):
        status = STATUS_SUPPORTED
    elif str_cross_border:
        status = STATUS_PARTIAL
    else:
        status = STATUS_CONTRADICTED

    return [
        claim(
            "Transaction was cross-border",
            "cross_border",
            status,
            [
                f"str_reports.from_country={from_country}",
                f"str_reports.to_country={to_country}",
                f"transactions.cross_border_flag={tx_cross_border}",
                f"ml_features.cross_border_flag={ml_cross_border}",
            ],
        )
    ]


def validate_transaction_count(reason: str, ml_features: dict[str, Any] | None) -> list[dict[str, Any]]:
    count = extract_transaction_count(reason)
    if count is None:
        return []

    tx_count_10 = ml_features.get("tx_count_10") if ml_features else None
    tx_count_30 = ml_features.get("tx_count_30") if ml_features else None
    status = STATUS_SUPPORTED
    if tx_count_10 is not None and int(tx_count_10) < count:
        status = STATUS_PARTIAL

    return [
        claim(
            f"Customer conducted {count} transaction(s)",
            "transaction_count",
            status,
            [
                f"reason.transaction_count={count}",
                f"ml_features.tx_count_10={tx_count_10}",
                f"ml_features.tx_count_30={tx_count_30}",
            ],
        )
    ]


def validate_sanctions(reason: str, account_kyc: dict[str, Any] | None, ml_features: dict[str, Any] | None) -> list[dict[str, Any]]:
    if "sanctions" not in lower(reason):
        return []

    sanctions_hit = account_kyc.get("sanctions_hit") if account_kyc else None
    ml_sender_sanctions = ml_features.get("sender_sanctions") if ml_features else None

    if sanctions_hit == 0 and ml_sender_sanctions in (0, None):
        status = STATUS_SUPPORTED
    elif sanctions_hit is None:
        status = STATUS_NOT_CHECKABLE
    else:
        status = STATUS_CONTRADICTED

    return [
        claim(
            "No sanctions matches were identified",
            "sanctions",
            status,
            [
                f"accounts.sanctions_hit={sanctions_hit}",
                f"ml_features.sender_sanctions={ml_sender_sanctions}",
            ],
        )
    ]


def validate_adverse_media(reason: str) -> list[dict[str, Any]]:
    if "adverse media" not in lower(reason):
        return []
    return [
        claim(
            "No adverse media matches were identified",
            "adverse_media",
            STATUS_NOT_CHECKABLE,
            ["No adverse-media screening field is available in the provided datasets."],
        )
    ]


def validate_account_tenure(reason: str, current: dict[str, Any], account_kyc: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not has_tenure_years_claim(reason):
        return []

    opened = parse_datetime(account_kyc.get("opened") if account_kyc else current.get("from_account_opened"))
    submission = parse_datetime(current.get("submission_date"))
    tenure_months = months_between(opened, submission)

    if tenure_months is None:
        status = STATUS_NOT_CHECKABLE
    elif tenure_months >= 24:
        status = STATUS_SUPPORTED
    elif tenure_months >= 12:
        status = STATUS_PARTIAL
    else:
        status = STATUS_CONTRADICTED

    return [
        claim(
            "Customer has been with the institution for some years",
            "account_tenure",
            status,
            [
                f"accounts.opened={account_kyc.get('opened') if account_kyc else None}",
                f"str_reports.from_account_opened={current.get('from_account_opened')}",
                f"str_reports.submission_date={current.get('submission_date')}",
                f"computed.account_age_months_at_submission={tenure_months}",
            ],
        )
    ]


def validate_rapid_succession(reason: str, ml_features: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not re.search(r"\brapid succession\b|\bvelocity\b|\ba number of the transfers\b", reason, re.IGNORECASE):
        return []

    tx_count_10 = ml_features.get("tx_count_10") if ml_features else None
    tx_count_30 = ml_features.get("tx_count_30") if ml_features else None
    velocity = ml_features.get("velocity_sum_10tx") if ml_features else None

    if tx_count_10 is None and tx_count_30 is None:
        status = STATUS_NOT_CHECKABLE
    elif int(tx_count_10 or 0) > 1 or int(tx_count_30 or 0) > 1:
        status = STATUS_SUPPORTED
    else:
        status = STATUS_CONTRADICTED

    return [
        claim(
            "Transfers were executed in rapid succession or showed elevated velocity",
            "velocity",
            status,
            [
                f"ml_features.tx_count_10={tx_count_10}",
                f"ml_features.tx_count_30={tx_count_30}",
                f"ml_features.velocity_sum_10tx={velocity}",
            ],
        )
    ]



def validate_counterparty(reason: str) -> list[dict[str, Any]]:
    counterparty = extract_named_counterparties(reason)
    if not counterparty:
        return []
    return [
        claim(
            f"Principal counterparty was {counterparty}",
            "counterparty",
            STATUS_UNSUPPORTED,
            [
                "No provided dataset column confirms narrative counterparty names.",
                "graph_edges contains account IDs, not person/counterparty names.",
            ],
        )
    ]


def validate_income_profile(reason: str) -> list[dict[str, Any]]:
    if "income profile" not in lower(reason):
        return []
    return [
        claim(
            "Customer KYC file lists a modest declared income profile",
            "kyc_income_profile",
            STATUS_NOT_CHECKABLE,
            ["accounts.csv contains risk_grade but no declared income field."],
        )
    ]


def validate_reason_claims(evidence_packet: dict[str, Any]) -> dict[str, Any]:
    reason = evidence_packet.get("reason") or ""
    current = evidence_packet.get("current_report") or {}
    account_kyc = evidence_packet.get("account_kyc")
    transaction = evidence_packet.get("matched_transaction")
    ml_features = evidence_packet.get("ml_features")

    validations: list[dict[str, Any]] = []
    validators = [
        lambda: validate_account_holder(reason, current, account_kyc),
        lambda: validate_institution(reason, current, account_kyc),
        lambda: validate_amount(reason, current, transaction),
        lambda: validate_cross_border(reason, current, transaction, ml_features),
        lambda: validate_transaction_count(reason, ml_features),
        lambda: validate_sanctions(reason, account_kyc, ml_features),
        lambda: validate_adverse_media(reason),
        lambda: validate_account_tenure(reason, current, account_kyc),
        lambda: validate_rapid_succession(reason, ml_features),
        lambda: validate_counterparty(reason),
        lambda: validate_income_profile(reason),
    ]

    for validator in validators:
        validations.extend(validator())

    status_counts = {
        status: sum(1 for item in validations if item["status"] == status)
        for status in [
            STATUS_SUPPORTED,
            STATUS_PARTIAL,
            STATUS_CONTRADICTED,
            STATUS_UNSUPPORTED,
            STATUS_NOT_CHECKABLE,
        ]
    }

    if not validations:
        assessment = "No checkable narrative claims were detected."
    elif status_counts[STATUS_CONTRADICTED]:
        assessment = "The narrative contains at least one claim contradicted by available data."
    elif status_counts[STATUS_UNSUPPORTED]:
        assessment = "The narrative is partly supported, but some claims lack evidence in the available data."
    else:
        assessment = "The detected narrative claims are supported or not checkable with the available data."

    return {
        "report_id": current.get("report_id"),
        "overall_assessment": assessment,
        "status_counts": status_counts,
        "claim_validations": validations,
        "data_quality_flags": evidence_packet.get("data_quality_flags", []),
    }
