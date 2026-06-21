from __future__ import annotations

import argparse
import json
from datetime import datetime
from statistics import mean
from typing import Any, Mapping

from .database import connect, database_url


DATE_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d",
]


CURRENT_REPORT_FIELDS = [
    "report_id",
    "reason",
    "submission_date",
    "tx_date",
    "tx_amount_local",
    "tx_transmode_code",
    "tx_transmode_comment",
    "from_funds_code",
    "from_country",
    "from_institution",
    "from_account",
    "from_account_name",
    "from_account_opened",
    "from_account_type",
    "from_account_balance",
    "to_funds_code",
    "to_country",
    "indicators",
    "indicator_count",
    "signatory_count",
    "to_account_count",
    "reason_word_count",
    "source_file",
]


ACCOUNT_KYC_FIELDS = [
    "account_id",
    "account_number",
    "institution",
    "branch",
    "acct_type",
    "risk_grade",
    "is_person",
    "name",
    "tax_number",
    "pep_flag",
    "sanctions_hit",
    "city",
    "opened",
]


TRANSACTION_EVIDENCE_FIELDS = [
    "row_index",
    "date_transaction",
    "sender_account",
    "receiver_account",
    "sender_account_number",
    "receiver_account_number",
    "amount_local_npr",
    "payment_type",
    "transmode_code",
    "cross_border_flag",
    "currency_mismatch",
    "sender_risk_grade",
    "sender_account_age_days",
    "receiver_account_age_days",
    "velocity_sum_10tx",
    "tx_count_10",
    "tx_count_30",
    "amount_zscore",
    "above_1m_npr",
    "above_10m_npr",
]


ML_FEATURE_FIELDS = [
    "amount_local_npr",
    "amount_zscore",
    "above_1m_npr",
    "above_10m_npr",
    "cross_border_flag",
    "currency_mismatch",
    "velocity_sum_10tx",
    "tx_count_10",
    "tx_count_30",
    "sender_account_age_days",
    "sender_pep",
    "sender_sanctions",
    "receiver_sanctions",
    "is_suspicious_tx",
]


def parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def months_between(start: datetime | None, end: datetime | None) -> float | None:
    if start is None or end is None:
        return None
    return round((end - start).days / 30.4375, 2)


def days_between(start: datetime | None, end: datetime | None) -> int | None:
    if start is None or end is None:
        return None
    return (end - start).days


def unique_non_empty(values: list[Any]) -> list[str]:
    return sorted({str(value) for value in values if value not in (None, "")})


