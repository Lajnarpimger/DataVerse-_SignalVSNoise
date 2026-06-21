import re
from typing import Dict, List, Any

def extract_evidence(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stage 1: Evidence Extraction (Deterministic)
    Extracts structured fields from XML (via parsed_data) and checks their
    presence in the free-text narrative ('reason').
    """
    narrative = str(parsed_data.get("reason", "")).lower()
    
    def check_presence(value: Any, field_type: str = "string") -> Dict[str, Any]:
        val_str = str(value).strip() if value is not None else ""
        if not val_str or val_str == "0" or val_str.lower() == "none":
            return {
                "present_in_xml": False,
                "present_in_narrative": False,
                "specificity": "missing",
                "value": None
            }
        
        present_in_narrative = False
        val_lower = val_str.lower()
        
        # --- FUZZY MATCHING LOGIC ---
        
        if field_type == "amount":
            # Extract numbers from narrative (e.g. "815,799" -> 815799.0)
            numbers = re.findall(r'\d+(?:[.,]\d+)*', narrative)
            narrative_numbers = [float(n.replace(',', '')) for n in numbers if n.replace(',', '').replace('.','',1).isdigit()]
            try:
                xml_amount = float(val_str)
                for n in narrative_numbers:
                    if abs(n - xml_amount) <= 1.0:
                        present_in_narrative = True
                        break
            except ValueError:
                pass
                
        elif field_type == "date":
            # Truncate timestamp T00:00:00 to match base date YYYY-MM-DD
            date_only = val_str.split("t")[0].split("T")[0]
            if len(date_only) >= 4 and date_only in narrative:
                present_in_narrative = True
                
        elif field_type == "country":
            # Map ISO country codes to narrative aliases
            country_aliases = {
                "gb": ["gb", "great britain", "uk", "united kingdom", "england"],
                "us": ["us", "usa", "united states", "america"],
                "np": ["np", "nepal"]
            }
            aliases = country_aliases.get(val_lower, [val_lower])
            if any(alias in narrative for alias in aliases):
                present_in_narrative = True
                
        elif field_type == "type":
            # Map Transmode Codes to text
            type_aliases = {
                "f": ["cross-border", "wire", "international", "transfer", "swift"],
                "a": ["cash", "deposit", "withdrawal"],
                "e": ["cheque", "check"],
                "p": ["ach", "transfer"],
                "j": ["card", "credit card", "debit card", "pos"]
            }
            aliases = type_aliases.get(val_lower, [val_lower])
            if any(alias in narrative for alias in aliases):
                present_in_narrative = True

        else:
            # Fallback strict matching
            if len(val_lower) > 2 and val_lower in narrative:
                present_in_narrative = True
            elif val_str.replace(",", "").replace(".", "").isdigit() and val_str in narrative.replace(",", ""):
                present_in_narrative = True
                
        return {
            "present_in_xml": True,
            "present_in_narrative": present_in_narrative,
            "specificity": "specific" if present_in_narrative else "missing_in_narrative",
            "value": val_str
        }

    def check_indicator_both(keywords: List[str]) -> Dict[str, Any]:
        indicators_xml_raw = str(parsed_data.get("indicators", "")).lower()
        in_xml = any(kw.lower() in indicators_xml_raw for kw in keywords)
        in_nar = any(kw.lower() in narrative for kw in keywords)
        return {
            "present_in_xml": in_xml,
            "present_in_narrative": in_nar,
            "specificity": "specific" if in_nar else ("generic" if in_xml else "missing"),
            "value": None
        }

    # Extract transaction details
    transaction = {
        "amount": check_presence(parsed_data.get("tx_amount_local"), "amount"),
        "currency": check_presence(parsed_data.get("currency_local"), "string"),
        "date": check_presence(parsed_data.get("tx_date"), "date"),
        "type": check_presence(parsed_data.get("tx_transmode_code"), "type"),
        "channel": check_presence(parsed_data.get("tx_transmode_comment"), "string"),
        "source": check_presence(parsed_data.get("from_account"), "string"),
        "destination": check_presence(parsed_data.get("to_account"), "string")
    }
    
    # Extract party details
    party = {
        "customer": check_presence(parsed_data.get("signatory_lastname") or parsed_data.get("signatory_firstname"), "string"),
        "counterparty": check_presence(parsed_data.get("to_account_name"), "string"),
        "country": check_presence(parsed_data.get("from_country") or parsed_data.get("to_country") or parsed_data.get("location_country"), "country"),
        "account_type": check_presence(parsed_data.get("from_account_type"), "string")
    }
    
    # Extract suspicion indicators from narrative
    suspicion_indicators = {
        "velocity": check_indicator_both(["velocity", "rapid", "frequent", "quick succession", "spike"]),
        "structuring": check_indicator_both(["structuring", "smurfing", "below threshold", "split"]),
        "pep": check_indicator_both(["pep", "politically exposed", "politician", "government official"]),
        "sanctions": check_indicator_both(["sanction", "ofac", "embargo", "designated"]),
        "geographic_risk": check_indicator_both(["high risk jurisdiction", "geographic risk", "cross border", "offshore"]),
        "unusual_behavior": check_indicator_both(["unusual", "anomalous", "inconsistent", "out of profile"])
    }
    
    return {
        "transaction": transaction,
        "party": party,
        "suspicion_indicators": suspicion_indicators,
        "narrative": parsed_data.get("reason", "")
    }
