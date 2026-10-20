"""
Shared warehouse access for the Python layer.

Reads connection details from your dbt profile (~/.dbt/profiles.yml, target 'dev'),
so credentials live in one place and never in the repo. Uses key-pair auth.

For local testing without Snowflake, set LUMORA_DUCKDB=/path/to/file.duckdb.
"""
import os
from pathlib import Path
import pandas as pd

MARTS = "LUMORA.MARTS"


def _profile():
    import yaml
    prof = yaml.safe_load(Path("~/.dbt/profiles.yml").expanduser().read_text())
    return prof["lumora"]["outputs"]["dev"]


def read_sql(sql: str) -> pd.DataFrame:
    """Run a query and return a DataFrame with lower-case column names."""
    duck = os.getenv("LUMORA_DUCKDB")
    if duck:
        import duckdb
        con = duckdb.connect(duck, read_only=True)
        df = con.execute(sql.replace("LUMORA.MARTS.", "marts.")).fetchdf()
        con.close()
    else:
        import snowflake.connector
        p = _profile()
        con = snowflake.connector.connect(
            account=p["account"], user=p["user"], private_key_file=p["private_key_path"],
            role=p.get("role"), warehouse=p.get("warehouse"), database=p.get("database"),
        )
        try:
            df = con.cursor().execute(sql).fetch_pandas_all()
        finally:
            con.close()
    df.columns = [c.lower() for c in df.columns]
    return df


def write_table(df: pd.DataFrame, table: str) -> None:
    """Write a DataFrame to LUMORA.MARTS.<table>, replacing it (Snowflake only)."""
    if os.getenv("LUMORA_DUCKDB"):
        print(f"(local test mode: skipped writing {table})")
        return
    import snowflake.connector
    from snowflake.connector.pandas_tools import write_pandas
    p = _profile()
    con = snowflake.connector.connect(
        account=p["account"], user=p["user"], private_key_file=p["private_key_path"],
        role=p.get("role"), warehouse=p.get("warehouse"), database=p.get("database"), schema="MARTS",
    )
    try:
        out = df.copy()
        out.columns = [c.upper() for c in out.columns]
        write_pandas(con, out, table_name=table.upper(), database="LUMORA", schema="MARTS",
                     auto_create_table=True, overwrite=True, quote_identifiers=False)
        print(f"Wrote {len(out):,} rows to LUMORA.MARTS.{table.upper()}")
    finally:
        con.close()
