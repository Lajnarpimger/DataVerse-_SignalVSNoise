from __future__ import annotations
import argparse
import csv
import os
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row


DEFAULT_CSV_PATH = Path("str_reports (1).csv")
DEFAULT_ACCOUNTS_PATH = Path("accounts.csv")
DEFAULT_TRANSACTIONS_PATH = Path("transactions.csv")
DEFAULT_GRAPH_EDGES_PATH = Path("graph_edges.csv")
DEFAULT_ML_FEATURES_PATH = Path("ml_features.csv")
DEFAULT_SCHEMA_PATH = Path("sql/schema.sql")
DEFAULT_DATABASE_URL = (
    "postgresql://str_user:str_password@localhost:55432/str_logic_validation"
)


REPORT_COLUMNS = [
    "report_id",
    "entity_reference",
    "rentity_id",
    "rentity_branch",
    "report_code",
    "submission_code",
    "submission_date",
    "currency_local",
    "reason",
    "comments",
    "reporter_gender",
    "reporter_title",
    "reporter_firstname",
    "reporter_lastname",
    "reporter_dob",
    "reporter_ssn",
    "reporter_phone",
    "reporter_occupation",
    "location_address",
    "location_town",
    "location_city",
    "location_zip",
    "location_state",
    "location_country",
    "tx_number",
    "tx_internal_ref",
    "tx_location",
    "tx_date",
    "tx_value_date",
    "tx_transmode_code",
    "tx_transmode_comment",
    "tx_amount_local",
    "from_funds_code",
    "from_country",
    "from_institution",
    "from_institution_code",
    "from_branch",
    "from_account",
    "from_account_name",
    "from_account_type",
    "from_account_opened",
    "from_account_balance",
    "from_account_status",
    "from_foreign_currency",
    "from_foreign_amount",
    "from_exchange_rate",
    "signatory_firstname",
    "signatory_lastname",
    "signatory_dob",
    "signatory_ssn",
    "signatory_passport",
    "signatory_passport_country",
    "signatory_nationality",
    "signatory_residence",
    "signatory_occupation",
    "signatory_tax_number",
    "signatory_mothers_name",
    "signatory_birth_place",
    "signatory_role",
    "to_funds_code",
    "to_country",
    "indicators",
    "indicator_count",
    "signatory_count",
    "to_account_count",
    "reason_word_count",
    "source_file",
]


NUMERIC_COLUMNS = {
    "tx_amount_local",
    "from_account_balance",
    "from_foreign_amount",
    "from_exchange_rate",
}


INTEGER_COLUMNS = {
    "rentity_id",
    "indicator_count",
    "signatory_count",
    "to_account_count",
    "reason_word_count",
}


ACCOUNT_COLUMNS = [
    "account_id",
    "account_number",
    "institution",
    "branch",
    "acct_type",
    "risk_grade",
    "is_person",
    "name",
    "tax_number",
    "pep_flag",
    "sanctions_hit",
    "city",
    "opened",
]


