import json
from typing import Dict, Any, Optional
from .client import OllamaClient

def detect_signal(narrative: str, client: OllamaClient) -> Optional[Dict[str, Any]]:
    """
    Stage 4: Signal Detection (LLM)
    Evaluates specificity, context, suspicion_explanation, reasoning, actionability.
    Outputs strict JSON.
    """
    if not narrative or len(narrative.strip()) == 0:
        return {
            "specificity": 0.0,
            "context": 0.0,
            "suspicion_explanation": 0.0,
            "reasoning": 0.0,
            "actionability": 0.0,
            "strengths": [],
            "weaknesses": ["Empty narrative"],
            "detected_signals": []
        }

    prompt = f"""You are an expert Anti-Money Laundering (AML) investigator evaluating a Suspicious Transaction Report (STR) narrative.
Your task is to extract the Signal dimensions from the narrative and return a strict JSON object.

Evaluate the following narrative based on these criteria:
1. Specificity (0.0-1.0): Are there specific dates, amounts, names, and locations?
2. Context (0.0-1.0): Is the background of the customer and the transaction clear?
3. Suspicion Explanation (0.0-1.0): Is the exact reason for suspicion clearly articulated?
4. Reasoning (0.0-1.0): Is there logical reasoning linking the facts to the suspicion?
5. Actionability (0.0-1.0): Does the report provide enough clear information for law enforcement to act upon?

Do NOT hallucinate. If the information is missing or ambiguous, score it low.

Narrative:
\"\"\"
{narrative}
\"\"\"

Output strictly in this JSON format, and nothing else:
{{
  "specificity": <float>,
  "context": <float>,
  "suspicion_explanation": <float>,
  "reasoning": <float>,
  "actionability": <float>,
  "strengths": ["<strength1>", "<strength2>"],
  "weaknesses": ["<weakness1>", "<weakness2>"],
  "detected_signals": ["<signal1>", "<signal2>"]
}}
"""
    result = client.generate(prompt)
    
    if result is None:
        return None
        
    # Ensure all required keys exist
    expected_keys = [
        "specificity", "context", "suspicion_explanation", 
        "reasoning", "actionability", "strengths", 
        "weaknesses", "detected_signals"
    ]
    
    for key in expected_keys:
        if key not in result:
            if key in ["strengths", "weaknesses", "detected_signals"]:
                result[key] = []
            else:
                result[key] = 0.0
                
    # Calculate overall signal score as average of numeric scores
    signal_keys = ["specificity", "context", "suspicion_explanation", "reasoning", "actionability"]
    total = sum(float(result.get(k, 0.0)) for k in signal_keys)
    result["signal_score"] = total / len(signal_keys)
    
    return result
