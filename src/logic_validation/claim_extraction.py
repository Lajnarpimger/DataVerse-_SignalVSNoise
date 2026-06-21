from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any


DEFAULT_MODEL = "llama3.2"
DEFAULT_OLLAMA_URL = "http://localhost:11434"

CLAIM_TYPES = [
    "account_holder",
    "institution",
    "amount",
    "date_range",
    "transaction_count",
    "transaction_type",
    "cross_border",
    "counterparty",
    "sanctions",
    "adverse_media",
    "account_tenure",
    "velocity",
    "typology_structuring",
    "usual_corridor",
    "kyc_income_profile",
    "other",
]


SYSTEM_PROMPT = """You extract factual and analytical claims from Suspicious Transaction Report narratives.

Return JSON only. Do not validate the claims. Do not use outside knowledge.
Each claim must be explicitly present in the narrative.
Copy claim_text exactly from the narrative as a complete phrase or clause.
Do not return short fragments, labels, summaries, or inferred facts.
"""


def build_extraction_prompt(reason: str) -> str:
    return (
        "Extract claims from this STR reason narrative.\n\n"
        "Rules:\n"
        "- claim_text must be copied exactly from the narrative.\n"
        "- claim_text must be a complete phrase or clause, not a keyword fragment.\n"
        "- Split compound narrative text into separate atomic claims.\n"
        "- Do not add claims that are only implied.\n"
        "- If a sentence says two facts, return two claims.\n\n"
        "Return JSON with this shape:\n"
        "{\n"
        '  "claims": [\n'
        '    {"claim_text": "...", "claim_type": "..."}\n'
        "  ]\n"
        "}\n\n"
        "Allowed claim_type values:\n"
        f"{', '.join(CLAIM_TYPES)}\n\n"
        "Example:\n"
        "Narrative: The compliance desk at PRABHU examined the account held by Robert King. "
        "The customer conducted 1 transaction(s) amounting to approximately NPR 813,936. "
        "It is worth noting that no adverse media or sanctions matches were identified.\n"
        "JSON:\n"
        "{\n"
        '  "claims": [\n'
        '    {"claim_text": "compliance desk at PRABHU", "claim_type": "institution"},\n'
        '    {"claim_text": "account held by Robert King", "claim_type": "account_holder"},\n'
        '    {"claim_text": "conducted 1 transaction(s)", "claim_type": "transaction_count"},\n'
        '    {"claim_text": "amounting to approximately NPR 813,936", "claim_type": "amount"},\n'
        '    {"claim_text": "no adverse media", "claim_type": "adverse_media"},\n'
        '    {"claim_text": "sanctions matches were identified", "claim_type": "sanctions"}\n'
        "  ]\n"
        "}\n\n"
        "Narrative:\n"
        f"{reason}"
    )


def normalize_claims(payload: Any, reason: str | None = None) -> list[dict[str, str]]:
    if isinstance(payload, dict):
        raw_claims = payload.get("claims", [])
    elif isinstance(payload, list):
        raw_claims = payload
    else:
        raw_claims = []

    claims = []
    lowered_reason = reason.lower() if reason else None
    seen = set()
    for item in raw_claims:
        if not isinstance(item, dict):
            continue
        claim_text = str(item.get("claim_text") or item.get("claim") or "").strip()
        claim_type = str(item.get("claim_type") or item.get("type") or "other").strip()
        if not claim_text:
            continue
        claim_text = re.sub(r"\s+", " ", claim_text)
        if lowered_reason and claim_text.lower() not in lowered_reason:
            continue
        if len(claim_text.split()) < 3 and claim_type != "amount":
            continue
        if claim_type not in CLAIM_TYPES:
            claim_type = "other"
        key = (claim_text.lower(), claim_type)
        if key in seen:
            continue
        seen.add(key)
        claims.append({"claim_text": claim_text, "claim_type": claim_type})
    return claims


