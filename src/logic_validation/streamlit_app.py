from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
import html as _html
import re

import streamlit as st

from src.logic_validation.database import connect, database_url
from src.logic_validation.claim_extraction import (
    DEFAULT_MODEL,
    extract_claims_hybrid,
    extract_claims_rule_based,
)
from src.logic_validation.claim_validation import validate_reason_claims
from src.logic_validation.features import build_evidence_packet


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_ready(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


@st.cache_data(ttl=15)
def list_reports(db_url: str) -> list[dict[str, Any]]:
    with connect(db_url) as conn:
        rows = conn.execute(
            """
            SELECT
                report_id,
                source_file,
                from_account,
                from_account_name,
                from_institution,
                tx_date,
                tx_amount_local
            FROM str_reports
            ORDER BY report_id
            """
        ).fetchall()
    return [json_ready(dict(row)) for row in rows]


def load_report_context(
    db_url: str,
    report_id: str,
    use_llm: bool,
    model: str,
) -> tuple[dict[str, Any], dict[str, Any] | None, str]:
    with connect(db_url) as conn:
        evidence = build_evidence_packet(conn, report_id)
    evidence = json_ready(evidence)

    extraction_source = "rule_based"
    if use_llm:
        try:
            extracted_claims, extraction_source = extract_claims_hybrid(
                evidence.get("reason") or "",
                use_llm=True,
                model=model,
            )
        except Exception as exc:
            st.warning(f"LLM claim extraction failed; using rule-based fallback. {exc}")
            extracted_claims = extract_claims_rule_based(evidence.get("reason") or "")
    else:
        extracted_claims, extraction_source = extract_claims_hybrid(
            evidence.get("reason") or "",
            use_llm=False,
            model=model,
        )

    result = validate_reason_claims(evidence, extracted_claims)
    result["claim_extraction_source"] = extraction_source
    return evidence, result, extraction_source


def format_amount(value: Any) -> str:
    if value in (None, ""):
        return "-"
    try:
        return f"NPR {float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)


def format_months(value: Any) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.1f} months"
    except (TypeError, ValueError):
        return str(value)


STATUS_COLORS = {
    "supported":           "#c3e6cb",
    "partially_supported": "#b8daff",
    "contradicted":        "#f5c6cb",
    "unsupported":         "#ffeeba",
    "not_checkable":       "#d6d8db",
}

STATUS_LABELS = {
    "supported":           "Supported",
    "partially_supported": "Partially Supported",
    "contradicted":        "Contradicted",
    "unsupported":         "Unsupported",
    "not_checkable":       "Not Checkable",
}

# Each claim type maps to the regex that locates it inside the reason text
CLAIM_PATTERNS: dict[str, str] = {
    "account_holder":       r"account held by\s+.+?\s+after",
    "institution":          r"compliance desk at\s+[A-Z0-9_-]+",
    "amount":               r"NPR\s+[0-9][0-9,]*(?:\.\d+)?",
    "cross_border":         r"cross-border",
    "transaction_count":    r"conducted\s+\d+\s+transaction\w*",
    "sanctions":            r"sanctions(?:\s+matches)?",
    "adverse_media":        r"adverse media(?:\s+matches)?",
    "account_tenure":       r"for\s+(?:some|several|many|multiple)\s+years|for\s+years|long[- ]standing",
    "velocity":             r"rapid succession|velocity|a number of the transfers",
    "typology_structuring": r"structuring|below reporting thresholds?",
    "counterparty":         r"principal counterparties observed were\s+[^.]+",
    "kyc_income_profile":   r"income profile",
}


def _claim_spans(reason: str, claim_validations: list[dict]) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for item in claim_validations:
        pattern = CLAIM_PATTERNS.get(item.get("type", ""))
        if not pattern:
            continue
        for m in re.finditer(pattern, reason, re.IGNORECASE):
            spans.append((m.start(), m.end(), item["status"]))
    return spans


def render_highlighted_narrative(reason: str, claim_validations: list[dict]) -> None:
    if not reason:
        st.caption("No reason narrative provided.")
        return

    spans = _claim_spans(reason, claim_validations)

    if not spans:
        st.write(reason)
        return

    # Longest match wins when spans start at the same position; earlier start wins overall
    spans.sort(key=lambda x: (x[0], -(x[1] - x[0])))

    # Remove overlaps: first span that occupies a character wins
    merged: list[tuple[int, int, str]] = []
    cursor = 0
    for start, end, status in spans:
        if start < cursor:
            continue
        merged.append((start, end, status))
        cursor = end

    parts: list[str] = []
    pos = 0
    for start, end, status in merged:
        if pos < start:
            parts.append(_html.escape(reason[pos:start]))
        color = STATUS_COLORS[status]
        label = STATUS_LABELS[status]
        text = _html.escape(reason[start:end])
        parts.append(
            f'<mark title="{label}" style="background:{color};padding:2px 4px;'
            f'border-radius:3px;cursor:help;">{text}</mark>'
        )
        pos = end
    if pos < len(reason):
        parts.append(_html.escape(reason[pos:]))

    st.markdown(
        f'<div style="line-height:1.8;font-size:0.9rem;">{"".join(parts)}</div>',
        unsafe_allow_html=True,
    )