TRANSACTION_COLUMN_MAP = {
    "row_index": "row_index",
    "Date": "date",
    "Time": "time",
    "Sender_account": "sender_account",
    "Receiver_account": "receiver_account",
    "Amount": "amount",
    "Payment_currency": "payment_currency",
    "Received_currency": "received_currency",
    "Sender_bank_location": "sender_bank_location",
    "Receiver_bank_location": "receiver_bank_location",
    "Payment_type": "payment_type",
    "transmode_code": "transmode_code",
    "fx_rate_to_npr": "fx_rate_to_npr",
    "amount_local_npr": "amount_local_npr",
    "sender_country_risk": "sender_country_risk",
    "receiver_country_risk": "receiver_country_risk",
    "cross_border_flag": "cross_border_flag",
    "currency_mismatch": "currency_mismatch",
    "sender_institution": "sender_institution",
    "sender_branch": "sender_branch",
    "sender_account_number": "sender_account_number",
    "sender_account_type": "sender_account_type",
    "sender_risk_grade": "sender_risk_grade",
    "sender_opened": "sender_opened",
    "sender_is_person": "sender_is_person",
    "sender_pep": "sender_pep",
    "sender_sanctions": "sender_sanctions",
    "sender_city": "sender_city",
    "sender_account_age_days": "sender_account_age_days",
    "receiver_institution": "receiver_institution",
    "receiver_branch": "receiver_branch",
    "receiver_account_number": "receiver_account_number",
    "receiver_account_type": "receiver_account_type",
    "receiver_pep": "receiver_pep",
    "receiver_sanctions": "receiver_sanctions",
    "receiver_account_age_days": "receiver_account_age_days",
    "date_transaction": "date_transaction",
    "hour_of_day": "hour_of_day",
    "day_of_week": "day_of_week",
    "is_weekend": "is_weekend",
    "month": "month",
    "log_amount": "log_amount",
    "above_1M_NPR": "above_1m_npr",
    "above_10M_NPR": "above_10m_npr",
    "velocity_sum_10tx": "velocity_sum_10tx",
    "tx_count_10": "tx_count_10",
    "tx_count_30": "tx_count_30",
    "amount_zscore": "amount_zscore",
    "transmode_A": "transmode_a",
    "transmode_B": "transmode_b",
    "transmode_E": "transmode_e",
    "transmode_F": "transmode_f",
    "transmode_J": "transmode_j",
    "transmode_P": "transmode_p",
    "transmode_Z": "transmode_z",
}


GRAPH_EDGE_COLUMN_MAP = {
    "row_index": "row_index",
    "Sender_account": "sender_account",
    "Receiver_account": "receiver_account",
    "amount_local_npr": "amount_local_npr",
    "Date": "date",
    "Time": "time",
}


ML_FEATURE_COLUMN_MAP = {
    "Date": "date",
    "Time": "time",
    "Sender_account": "sender_account",
    "Receiver_account": "receiver_account",
    "amount_local_npr": "amount_local_npr",
    "log_amount": "log_amount",
    "amount_zscore": "amount_zscore",
    "above_1M_NPR": "above_1m_npr",
    "above_10M_NPR": "above_10m_npr",
    "hour_of_day": "hour_of_day",
    "day_of_week": "day_of_week",
    "is_weekend": "is_weekend",
    "month": "month",
    "sender_country_risk": "sender_country_risk",
    "receiver_country_risk": "receiver_country_risk",
    "cross_border_flag": "cross_border_flag",
    "currency_mismatch": "currency_mismatch",
    "velocity_sum_10tx": "velocity_sum_10tx",
    "tx_count_10": "tx_count_10",
    "tx_count_30": "tx_count_30",
    "sender_account_age_days": "sender_account_age_days",
    "receiver_account_age_days": "receiver_account_age_days",
    "sender_is_person": "sender_is_person",
    "sender_pep": "sender_pep",
    "sender_sanctions": "sender_sanctions",
    "receiver_pep": "receiver_pep",
    "receiver_sanctions": "receiver_sanctions",
    "transmode_A": "transmode_a",
    "transmode_B": "transmode_b",
    "transmode_E": "transmode_e",
    "transmode_F": "transmode_f",
    "transmode_J": "transmode_j",
    "transmode_P": "transmode_p",
    "transmode_Z": "transmode_z",
    "is_suspicious_tx": "is_suspicious_tx",
}


SUPPORTING_INTEGER_COLUMNS = {
    "row_index",
    "pep_flag",
    "sanctions_hit",
    "cross_border_flag",
    "currency_mismatch",
    "sender_account_age_days",
    "receiver_account_age_days",
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "month",
    "above_1m_npr",
    "above_10m_npr",
    "tx_count_10",
    "tx_count_30",
    "sender_pep",
    "sender_sanctions",
    "receiver_pep",
    "receiver_sanctions",
    "transmode_a",
    "transmode_b",
    "transmode_e",
    "transmode_f",
    "transmode_j",
    "transmode_p",
    "transmode_z",
    "is_suspicious_tx",
}