def get_report(conn: Any, report_id: str) -> Mapping[str, Any]:
    row = conn.execute(
        "SELECT * FROM str_reports WHERE report_id = %s",
        (report_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Report not found: {report_id}")
    return row


def get_account_history(
    conn: Any,
    from_account: str | None,
    tx_date: Any,
    report_id: str,
) -> list[Mapping[str, Any]]:
    if not from_account or not tx_date:
        return []

    return list(
        conn.execute(
            """
            SELECT *
            FROM str_reports
            WHERE from_account = %s
              AND report_id != %s
              AND (
                  tx_date < %s
                  OR tx_date IS NULL
              )
            ORDER BY tx_date
            """,
            (from_account, report_id, tx_date),
        )
    )


def get_account_kyc(
    conn: Any,
    account_number: str | None,
) -> Mapping[str, Any] | None:
    if not account_number:
        return None
    return conn.execute(
        "SELECT * FROM accounts WHERE account_number = %s",
        (account_number,),
    ).fetchone()


def get_best_transaction_match(
    conn: Any,
    account_number: str | None,
    tx_date: Any,
    amount: Any,
) -> Mapping[str, Any] | None:
    if not account_number:
        return None

    params = [account_number]
    amount_filter = ""
    if amount is not None:
        amount_filter = "ABS(amount_local_npr - %s) ASC,"
        params.append(float(amount))

    date_filter = ""
    if tx_date is not None:
        date_filter = "ABS(EXTRACT(EPOCH FROM (date_transaction - %s::timestamp))) ASC,"
        params.append(tx_date)

    return conn.execute(
        f"""
        SELECT *
        FROM transactions
        WHERE sender_account_number = %s
        ORDER BY {amount_filter} {date_filter} row_index
        LIMIT 1
        """,
        tuple(params),
    ).fetchone()


def get_ml_feature_match(
    conn: Any,
    account_id: str | None,
    transaction: Mapping[str, Any] | None,
) -> Mapping[str, Any] | None:
    if not account_id:
        return None

    params = [account_id]
    amount_filter = ""
    if transaction and transaction.get("amount_local_npr") is not None:
        amount_filter = "ABS(amount_local_npr - %s) ASC,"
        params.append(float(transaction["amount_local_npr"]))

    date_filter = ""
    if transaction and transaction.get("date") is not None:
        date_filter = "date = %s DESC,"
        params.append(transaction["date"])

    return conn.execute(
        f"""
        SELECT *
        FROM ml_features
        WHERE sender_account = %s
        ORDER BY {amount_filter} {date_filter} row_index
        LIMIT 1
        """,
        tuple(params),
    ).fetchone()


def summarize_graph_edges(conn: Any, account_id: str | None) -> dict[str, Any]:
    if not account_id:
        return {
            "outgoing_edge_count": 0,
            "unique_receiver_count": 0,
            "top_receivers": [],
        }

    rows = conn.execute(
        """
        SELECT receiver_account, COUNT(*) AS edge_count, SUM(amount_local_npr) AS total_amount
        FROM graph_edges
        WHERE sender_account = %s
        GROUP BY receiver_account
        ORDER BY edge_count DESC, total_amount DESC
        LIMIT 5
        """,
        (account_id,),
    ).fetchall()

    totals = conn.execute(
        """
        SELECT COUNT(*) AS outgoing_edge_count,
               COUNT(DISTINCT receiver_account) AS unique_receiver_count
        FROM graph_edges
        WHERE sender_account = %s
        """,
        (account_id,),
    ).fetchone()

    return {
        "outgoing_edge_count": int(totals["outgoing_edge_count"] or 0),
        "unique_receiver_count": int(totals["unique_receiver_count"] or 0),
        "top_receivers": [dict(row) for row in rows],
    }


def summarize_history(
    current: Mapping[str, Any],
    history: list[Mapping[str, Any]],
) -> dict[str, Any]:
    previous_amounts = [
        float(row["tx_amount_local"])
        for row in history
        if row["tx_amount_local"] is not None
    ]
    current_amount = (
        float(current["tx_amount_local"])
        if current["tx_amount_local"] is not None
        else None
    )

    previous_dates = [
        parse_datetime(row["tx_date"])
        for row in history
        if parse_datetime(row["tx_date"]) is not None
    ]
    current_tx_date = parse_datetime(current["tx_date"])
    latest_previous_date = max(previous_dates) if previous_dates else None

    avg_previous_amount = round(mean(previous_amounts), 2) if previous_amounts else None
    max_previous_amount = max(previous_amounts) if previous_amounts else None

    amount_vs_average = None
    if current_amount is not None and avg_previous_amount not in (None, 0):
        amount_vs_average = round(current_amount / avg_previous_amount, 2)

    amount_vs_max = None
    if current_amount is not None and max_previous_amount not in (None, 0):
        amount_vs_max = round(current_amount / max_previous_amount, 2)

    return {
        "previous_report_count": len(history),
        "previous_transaction_count": len(history),
        "average_previous_amount": avg_previous_amount,
        "max_previous_amount": max_previous_amount,
        "current_amount_vs_average_previous": amount_vs_average,
        "current_amount_vs_max_previous": amount_vs_max,
        "days_since_previous_report": days_between(
            latest_previous_date,
            current_tx_date,
        ),
        "previous_transaction_modes": unique_non_empty(
            [row["tx_transmode_comment"] for row in history]
        ),
        "previous_from_countries": unique_non_empty(
            [row["from_country"] for row in history]
        ),
        "previous_to_countries": unique_non_empty(
            [row["to_country"] for row in history]
        ),
        "previous_indicators": unique_non_empty(
            [row["indicators"] for row in history]
        ),
    }


def build_evidence_packet(
    conn: Any,
    report_id: str,
) -> dict[str, Any]:
    current = get_report(conn, report_id)
    account_kyc = get_account_kyc(conn, current["from_account"])
    transaction = get_best_transaction_match(
        conn,
        current["from_account"],
        current["tx_date"],
        current["tx_amount_local"],
    )
    ml_features = get_ml_feature_match(
        conn,
        account_kyc["account_id"] if account_kyc else None,
        transaction,
    )
    graph_summary = summarize_graph_edges(
        conn,
        account_kyc["account_id"] if account_kyc else None,
    )
    history = get_account_history(
        conn,
        current["from_account"],
        current["tx_date"],
        current["report_id"],
    )

    opened_at = parse_datetime(current["from_account_opened"])
    submission_at = parse_datetime(current["submission_date"])
    tx_at = parse_datetime(current["tx_date"])

    from_country = current["from_country"]
    to_country = current["to_country"]
    is_cross_border = (
        bool(from_country and to_country)
        and str(from_country).upper() != str(to_country).upper()
    )

    current_report = {
        field: current[field]
        for field in CURRENT_REPORT_FIELDS
        if field in current
    }

    computed_facts = {
        "account_age_days_at_submission": days_between(opened_at, submission_at),
        "account_age_months_at_submission": months_between(opened_at, submission_at),
        "account_age_days_at_transaction": days_between(opened_at, tx_at),
        "account_age_months_at_transaction": months_between(opened_at, tx_at),
        "days_between_transaction_and_submission": days_between(tx_at, submission_at),
        "is_cross_border": is_cross_border,
    }
    computed_facts["account_opened_after_transaction"] = (
        computed_facts["account_age_days_at_transaction"] is not None
        and computed_facts["account_age_days_at_transaction"] < 0
    )
    computed_facts["account_tenure_less_than_two_years_at_submission"] = (
        computed_facts["account_age_months_at_submission"] is not None
        and computed_facts["account_age_months_at_submission"] < 24
    )

    data_quality_flags = []
    if computed_facts["account_opened_after_transaction"]:
        data_quality_flags.append(
            {
                "type": "account_opened_after_transaction",
                "severity": "high",
                "description": (
                    "from_account_opened is later than tx_date. This is a "
                    "structured-data issue and should only affect the logic score "
                    "if the reason narrative makes a contradictory chronology claim."
                ),
            }
        )

    return {
        "reason": current["reason"],
        "current_report": current_report,
        "account_kyc": (
            {field: account_kyc[field] for field in ACCOUNT_KYC_FIELDS}
            if account_kyc
            else None
        ),
        "matched_transaction": (
            {
                field: transaction[field]
                for field in TRANSACTION_EVIDENCE_FIELDS
                if field in transaction
            }
            if transaction
            else None
        ),
        "ml_features": (
            {field: ml_features[field] for field in ML_FEATURE_FIELDS if field in ml_features}
            if ml_features
            else None
        ),
        "graph_summary": graph_summary,
        "computed_facts": computed_facts,
        "data_quality_flags": data_quality_flags,
        "account_history_summary": summarize_history(current, history),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an evidence packet for LLM logic validation."
    )
    parser.add_argument("report_id", help="Report ID to inspect, e.g. RPT-2026-000003")
    parser.add_argument("--database-url", default=database_url())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with connect(args.database_url) as conn:
        packet = build_evidence_packet(conn, args.report_id)
    print(json.dumps(packet, indent=2, default=str))


if __name__ == "__main__":
    main()
