import json
from typing import Dict, Any, Optional
from .client import OllamaClient

def evaluate_report(narrative: str, parsed_data: Dict[str, Any], client: OllamaClient) -> Optional[Dict[str, Any]]:
    """
    Stage 4 & 5: Unified LLM Evaluation
    Detects both signal and noise in a single LLM call to lower latency and variance.
    Must return exact JSON matching the schema.
    """
    if not narrative or len(narrative.strip()) == 0:
        return {
            "signal": {
                "specificity": 0.0, "context": 0.0, "suspicion_explanation": 0.0,
                "reasoning": 0.0, "actionability": 0.0
            },
            "noise": {
                "generic_noise": 1.0, "unsupported_conclusions": 0.0,
                "repetition_noise": 0.0, "boilerplate_noise": 1.0
            },
            "strengths": [],
            "weaknesses": ["Empty narrative"],
            "detected_signals": [],
            "detected_noise": ["Empty narrative is entirely noise/useless"]
        }

    # Extract specific facts to protect them from being flagged as noise
    cust_name = str(parsed_data.get("signatory_lastname") or parsed_data.get("signatory_firstname") or "the customer").strip()
    bank_name = str(parsed_data.get("sender_institution") or parsed_data.get("receiver_institution") or "the bank").strip()
    
    prompt = f"""You are an expert Anti-Money Laundering (AML) auditor evaluating a Suspicious Transaction Report (STR).
Your task is to identify both the analytical SIGNAL (useful info) and the NOISE (useless info) from the narrative.

Evaluate the narrative based on these Signal dimensions (0.0=None to 1.0=Excellent):
1. specificity: Are there specific dates, amounts, names, and locations?
2. context: Is the background of the customer and the transaction clear?
3. suspicion_explanation: Is the exact reason for suspicion clearly articulated?
4. reasoning: Is there logical reasoning linking the facts to the suspicion?
5. actionability: Does the report provide enough clear information for law enforcement to act upon?

Evaluate the narrative based on these Noise dimensions (0.0=No noise to 1.0=High noise):
1. generic_noise: Does it use vague language without specifics?
2. unsupported_conclusions: Does it make claims without evidence?
3. repetition_noise: Does it repeat the same point multiple times without adding value?
4. boilerplate_noise: Does it overly rely on standard compliance disclaimers or canned phrases?

EXCEPTIONS FOR NOISE (CRITICAL):
- Sentences that introduce the report but contain specific facts (e.g., Bank names like "{bank_name}", customer names like "{cust_name}", or specific trigger reasons like internal alerts) are VALID CONTEXT and MUST NOT be penalized as noise.
- "Boilerplate noise" strictly applies to purely useless legal disclaimers (e.g., "submitted out of an abundance of caution", "does not constitute wrongdoing").

IMPORTANT (TRACEABILITY REQUIREMENT):
For "detected_signals" and "detected_noise", you MUST quote exact phrases from the narrative that justify your scores.

Narrative:
\"\"\"
{narrative}
\"\"\"

Output strictly in this JSON format, and nothing else:
{{
  "signal": {{
    "specificity": <float>,
    "context": <float>,
    "suspicion_explanation": <float>,
    "reasoning": <float>,
    "actionability": <float>
  }},
  "noise": {{
    "generic_noise": <float>,
    "unsupported_conclusions": <float>,
    "repetition_noise": <float>,
    "boilerplate_noise": <float>
  }},
  "strengths": ["<string>", ...],
  "weaknesses": ["<string>", ...],
  "detected_signals": ["<string containing exact phrase quote>", ...],
  "detected_noise": ["<string containing exact phrase quote>", ...]
}}
"""
    result = client.generate(prompt)
    
    if result is None:
        return None
        
    # Ensure nested structures exist
    if "signal" not in result:
        result["signal"] = {}
    if "noise" not in result:
        result["noise"] = {}
        
    for k in ["strengths", "weaknesses", "detected_signals", "detected_noise"]:
        if k not in result:
            result[k] = []
            
    # Calculate averages
    signal_vals = [float(v) for v in result["signal"].values()] if result["signal"] else [0.0]
    result["signal_score"] = sum(signal_vals) / len(signal_vals) if signal_vals else 0.0
    
    noise_vals = [float(v) for v in result["noise"].values()] if result["noise"] else [1.0]
    result["noise_score"] = sum(noise_vals) / len(noise_vals) if noise_vals else 1.0
    
    return result
