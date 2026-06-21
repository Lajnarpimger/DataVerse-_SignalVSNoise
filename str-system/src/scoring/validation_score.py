from typing import Dict, Any, Tuple

def calculate_validation(extracted_evidence: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """
    Stage 3: Validation Score (Deterministic)
    Measures correctness: correct_matches / comparable_fields
    Compare: amount, date, country, counterparty, transaction type.
    """
    comparable_fields = 0
    correct_matches = 0
    evidence = []
    
    # Define which fields map to the expected comparable fields
    validation_map = [
        ("transaction", "amount"),
        ("transaction", "date"),
        ("party", "country"),
        ("party", "counterparty"),
        ("transaction", "type")
    ]
    
    for cat, field in validation_map:
        data = extracted_evidence[cat].get(field, {})
        if data.get("present_in_xml"):
            comparable_fields += 1
            if data.get("present_in_narrative"):
                correct_matches += 1
                evidence.append(f"Validated {field}: Correct match found in narrative for '{data['value']}'.")
            else:
                evidence.append(f"Failed validation {field}: '{data['value']}' not supported in narrative.")
                
    validation = correct_matches / comparable_fields if comparable_fields > 0 else 0.0
    
    return validation, {
        "comparable_fields": comparable_fields,
        "correct_matches": correct_matches,
        "evidence": evidence
    }
