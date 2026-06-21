from typing import Dict, Any, List

def generate_diagnostics(
    final_score: float,
    coverage_data: Dict[str, Any],
    validation_data: Dict[str, Any],
    signal_data: Dict[str, Any],
    noise_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Stage 7 & 8: Diagnostic Breakdown and Traceability.
    Ensures every score has evidence and generates diagnostics for low-scoring reports.
    """
    
    # Check if we have any valid data to score
    # Final rule: If no expected fields and no narrative, or signal/noise failed to run
    if coverage_data.get("expected_fields", 0) == 0 and not signal_data:
        return {"error": "insufficient_evidence_to_score"}
        
    failure_reasons = []
    missing_information = []
    why_report_is_vague = []
    why_report_is_useful = []
    
    # Coverage Diagnostics
    if coverage_data["expected_fields"] > 0:
        cov_ratio = coverage_data["mentioned_fields"] / coverage_data["expected_fields"]
        if cov_ratio < 0.5:
            failure_reasons.append({
                "dimension": "coverage",
                "issue": "Low coverage of structured data in narrative",
                "evidence": "Coverage ratio is " + str(round(cov_ratio, 2))
            })
            missing_information.extend([ev for ev in coverage_data["evidence"] if ev.startswith("Missing")])
            
    # Validation Diagnostics
    if validation_data["comparable_fields"] > 0:
        val_ratio = validation_data["correct_matches"] / validation_data["comparable_fields"]
        if val_ratio < 0.5:
            failure_reasons.append({
                "dimension": "validation",
                "issue": "Data mismatch between XML and narrative",
                "evidence": "Validation ratio is " + str(round(val_ratio, 2))
            })
            missing_information.extend([ev for ev in validation_data["evidence"] if ev.startswith("Failed validation")])
            
    # Signal Diagnostics
    if signal_data:
        if signal_data.get("signal_score", 0.0) < 0.5:
            failure_reasons.append({
                "dimension": "signal",
                "issue": "Low analytical signal",
                "evidence": f"Signal score is {round(signal_data.get('signal_score', 0.0), 2)}"
            })
            missing_information.extend(signal_data.get("weaknesses", []))
        else:
            why_report_is_useful.extend(signal_data.get("strengths", []))
            why_report_is_useful.extend(signal_data.get("detected_signals", []))
            
    # Noise Diagnostics
    if noise_data:
        if noise_data.get("noise_score", 0.0) > 0.5:
            failure_reasons.append({
                "dimension": "noise",
                "issue": "High presence of noise",
                "evidence": f"Noise score is {round(noise_data.get('noise_score', 0.0), 2)}"
            })
            why_report_is_vague.extend(noise_data.get("noise_examples", []))
            
    # Compile final evidence trace (Stage 7 Traceability)
    traceability = {
        "coverage_evidence": coverage_data["evidence"],
        "validation_evidence": validation_data["evidence"],
        "signal_evidence": signal_data.get("detected_signals", []),
        "noise_evidence": noise_data.get("noise_examples", [])
    }
    
    # Check if we have absolutely no evidence to justify ANY score
    if not any(traceability.values()) and final_score < 0.1:
        return {"error": "insufficient_evidence_to_score"}
        
    diagnostic_output = {
        "final_score": final_score,
        "traceability": traceability
    }
    
    diagnostic_output.update({
        "failure_reasons": failure_reasons,
        "missing_information": missing_information,
        "why_report_is_vague": why_report_is_vague,
        "why_report_is_useful_or_not": why_report_is_useful if why_report_is_useful else ["Report lacks useful actionable information."]
    })
        
    return diagnostic_output
