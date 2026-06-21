from typing import Dict, Any, Union
from src.extraction.extractor import extract_evidence
from src.scoring.coverage_score import calculate_coverage
from src.scoring.validation_score import calculate_validation
from src.llm.client import OllamaClient
from src.llm.llm_evaluator import evaluate_report
from src.scoring.utility_engine import UtilityEngine
from src.diagnostics.diagnostics_gen import generate_diagnostics

def run_pipeline(parsed_str_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
    """
    Orchestrates the STR Signal vs Noise Detection System pipeline.
    """
    
    # Check if data is sufficient to start
    if not parsed_str_data:
        return "insufficient_information"
        
    narrative = str(parsed_str_data.get("reason", "")).strip()
    
    # Stage 1: Evidence Extraction
    extracted_evidence = extract_evidence(parsed_str_data)
    
    # Stage 2: Coverage Score
    coverage_score, coverage_data = calculate_coverage(extracted_evidence)
    
    # Stage 3: Validation Score
    validation_score, validation_data = calculate_validation(extracted_evidence)
    
    # Initialize LLM Client
    llm_client = OllamaClient()
    
    # Stage 4 & 5: Unified LLM Evaluation (Signal & Noise)
    llm_data = evaluate_report(narrative, parsed_str_data, llm_client)
    if llm_data is None:
        llm_data = {}
        
    signal_data = llm_data.get("signal", {})
    noise_data = llm_data.get("noise", {})
    
    signal_data["signal_score"] = llm_data.get("signal_score", 0.0)
    signal_data["strengths"] = llm_data.get("strengths", [])
    signal_data["weaknesses"] = llm_data.get("weaknesses", [])
    signal_data["detected_signals"] = llm_data.get("detected_signals", [])
    
    noise_data["noise_score"] = llm_data.get("noise_score", 1.0)
    noise_data["noise_examples"] = llm_data.get("detected_noise", [])

        
    # Stage 6: Utility Scoring Engine
    engine = UtilityEngine()
    final_score = engine.calculate_score(
        coverage=coverage_score,
        validation=validation_score,
        signal_score=signal_data.get("signal_score", 0.0),
        noise_score=noise_data.get("noise_score", 1.0) # Default to high noise if failed
    )
    
    # Stage 7 & 8: Diagnostics & Traceability
    diagnostics = generate_diagnostics(
        final_score=final_score,
        coverage_data=coverage_data,
        validation_data=validation_data,
        signal_data=signal_data,
        noise_data=noise_data
    )
    
    if "error" in diagnostics and diagnostics["error"] == "insufficient_evidence_to_score":
        return "insufficient_evidence_to_score"
        
    # Construct Final Ranked Output
    final_output = {
        "report_id": parsed_str_data.get("report_id"),
        "final_utility_score": final_score,
        "components": {
            "coverage_score": coverage_score,
            "validation_score": validation_score,
            "signal_score": signal_data.get("signal_score", 0.0),
            "noise_score": noise_data.get("noise_score", 1.0)
        },
        "diagnostics": diagnostics
    }
    
    return final_output