def extract_claims_with_ollama(
    reason: str,
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
) -> list[dict[str, str]]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_extraction_prompt(reason)},
        ],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }
    request = urllib.request.Request(
        f"{ollama_url.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Could not reach Ollama. Start Ollama and make sure the selected "
            f"open-weight model is available: ollama pull {model}"
        ) from exc

    content = data.get("message", {}).get("content")
    if not content:
        raise RuntimeError(f"Ollama returned an empty claim extraction response: {data}")

    return normalize_claims(json.loads(content), reason=reason)


def _add_regex_claim(
    claims: list[dict[str, str]],
    reason: str,
    claim_type: str,
    pattern: str,
    flags: int = re.IGNORECASE,
) -> None:
    match = re.search(pattern, reason, flags)
    if not match:
        return
    claim_text = re.sub(r"\s+", " ", match.group(0)).strip(" .,;")
    if claim_text:
        claims.append({"claim_text": claim_text, "claim_type": claim_type})


def extract_claims_rule_based(reason: str) -> list[dict[str, str]]:
    """Fallback extractor used when local LLM extraction is unavailable."""
    claims = []
    _add_regex_claim(claims, reason, "institution", r"compliance desk at\s+[A-Z0-9_-]+")
    _add_regex_claim(claims, reason, "account_holder", r"account held by\s+.+?(?=\s+after|\s+following|\.|,)")
    _add_regex_claim(claims, reason, "date_range", r"Between\s+\d{4}-\d{2}-\d{2}\s+and\s+\d{4}-\d{2}-\d{2}")
    _add_regex_claim(claims, reason, "transaction_count", r"conducted\s+\d+\s+transaction\(s\)")
    _add_regex_claim(claims, reason, "transaction_type", r"predominantly\s+.+?(?=\s+[\u2014-]\s+|,|\.|;)")
    _add_regex_claim(claims, reason, "amount", r"amounting to approximately\s+NPR\s+[0-9][0-9,]*(?:\.\d+)?")
    _add_regex_claim(claims, reason, "cross_border", r"\d+\s+were\s+cross-border")
    _add_regex_claim(claims, reason, "usual_corridor", r"routed to counterparties outside the customer's usual corridor")
    _add_regex_claim(claims, reason, "counterparty", r"principal counterparties observed were\s+[^.]+")
    _add_regex_claim(claims, reason, "kyc_income_profile", r"customer's KYC file lists\s+[^.;]+")
    _add_regex_claim(claims, reason, "velocity", r"velocity and aggregate value of the funds are not fully consistent with that profile")
    _add_regex_claim(claims, reason, "adverse_media", r"no adverse media")
    _add_regex_claim(claims, reason, "sanctions", r"no\s+(?:adverse media or\s+)?sanctions matches were identified")
    _add_regex_claim(claims, reason, "account_tenure", r"customer has been with the institution for\s+[^,.;]+")
    _add_regex_claim(claims, reason, "typology_structuring", r"transfers appear to have been deliberately kept below reporting thresholds")
    _add_regex_claim(claims, reason, "velocity", r"executed in rapid succession")
    _add_regex_claim(claims, reason, "typology_structuring", r"pattern[^.]+consistent with\s+[^.]+")
    return normalize_claims(claims, reason=reason)


def merge_claims(*claim_groups: list[dict[str, str]]) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    seen = set()
    for claims in claim_groups:
        for item in claims:
            claim_text = str(item.get("claim_text", "")).strip()
            claim_type = str(item.get("claim_type", "other")).strip()
            key = (claim_text.lower(), claim_type)
            if not claim_text or key in seen:
                continue
            seen.add(key)
            merged.append({"claim_text": claim_text, "claim_type": claim_type})
    return merged


def extract_claims_hybrid(
    reason: str,
    use_llm: bool = True,
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
) -> tuple[list[dict[str, str]], str]:
    rule_claims = extract_claims_rule_based(reason)
    if not use_llm:
        return rule_claims, "rule_based"

    llm_claims = extract_claims_with_ollama(reason, model=model, ollama_url=ollama_url)
    return merge_claims(llm_claims, rule_claims), f"llm+rules:{model}"
