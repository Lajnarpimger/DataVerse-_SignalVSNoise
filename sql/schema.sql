DROP TABLE IF EXISTS logic_validation_results;
DROP TABLE IF EXISTS str_reports;

CREATE TABLE str_reports (
    report_id TEXT PRIMARY KEY,
    entity_reference TEXT,
    rentity_id INTEGER,
    rentity_branch TEXT,
    report_code TEXT,
    submission_code TEXT,
    submission_date TIMESTAMP,
    currency_local TEXT,
    reason TEXT,
    comments TEXT,
    reporter_gender TEXT,
    reporter_title TEXT,
    reporter_firstname TEXT,
    reporter_lastname TEXT,
    reporter_dob TIMESTAMP,
    reporter_ssn TEXT,
    reporter_phone TEXT,
    reporter_occupation TEXT,
    location_address TEXT,
    location_town TEXT,
    location_city TEXT,
    location_zip TEXT,
    location_state TEXT,
    location_country TEXT,
    tx_number TEXT,
    tx_internal_ref TEXT,
    tx_location TEXT,
    tx_date TIMESTAMP,
    tx_value_date TIMESTAMP,
    tx_transmode_code TEXT,
    tx_transmode_comment TEXT,
    tx_amount_local NUMERIC,
    from_funds_code TEXT,
    from_country TEXT,
    from_institution TEXT,
    from_institution_code TEXT,
    from_branch TEXT,
    from_account TEXT,
    from_account_name TEXT,
    from_account_type TEXT,
    from_account_opened TIMESTAMP,
    from_account_balance NUMERIC,
    from_account_status TEXT,
    from_foreign_currency TEXT,
    from_foreign_amount NUMERIC,
    from_exchange_rate NUMERIC,
    signatory_firstname TEXT,
    signatory_lastname TEXT,
    signatory_dob TIMESTAMP,
    signatory_ssn TEXT,
    signatory_passport TEXT,
    signatory_passport_country TEXT,
    signatory_nationality TEXT,
    signatory_residence TEXT,
    signatory_occupation TEXT,
    signatory_tax_number TEXT,
    signatory_mothers_name TEXT,
    signatory_birth_place TEXT,
    signatory_role TEXT,
    to_funds_code TEXT,
    to_country TEXT,
    indicators TEXT,
    indicator_count INTEGER,
    signatory_count INTEGER,
    to_account_count INTEGER,
    reason_word_count INTEGER,
    source_file TEXT
);

CREATE INDEX idx_str_reports_from_account_tx_date
    ON str_reports (from_account, tx_date);

CREATE INDEX idx_str_reports_source_file
    ON str_reports (source_file);

CREATE TABLE logic_validation_results (
    id BIGSERIAL PRIMARY KEY,
    report_id TEXT NOT NULL REFERENCES str_reports(report_id),
    logic_validation_score NUMERIC NOT NULL,
    verdict TEXT NOT NULL,
    contradictions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    unsupported_claims_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    supported_claims_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    explanation TEXT,
    model_name TEXT,
    prompt_version TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_logic_validation_results_report_id
    ON logic_validation_results (report_id);

