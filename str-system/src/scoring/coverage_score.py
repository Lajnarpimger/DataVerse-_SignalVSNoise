from typing import Dict, Any, Tuple

def calculate_coverage(extracted_evidence: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """
    Stage 2: Coverage Score (Deterministic)
    Measures how much structured information is reflected in the narrative.
    coverage = mentioned_fields / expected_fields
    """
    expected_fields = 0
    mentioned_fields = 0
    evidence = []
    
    categories = ["transaction", "party"]
    
    for cat in categories:
        for field, data in extracted_evidence[cat].items():
            if data["present_in_xml"]:
                expected_fields += 1
                if data["present_in_narrative"]:
                    mentioned_fields += 1
                    evidence.append(f"Covered {cat}.{field}: '{data['value']}' found in narrative.")
                else:
                    evidence.append(f"Missing {cat}.{field}: '{data['value']}' not found in narrative.")
                    
    coverage = mentioned_fields / expected_fields if expected_fields > 0 else 0.0
    
    return coverage, {
        "expected_fields": expected_fields,
        "mentioned_fields": mentioned_fields,
        "evidence": evidence
    }