SUPPORTING_NUMERIC_COLUMNS = {
    "amount",
    "fx_rate_to_npr",
    "amount_local_npr",
    "log_amount",
    "velocity_sum_10tx",
    "amount_zscore",
}


SUPPORTING_BOOLEAN_COLUMNS = {
    "is_person",
    "sender_is_person",
}


def database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def connect(database_url_value: str | None = None) -> psycopg.Connection:
    return psycopg.connect(database_url_value or database_url(), row_factory=dict_row)


def create_schema(conn: psycopg.Connection, schema_path: Path = DEFAULT_SCHEMA_PATH) -> None:
    conn.execute(schema_path.read_text())
    conn.commit()


def coerce_value(column: str, value: str | None) -> Any:
    if value is None or value == "":
        return None
    if column in INTEGER_COLUMNS:
        try:
            return int(value)
        except ValueError:
            return None
    if column in NUMERIC_COLUMNS:
        try:
            return float(value)
        except ValueError:
            return None
    return value


def coerce_supporting_value(column: str, value: str | None) -> Any:
    if value is None or value == "":
        return None
    if column in SUPPORTING_BOOLEAN_COLUMNS:
        return str(value).strip().lower() in {"true", "1", "yes"}
    if column in SUPPORTING_INTEGER_COLUMNS:
        try:
            return int(float(value))
        except ValueError:
            return None
    if column in SUPPORTING_NUMERIC_COLUMNS:
        try:
            return float(value)
        except ValueError:
            return None
    return value


def read_csv_rows(csv_path: Path) -> list[dict[str, Any]]:
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing_columns = sorted(set(REPORT_COLUMNS) - set(reader.fieldnames or []))
        if missing_columns:
            raise ValueError(f"CSV missing expected columns: {missing_columns}")

        rows = []
        for raw in reader:
            rows.append(
                {
                    column: coerce_value(column, raw.get(column))
                    for column in REPORT_COLUMNS
                }
            )
        return rows


def import_reports(
    csv_path: Path = DEFAULT_CSV_PATH,
    database_url_value: str | None = None,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
) -> int:
    rows = read_csv_rows(csv_path)
    columns = ", ".join(REPORT_COLUMNS)
    placeholders = ", ".join(f"%({column})s" for column in REPORT_COLUMNS)

    with connect(database_url_value) as conn:
        create_schema(conn, schema_path)
        with conn.cursor() as cur:
            cur.executemany(
                f"INSERT INTO str_reports ({columns}) VALUES ({placeholders})",
                rows,
            )
        conn.commit()

    return len(rows)


def read_mapped_csv_rows(
    csv_path: Path,
    column_map: dict[str, str],
) -> list[dict[str, Any]]:
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing_columns = sorted(set(column_map) - set(reader.fieldnames or []))
        if missing_columns:
            raise ValueError(f"{csv_path} missing expected columns: {missing_columns}")

        rows = []
        for raw in reader:
            rows.append(
                {
                    target: coerce_supporting_value(target, raw.get(source))
                    for source, target in column_map.items()
                }
            )
        return rows


def insert_rows(conn: psycopg.Connection, table: str, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    columns = list(rows[0])
    column_sql = ", ".join(columns)
    placeholders = ", ".join(f"%({column})s" for column in columns)
    with conn.cursor() as cur:
        cur.executemany(
            f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})",
            rows,
        )
    return len(rows)


