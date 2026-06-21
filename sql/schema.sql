DROP TABLE IF EXISTS logic_validation_results;
DROP TABLE IF EXISTS ml_features;
DROP TABLE IF EXISTS graph_edges;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS accounts;
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

CREATE TABLE accounts (
    account_id TEXT PRIMARY KEY,
    account_number TEXT,
    institution TEXT,
    branch TEXT,
    acct_type TEXT,
    risk_grade TEXT,
    is_person BOOLEAN,
    name TEXT,
    tax_number TEXT,
    pep_flag INTEGER,
    sanctions_hit INTEGER,
    city TEXT,
    opened DATE
);

CREATE INDEX idx_accounts_account_number
    ON accounts (account_number);

CREATE INDEX idx_accounts_name
    ON accounts (name);

CREATE TABLE transactions (
    row_index INTEGER PRIMARY KEY,
    date TEXT,
    time TEXT,
    sender_account TEXT,
    receiver_account TEXT,
    amount NUMERIC,
    payment_currency TEXT,
    received_currency TEXT,
    sender_bank_location TEXT,
    receiver_bank_location TEXT,
    payment_type TEXT,
    transmode_code TEXT,
    fx_rate_to_npr NUMERIC,
    amount_local_npr NUMERIC,
    sender_country_risk TEXT,
    receiver_country_risk TEXT,
    cross_border_flag INTEGER,
    currency_mismatch INTEGER,
    sender_institution TEXT,
    sender_branch TEXT,
    sender_account_number TEXT,
    sender_account_type TEXT,
    sender_risk_grade TEXT,
    sender_opened DATE,
    sender_is_person BOOLEAN,
    sender_pep INTEGER,
    sender_sanctions INTEGER,
    sender_city TEXT,
    sender_account_age_days INTEGER,
    receiver_institution TEXT,
    receiver_branch TEXT,
    receiver_account_number TEXT,
    receiver_account_type TEXT,
    receiver_pep INTEGER,
    receiver_sanctions INTEGER,
    receiver_account_age_days INTEGER,
    date_transaction TIMESTAMP,
    hour_of_day INTEGER,
    day_of_week INTEGER,
    is_weekend INTEGER,
    month INTEGER,
    log_amount NUMERIC,
    above_1m_npr INTEGER,
    above_10m_npr INTEGER,
    velocity_sum_10tx NUMERIC,
    tx_count_10 INTEGER,
    tx_count_30 INTEGER,
    amount_zscore NUMERIC,
    transmode_a INTEGER,
    transmode_b INTEGER,
    transmode_e INTEGER,
    transmode_f INTEGER,
    transmode_j INTEGER,
    transmode_p INTEGER,
    transmode_z INTEGER
);

CREATE INDEX idx_transactions_sender_account_number
    ON transactions (sender_account_number);

CREATE INDEX idx_transactions_sender_date
    ON transactions (sender_account_number, date_transaction);

CREATE INDEX idx_transactions_amount_date
    ON transactions (amount_local_npr, date_transaction);

CREATE TABLE graph_edges (
    row_index INTEGER PRIMARY KEY,
    sender_account TEXT,
    receiver_account TEXT,
    amount_local_npr NUMERIC,
    date TEXT,
    time TEXT
);

CREATE INDEX idx_graph_edges_sender
    ON graph_edges (sender_account);

CREATE INDEX idx_graph_edges_receiver
    ON graph_edges (receiver_account);

CREATE TABLE ml_features (
    row_index BIGSERIAL PRIMARY KEY,
    date TEXT,
    time TEXT,
    sender_account TEXT,
    receiver_account TEXT,
    amount_local_npr NUMERIC,
    log_amount NUMERIC,
    amount_zscore NUMERIC,
    above_1m_npr INTEGER,
    above_10m_npr INTEGER,
    hour_of_day INTEGER,
    day_of_week INTEGER,
    is_weekend INTEGER,
    month INTEGER,
    sender_country_risk TEXT,
    receiver_country_risk TEXT,
    cross_border_flag INTEGER,
    currency_mismatch INTEGER,
    velocity_sum_10tx NUMERIC,
    tx_count_10 INTEGER,
    tx_count_30 INTEGER,
    sender_account_age_days INTEGER,
    receiver_account_age_days INTEGER,
    sender_is_person BOOLEAN,
    sender_pep INTEGER,
    sender_sanctions INTEGER,
    receiver_pep INTEGER,
    receiver_sanctions INTEGER,
    transmode_a INTEGER,
    transmode_b INTEGER,
    transmode_e INTEGER,
    transmode_f INTEGER,
    transmode_j INTEGER,
    transmode_p INTEGER,
    transmode_z INTEGER,
    is_suspicious_tx INTEGER
);

CREATE INDEX idx_ml_features_sender
    ON ml_features (sender_account);
