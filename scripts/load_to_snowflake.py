"""
Load data/raw/*.csv into LUMORA.RAW in Snowflake.

Design choice: RAW keeps every column as text, exactly as landed.
Type casting happens in dbt staging models (Day 2), which is where
it is tested and documented.

Auth: set environment variables (see .env.example). Default authenticator
is 'externalbrowser' (opens your browser for SSO/MFA login), which works
with Snowflake trial accounts that enforce MFA.
"""
import os
from pathlib import Path
import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

conn = snowflake.connector.connect(
    account=os.environ["SNOWFLAKE_ACCOUNT"],          # e.g. abc12345.eu-central-1
    user=os.environ["SNOWFLAKE_USER"],
    authenticator=os.getenv("SNOWFLAKE_AUTHENTICATOR", "externalbrowser"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),          # only if not using externalbrowser
    role=os.getenv("SNOWFLAKE_ROLE", "SYSADMIN"),
    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "LUMORA_WH"),
    database="LUMORA",
    schema="RAW",
)

try:
    for csv in sorted(RAW_DIR.glob("raw_*.csv")):
        df = pd.read_csv(csv, dtype=str, keep_default_na=False)   # all text, empty = ''
        df.columns = [c.upper() for c in df.columns]
        df["_LOADED_AT"] = pd.Timestamp.utcnow().isoformat()
        table = csv.stem.upper()
        ok, _, nrows, _ = write_pandas(
            conn, df, table_name=table, database="LUMORA", schema="RAW",
            auto_create_table=True, overwrite=True, quote_identifiers=False,
        )
        print(f"{'OK ' if ok else 'FAIL'} {table:24s} {nrows:>8,d} rows")
finally:
    conn.close()