def render_legend() -> None:
    swatches = " ".join(
        f'<span style="background:{STATUS_COLORS[k]};padding:2px 10px;'
        f'border-radius:3px;font-size:0.78rem;">{v}</span>'
        for k, v in STATUS_LABELS.items()
    )
    st.markdown(swatches, unsafe_allow_html=True)


def report_label(row: dict[str, Any]) -> str:
    return (
        f"{row['report_id']} | "
        f"{row.get('from_account_name') or 'Unknown account'}"
    )


def render_result(result: dict[str, Any] | None) -> None:
    if not result:
        st.info("No claim validation result available for this report.")
        return

    st.write(result.get("overall_assessment") or "")
    st.caption(f"Claim extraction source: {result.get('claim_extraction_source', 'unknown')}")

    counts = result.get("status_counts", {})
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Supported", counts.get("supported", 0))
    c2.metric("Partial", counts.get("partially_supported", 0))
    c3.metric("Contradicted", counts.get("contradicted", 0))
    c4.metric("Unsupported", counts.get("unsupported", 0))
    c5.metric("Not Checkable", counts.get("not_checkable", 0))

    st.markdown("#### Claim Validations")
    claim_validations = result.get("claim_validations", [])
    if not claim_validations:
        st.caption("No checkable claims were detected.")
    for item in claim_validations:
        status = item.get("status")
        message = (
            f"**{status}** · {item.get('type')}\n\n"
            f"{item.get('claim')}\n\n"
            + "\n".join(f"- {evidence}" for evidence in item.get("evidence", []))
        )
        if status == "supported":
            st.success(message)
        elif status == "partially_supported":
            st.info(message)
        elif status == "contradicted":
            st.error(message)
        elif status == "unsupported":
            st.warning(message)
        else:
            st.caption(message)

    with st.expander("Raw validation result", expanded=False):
        st.json(result)

    with st.expander("Extracted claims", expanded=False):
        st.json(result.get("extracted_claims", []))


def render_report_summary(evidence: dict[str, Any]) -> None:
    current = evidence["current_report"]
    facts = evidence["computed_facts"]
    history = evidence["account_history_summary"]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Amount", format_amount(current.get("tx_amount_local")))
    m2.metric("Account Tenure", format_months(facts.get("account_age_months_at_submission")))
    m3.metric("Prior Reports", history.get("previous_report_count", "-"))
    m4.metric("Cross-border", "Yes" if facts.get("is_cross_border") else "No")


def main() -> None:
    st.set_page_config(
        page_title="STR Logic Validator",
        layout="wide",
    )

    st.title("STR Logic Validation")
    st.caption("Validates STR reason narratives against structured fields.")

    with st.sidebar:
        st.header("Database")
        db_url = st.text_input("Connection URL", value=database_url(), type="password")
        st.divider()
        st.header("Claim Extraction")
        use_llm = st.toggle("Use local LLM extractor", value=True)
        model = st.text_input("Ollama model", value=DEFAULT_MODEL)
        st.divider()
        st.header("Select Report")

    reports = list_reports(db_url)
    report_labels = {report_label(row): row["report_id"] for row in reports}

    if not report_labels:
        st.info("No reports found. Import reports into PostgreSQL first.")
        return

    label = st.sidebar.selectbox("Report", list(report_labels))
    selected_report_id = report_labels[label]

    evidence, latest, _ = load_report_context(db_url, selected_report_id, use_llm, model)
    current = evidence["current_report"]

    left, right = st.columns([1.15, 0.85], gap="large")

    with left:
        st.subheader(f"{current['report_id']} · {current.get('source_file') or 'source unavailable'}")
        render_report_summary(evidence)

        st.markdown("#### Reason Narrative")
        render_legend()
        st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
        claim_validations = (latest or {}).get("claim_validations", [])
        render_highlighted_narrative(evidence.get("reason") or "", claim_validations)

    with right:
        st.subheader("Logic Validation Result")
        render_result(latest)


if __name__ == "__main__":
    main()
