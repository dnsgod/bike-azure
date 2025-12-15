import os, json, requests, datetime as dt
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("SEOUL_BIKE_API_KEY")
print(API_KEY)
BASE = f"http://openapi.seoul.go.kr:8088/{API_KEY}/json/bikeList"

# 따릉이 데이터 전체 구간 (2725까지, 구간당 999)
RANGES = [(1, 999), (1000, 1998), (1999, 2725)]

def fetch_simple():
    rows = []
    for start, end in RANGES:
        url = f"{BASE}/{start}/{end}/"
        print(f"[CALL] {url}")
        res = requests.get(url, timeout=15)
        if res.status_code != 200:
            print(f"[ERROR] HTTP {res.status_code}: {res.text[:100]}")
            continue
        try:
            data = res.json().get("rentBikeStatus", {})
            page = data.get("row", []) or []
            print(f"[PAGE {start}-{end}] {len(page)} rows")
            rows.extend(page)
        except json.JSONDecodeError:
            print(f"[PARSE ERROR] invalid JSON for {url}")
    print(f"[TOTAL] {len(rows)} rows fetched")
    return rows

def main():
    ts = dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    outdir = Path("out_simple"); outdir.mkdir(exist_ok=True)
    rows = fetch_simple()
    payload = {
        "meta": {"timestamp_utc": ts, "total_rows": len(rows)},
        "rentBikeStatus": {"row": rows}
    }
    path = outdir / f"bike_snapshot_{ts}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] {path}")

if __name__ == "__main__":
    main()
