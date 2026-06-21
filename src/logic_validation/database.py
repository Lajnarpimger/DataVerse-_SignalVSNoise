from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row


DEFAULT_CSV_PATH = Path("str_reports (1).csv")
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

    return {
        "report_count": int(row["report_count"]),
        "account_count": int(row["account_count"]),
        "source_file_count": int(row["source_file_count"]),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create PostgreSQL tables and import the compiled STR CSV."
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    parser.add_argument("--database-url", default=database_url())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    imported = import_reports(args.csv, args.database_url, args.schema)
    summary = database_summary(args.database_url)

    print(f"Imported {imported} reports into PostgreSQL")
    print(f"Reports: {summary['report_count']}")
    print(f"Accounts: {summary['account_count']}")
    print(f"Source files: {summary['source_file_count']}")


if __name__ == "__main__":
    main()
