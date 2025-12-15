# funcs/export_csv_fixed.py
from pathlib import Path
import pandas as pd
from common.db.connect import get_conn

OUT = Path("data"); OUT.mkdir(exist_ok=True)

QUERIES = {
    "bike_status_all": "SELECT * FROM dbo.bike_status ORDER BY ts_utc DESC;"
}

def run():
    OUT.mkdir(exist_ok=True)
    with get_conn() as cn:
        for name, sql in QUERIES.items():
            print(f"[RUN] {sql}")
            df = pd.read_sql(sql, cn)
            out_path = OUT / f"{name}.csv"
            df.to_csv(out_path, index=False, encoding="utf-8-sig")
            print(f"[OK] {name} ({len(df)} rows) -> {out_path}")

if __name__ == "__main__":
    run()
