import argparse
import os
import sys
from pathlib import Path

import psycopg
import yaml


def validate_contract(contract_path):
    errors = []

    with Path(contract_path).open("r", encoding="utf-8") as file:
        contract = yaml.safe_load(file)

    if not isinstance(contract, dict):
        raise ValueError("Contract must contain a YAML mapping.")

    dataset = contract.get("dataset")
    owner = contract.get("owner")
    columns = contract.get("columns")

    if not isinstance(dataset, str) or dataset.count(".") != 1:
        raise ValueError("dataset must use the format schema.table.")

    if not isinstance(owner, str) or not owner.strip():
        errors.append("Contract owner is missing.")

    if not isinstance(columns, dict) or not columns:
        raise ValueError("Contract must declare at least one column.")

    freshness = contract.get("freshness")
    if not isinstance(freshness, dict):
        errors.append("Freshness configuration is missing.")
    else:
        timestamp_column = freshness.get("timestamp_column")
        max_age = freshness.get("max_age_minutes")

        if timestamp_column not in columns:
            errors.append(
                "Freshness timestamp_column must be declared in columns."
            )

        if (
            isinstance(max_age, bool)
            or not isinstance(max_age, int)
            or max_age <= 0
        ):
            errors.append(
                "freshness.max_age_minutes must be a positive integer."
            )

    schema_name, table_name = dataset.split(".", 1)

    connection_options = {
        "host": os.getenv("PGHOST", "127.0.0.1"),
        "port": os.getenv("PGPORT", "55432"),
        "dbname": os.getenv("PGDATABASE", "contracts_demo"),
        "user": os.getenv("PGUSER", "contract_user"),
        "password": os.getenv("PGPASSWORD", "local_demo_password"),
    }

    with psycopg.connect(**connection_options) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
                """,
                (schema_name, table_name),
            )

            actual_columns = {
                name: {
                    "type": data_type,
                    "nullable": is_nullable == "YES",
                }
                for name, data_type, is_nullable in cursor.fetchall()
            }

    if not actual_columns:
        errors.append(f"Table not found or not accessible: {dataset}")

    for name, expected in columns.items():
        if not isinstance(expected, dict):
            errors.append(f"Invalid definition for column: {name}")
            continue

        if not isinstance(expected.get("type"), str):
            errors.append(f"Column {name} must declare a type.")
            continue

        if not isinstance(expected.get("nullable"), bool):
            errors.append(f"Column {name} must declare nullable as true or false.")
            continue

        actual = actual_columns.get(name)

        if actual is None:
            errors.append(f"Missing required column: {name}")
            continue

        if actual["type"] != expected["type"]:
            errors.append(
                f"Type mismatch for {name}: "
                f"expected '{expected['type']}', found '{actual['type']}'."
            )

        if actual["nullable"] != expected["nullable"]:
            errors.append(
                f"Nullability mismatch for {name}: "
                f"expected {expected['nullable']}, "
                f"found {actual['nullable']}."
            )

    return dataset, errors


def main():
    parser = argparse.ArgumentParser(
        description="Compare a YAML contract with a PostgreSQL table."
    )
    parser.add_argument(
        "--contract",
        default="contracts/orders.yml",
        help="Path to the YAML contract.",
    )
    args = parser.parse_args()

    try:
        dataset, errors = validate_contract(args.contract)
    except (OSError, ValueError, yaml.YAMLError, psycopg.Error) as exc:
        print(f"ERROR: Unable to validate contract: {exc}", file=sys.stderr)
        return 1

    if errors:
        print(f"FAIL: Contract validation for {dataset}")
        for error in errors:
            print(f" - {error}")
        return 1

    print(f"PASS: Contract matches PostgreSQL table {dataset}")
    print("PASS: Owner and freshness settings are present")
    print("NOTE: Freshness of the data is not checked by this script.")
    return 0


if __name__ == "__main__":
    sys.exit(main())