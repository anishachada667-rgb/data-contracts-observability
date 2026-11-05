import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import great_expectations as gx
import pandas as pd
import psycopg
import yaml


def load_orders():
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
                SELECT order_id, customer_id, loaded_at
                FROM source.orders
                ORDER BY order_id
                """
            )
            rows = cursor.fetchall()

    return pd.DataFrame(
        rows,
        columns=["order_id", "customer_id", "loaded_at"],
    )


def get_freshness_limit():
    contract_path = Path("contracts/orders.yml")

    with contract_path.open("r", encoding="utf-8") as file:
        contract = yaml.safe_load(file)

    freshness = contract["freshness"]

    if freshness["timestamp_column"] != "loaded_at":
        raise ValueError(
            "This monitor currently supports loaded_at as the "
            "freshness timestamp."
        )

    max_age = freshness["max_age_minutes"]

    if isinstance(max_age, bool) or not isinstance(max_age, int) or max_age <= 0:
        raise ValueError("max_age_minutes must be a positive integer.")

    return max_age


def apply_scenario(orders, scenario, now):
    result = orders.copy()

    if scenario == "fresh":
        result["loaded_at"] = now

    elif scenario == "low-volume":
        result = result.head(100).copy()
        result["loaded_at"] = now

    elif scenario == "null-spike":
        result["loaded_at"] = now
        if not result.empty:
            result["customer_id"] = result["customer_id"].astype("object")
            result.loc[result.index[:50], "customer_id"] = None

    elif scenario == "stale":
        result["loaded_at"] = now - timedelta(hours=2)

    return result


def run_gx_checks(orders):
    context = gx.get_context(mode="ephemeral")

    data_source = context.data_sources.add_pandas(
        name="orders_dataframe"
    )

    asset = data_source.add_dataframe_asset(
        name="orders_asset"
    )

    batch_definition = asset.add_batch_definition_whole_dataframe(
        name="orders_batch"
    )

    batch = batch_definition.get_batch(
        batch_parameters={"dataframe": orders}
    )

    volume_expectation = gx.expectations.ExpectTableRowCountToBeBetween(
        min_value=900,
        max_value=1100,
    )

    null_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
        column="customer_id"
    )

    volume_result = batch.validate(volume_expectation)
    null_result = batch.validate(null_expectation)

    return volume_result.success, null_result.success


def main():
    parser = argparse.ArgumentParser(
        description="Run local orders quality and freshness checks."
    )

    parser.add_argument(
        "--scenario",
        choices=["actual", "fresh", "stale", "low-volume", "null-spike"],
        default="actual",
        help="Use actual data or an in-memory test scenario.",
    )

    args = parser.parse_args()

    try:
        now = datetime.now(timezone.utc)
        max_age_minutes = get_freshness_limit()
        orders = load_orders()

        if orders.empty:
            raise ValueError("The source.orders table contains no rows.")

        orders = apply_scenario(orders, args.scenario, now)

        volume_ok, nulls_ok = run_gx_checks(orders)

        timestamps = pd.to_datetime(orders["loaded_at"], utc=True)
        newest = timestamps.max()

        if pd.isna(newest):
            freshness_ok = False
            age_minutes = None
        else:
            age_minutes = (now - newest.to_pydatetime()).total_seconds() / 60
            freshness_ok = 0 <= age_minutes <= max_age_minutes

        print()
        print("ORDERS MONITORING RESULTS")
        print(f"Scenario: {args.scenario}")

        if args.scenario != "actual":
            print("Mode: simulated in memory; database unchanged")

        print(f"Rows checked: {len(orders)}")

        print(
            f"Volume: {'PASS' if volume_ok else 'FAIL'} "
            "(expected 900 to 1,100 rows)"
        )

        print(
            f"Customer ID null check: {'PASS' if nulls_ok else 'FAIL'}"
        )

        if age_minutes is None:
            print("Freshness: FAIL (no valid loaded_at value)")
        else:
            print(
                f"Freshness: {'PASS' if freshness_ok else 'FAIL'} "
                f"(latest load: {age_minutes:.1f} minutes old; "
                f"limit: {max_age_minutes} minutes)"
            )

        print()
        print("Overall:", "PASS" if all(
            [volume_ok, nulls_ok, freshness_ok]
        ) else "FAIL")

        return 0 if all([volume_ok, nulls_ok, freshness_ok]) else 1

    except Exception as exc:
        print(f"ERROR: Monitoring could not run: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())