def import_supporting_data(
    conn: psycopg.Connection,
    accounts_path: Path = DEFAULT_ACCOUNTS_PATH,
    transactions_path: Path = DEFAULT_TRANSACTIONS_PATH,
    graph_edges_path: Path = DEFAULT_GRAPH_EDGES_PATH,
    ml_features_path: Path = DEFAULT_ML_FEATURES_PATH,
) -> dict[str, int]:
    counts = {}

    if accounts_path.exists():
        rows = read_mapped_csv_rows(
            accounts_path,
            {column: column for column in ACCOUNT_COLUMNS},
        )
        counts["accounts"] = insert_rows(conn, "accounts", rows)

    if transactions_path.exists():
        rows = read_mapped_csv_rows(transactions_path, TRANSACTION_COLUMN_MAP)
        counts["transactions"] = insert_rows(conn, "transactions", rows)

    if graph_edges_path.exists():
        rows = read_mapped_csv_rows(graph_edges_path, GRAPH_EDGE_COLUMN_MAP)
        counts["graph_edges"] = insert_rows(conn, "graph_edges", rows)

    if ml_features_path.exists():
        rows = read_mapped_csv_rows(ml_features_path, ML_FEATURE_COLUMN_MAP)
        counts["ml_features"] = insert_rows(conn, "ml_features", rows)

    return counts


def import_all_data(
    csv_path: Path = DEFAULT_CSV_PATH,
    database_url_value: str | None = None,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    accounts_path: Path = DEFAULT_ACCOUNTS_PATH,
    transactions_path: Path = DEFAULT_TRANSACTIONS_PATH,
    graph_edges_path: Path = DEFAULT_GRAPH_EDGES_PATH,
    ml_features_path: Path = DEFAULT_ML_FEATURES_PATH,
) -> dict[str, int]:
    report_rows = read_csv_rows(csv_path)
    columns = ", ".join(REPORT_COLUMNS)
    placeholders = ", ".join(f"%({column})s" for column in REPORT_COLUMNS)

    with connect(database_url_value) as conn:
        create_schema(conn, schema_path)
        with conn.cursor() as cur:
            cur.executemany(
                f"INSERT INTO str_reports ({columns}) VALUES ({placeholders})",
                report_rows,
            )
        counts = {"str_reports": len(report_rows)}
        counts.update(
            import_supporting_data(
                conn,
                accounts_path,
                transactions_path,
                graph_edges_path,
                ml_features_path,
            )
        )
        conn.commit()

    return counts


def database_summary(database_url_value: str | None = None) -> dict[str, int]:
    with connect(database_url_value) as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS report_count,
                COUNT(DISTINCT from_account) AS account_count,
                COUNT(DISTINCT source_file) AS source_file_count
            FROM str_reports
            """
        ).fetchone()
        supporting_counts = {}
        for table in ["accounts", "transactions", "graph_edges", "ml_features"]:
            supporting_counts[table] = int(
                conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()[
                    "count"
                ]
            )

    summary = {
        "report_count": int(row["report_count"]),
        "account_count": int(row["account_count"]),
        "source_file_count": int(row["source_file_count"]),
    }
    summary.update(supporting_counts)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create PostgreSQL tables and import the compiled STR CSV."
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--accounts", type=Path, default=DEFAULT_ACCOUNTS_PATH)
    parser.add_argument("--transactions", type=Path, default=DEFAULT_TRANSACTIONS_PATH)
    parser.add_argument("--graph-edges", type=Path, default=DEFAULT_GRAPH_EDGES_PATH)
    parser.add_argument("--ml-features", type=Path, default=DEFAULT_ML_FEATURES_PATH)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    parser.add_argument("--database-url", default=database_url())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    imported = import_all_data(
        args.csv,
        args.database_url,
        args.schema,
        args.accounts,
        args.transactions,
        args.graph_edges,
        args.ml_features,
    )
    summary = database_summary(args.database_url)

    print("Imported data into PostgreSQL")
    for table, count in imported.items():
        print(f"{table}: {count}")
    print(f"Reports: {summary['report_count']}")
    print(f"Accounts: {summary['account_count']}")
    print(f"Source files: {summary['source_file_count']}")


if __name__ == "__main__":
    main()
