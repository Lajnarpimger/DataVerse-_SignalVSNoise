import json
from typing import Dict, Any, Optional
from .client import OllamaClient

def detect_noise(narrative: str, client: OllamaClient) -> Optional[Dict[str, Any]]:
    """
    Stage 5: Noise Detection (LLM)
    Detects generic statements, unsupported claims, repetition, boilerplate compliance language.
    Outputs strict JSON.
    """
    if not narrative or len(narrative.strip()) == 0:
        return {
            "generic_noise": 1.0,
            "unsupported_conclusions": 0.0,
            "repetition_noise": 0.0,
            "boilerplate_noise": 1.0,
            "noise_examples": ["Empty narrative is entirely noise/useless"]
        }

    prompt = f"""You are an expert Anti-Money Laundering (AML) auditor evaluating a Suspicious Transaction Report (STR) narrative for noise.
Your task is to identify unhelpful, generic, or poorly supported statements and return a strict JSON object.

Evaluate the following narrative based on these noise dimensions (Score 0.0 for NO noise, to 1.0 for HIGH noise):
1. Generic Noise (0.0-1.0): Does it use vague language without specifics? (e.g., "customer acting suspiciously")
2. Unsupported Conclusions (0.0-1.0): Does it make claims without evidence? (e.g., "money laundering" stated as fact without why)
3. Repetition Noise (0.0-1.0): Does it repeat the same point multiple times without adding value?
4. Boilerplate Noise (0.0-1.0): Does it overly rely on standard compliance disclaimers or canned phrases instead of custom analysis?

Narrative:
\"\"\"
{narrative}
\"\"\"

Output strictly in this JSON format, and nothing else:
{{
  "generic_noise": <float>,
  "unsupported_conclusions": <float>,
  "repetition_noise": <float>,
  "boilerplate_noise": <float>,
  "noise_examples": ["<example1>", "<example2>"]
}}
"""
    result = client.generate(prompt)
    
    if result is None:
        return None
        
    expected_keys = [
        "generic_noise", "unsupported_conclusions", 
        "repetition_noise", "boilerplate_noise", "noise_examples"
    ]
    
    for key in expected_keys:
        if key not in result:
            if key == "noise_examples":
                result[key] = []
            else:
                result[key] = 0.0
                
    # Calculate overall noise score as average of numeric scores
    noise_keys = ["generic_noise", "unsupported_conclusions", "repetition_noise", "boilerplate_noise"]
    total = sum(float(result.get(k, 0.0)) for k in noise_keys)
    result["noise_score"] = total / len(noise_keys)
    
    return result
