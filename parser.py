import os
import glob
import xml.etree.ElementTree as ET
import pandas as pd

def parse_xml_file(filepath):
    """
    Parses a single STR XML report and returns a dictionary of extracted fields.
    """
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return None

    def get_text(parent, path, default=""):
        if parent is None:
            return default
        elem = parent.find(path)
        return elem.text if elem is not None and elem.text is not None else default

    # Extract high-level report metadata
    data = {
        "report_id": get_text(root, "report_id"),
        "entity_reference": get_text(root, "entity_reference"),
        "rentity_id": get_text(root, "rentity_id"),
        "rentity_branch": get_text(root, "rentity_branch"),
        "report_code": get_text(root, "report_code"),
        "submission_code": get_text(root, "submission_code"),
        "submission_date": get_text(root, "submission_date"),
        "currency_local": get_text(root, "currency_code_local"),
        "reason": get_text(root, "reason"),
        "source_file": os.path.basename(filepath),
    }

    # Reporting Person details
    rp = root.find("reporting_person")
    if rp is not None:
        data["reporter_gender"] = get_text(rp, "gender")
        data["reporter_title"] = get_text(rp, "title")
        data["reporter_firstname"] = get_text(rp, "first_name")
        data["reporter_lastname"] = get_text(rp, "last_name")
        data["reporter_dob"] = get_text(rp, "birthdate")
        data["reporter_ssn"] = get_text(rp, "ssn")
        data["reporter_phone"] = get_text(rp, "phones/phone/tph_number")
        data["reporter_occupation"] = get_text(rp, "occupation")
    
    # Location details
    loc = root.find("location")
    if loc is not None:
        data["location_address"] = get_text(loc, "address")
        data["location_town"] = get_text(loc, "town")
        data["location_city"] = get_text(loc, "city")
        data["location_zip"] = get_text(loc, "zip")
        data["location_state"] = get_text(loc, "state")
        data["location_country"] = get_text(loc, "country_code")

    # Transaction details
    tx = root.find("transaction")
    if tx is not None:
        data["tx_number"] = get_text(tx, "transactionnumber")
        data["tx_internal_ref"] = get_text(tx, "internal_ref_number")
        data["tx_location"] = get_text(tx, "transaction_location")
        data["tx_date"] = get_text(tx, "date_transaction")
        data["tx_value_date"] = get_text(tx, "value_date")
        data["tx_transmode_code"] = get_text(tx, "transmode_code")
        data["tx_transmode_comment"] = get_text(tx, "transmode_comment")
        data["tx_amount_local"] = float(get_text(tx, "amount_local", "0"))
        data["comments"] = get_text(tx, "comments")

        # Sender Info (t_from_my_client)
        t_from = tx.find("t_from_my_client")
        if t_from is not None:
            data["from_funds_code"] = get_text(t_from, "from_funds_code")
            data["from_country"] = get_text(t_from, "from_country")
            
            # Sender Account Info
            from_acct = t_from.find("from_account")
            if from_acct is not None:
                data["from_institution"] = get_text(from_acct, "institution_name")
                data["from_institution_code"] = get_text(from_acct, "institution_code")
                data["from_branch"] = get_text(from_acct, "branch")
                data["from_account"] = get_text(from_acct, "account")
                data["from_account_name"] = get_text(from_acct, "account_name")
                data["from_account_type"] = get_text(from_acct, "personal_account_type")
                data["from_account_opened"] = get_text(from_acct, "opened")
                data["from_account_balance"] = float(get_text(from_acct, "balance", "0"))
                data["from_account_status"] = get_text(from_acct, "status_code")

                # Sender Foreign Currency Info
                fc = t_from.find("from_foreign_currency")
                if fc is not None:
                    data["from_foreign_currency"] = get_text(fc, "foreign_currency_code")
                    data["from_foreign_amount"] = float(get_text(fc, "foreign_amount", "0"))
                    data["from_exchange_rate"] = float(get_text(fc, "foreign_exchange_rate", "0"))

                # Signatory / Person Info
                sig = from_acct.find("signatory")
                if sig is not None:
                    data["signatory_role"] = get_text(sig, "role")
                    tp = sig.find("t_person")
                    if tp is not None:
                        data["signatory_firstname"] = get_text(tp, "first_name")
                        data["signatory_lastname"] = get_text(tp, "last_name")
                        data["signatory_dob"] = get_text(tp, "birthdate")
                        data["signatory_ssn"] = get_text(tp, "ssn")
                        data["signatory_passport"] = get_text(tp, "passport_number")
                        data["signatory_passport_country"] = get_text(tp, "passport_country")
                        data["signatory_nationality"] = get_text(tp, "nationality1")
                        data["signatory_residence"] = get_text(tp, "residence")
                        data["signatory_occupation"] = get_text(tp, "occupation")
                        data["signatory_tax_number"] = get_text(tp, "tax_number")
                        data["signatory_mothers_name"] = get_text(tp, "mothers_name")
                        data["signatory_birth_place"] = get_text(tp, "birth_place")

        # Receiver Info (t_to)
        t_to = tx.find("t_to")
        if t_to is not None:
            data["to_funds_code"] = get_text(t_to, "to_funds_code")
            data["to_country"] = get_text(t_to, "to_country")
            
            # Receiver Account Info
            to_acct = t_to.find("to_account")
            if to_acct is not None:
                data["to_institution"] = get_text(to_acct, "institution_name")
                data["to_institution_code"] = get_text(to_acct, "institution_code")
                data["to_branch"] = get_text(to_acct, "branch")
                data["to_account"] = get_text(to_acct, "account")
                data["to_account_name"] = get_text(to_acct, "account_name")
                data["to_account_type"] = get_text(to_acct, "personal_account_type")
                data["to_account_opened"] = get_text(to_acct, "opened")

    # Indicators
    indicators = []
    ri = root.find("report_indicators")
    if ri is not None:
        for ind in ri.findall("indicator"):
            if ind.text is not None:
                indicators.append(ind.text)
    data["indicators"] = ",".join(indicators)
    data["indicator_count"] = len(indicators)
    data["reason_word_count"] = len(data["reason"].split()) if data["reason"] else 0

    return data

def parse_all_reports(reports_dir):
    """
    Parses all XML files in reports_dir and returns a structured DataFrame.
    If reports_dir is empty or XML parsing fails, attempts to load from str_reports.csv.
    """
    xml_files = glob.glob(os.path.join(reports_dir, "*.xml"))
    
    if not xml_files:
        print("No XML files found in reports directory. Checking fallback CSV...")
        fallback_path = os.path.join(os.path.dirname(reports_dir), "str_reports.csv")
        if os.path.exists(fallback_path):
            print(f"Loading pre-parsed reports from {fallback_path}")
            return pd.read_csv(fallback_path)
        else:
            raise FileNotFoundError("Neither XML files nor str_reports.csv fallback was found.")

    print(f"Found {len(xml_files)} XML reports to parse.")
    records = []
    for filepath in sorted(xml_files):
        record = parse_xml_file(filepath)
        if record is not None:
            records.append(record)
    
    df = pd.DataFrame(records)
    print(f"Successfully parsed {len(df)} reports.")
    return df
