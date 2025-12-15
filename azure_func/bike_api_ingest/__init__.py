import os
import json
import logging
from datetime import datetime, timezone

import azure.functions as func
import requests
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp()

# =========================================================
# 설정값
# =========================================================
LAST = 2725
SIZE = 999

RANGES = []
s = 1
while s <= LAST:
    e = min(s + SIZE - 1, LAST)
    RANGES.append((s, e))
    s = e + 1


# =========================================================
# 1. 서울시 따릉이 API 전체 수집
# =========================================================
def fetch_all():
    api_key = os.getenv("SEOUL_BIKE_API_KEY")
    if not api_key:
        raise RuntimeError("SEOUL_BIKE_API_KEY missing")

    base = f"http://openapi.seoul.go.kr:8088/{api_key}/json/bikeList"
    rows = []

    for start, end in RANGES:
        url = f"{base}/{start}/{end}/"
        logging.info(f"[CALL] {url}")

        r = requests.get(url, timeout=15)
        r.raise_for_status()

        data = r.json().get("rentBikeStatus", {})
        page = data.get("row", []) or []

        logging.info(f"[PAGE {start}-{end}] rows={len(page)}")
        rows.extend(page)

    logging.info(f"[TOTAL] rows={len(rows)}")
    return rows


# =========================================================
# 2. Blob Storage 업로드 (raw/YYYY/MM/DD/HH/)
# =========================================================
def upload_to_blob(rows):
    conn_str = os.getenv("AzureWebJobsStorage")
    if not conn_str:
        raise RuntimeError("AzureWebJobsStorage missing")

    bsc = BlobServiceClient.from_connection_string(conn_str)
    container = bsc.get_container_client("raw")

    try:
        container.create_container()
        logging.info("[BLOB] created container: raw")
    except Exception:
        pass  # 이미 존재

    ts = datetime.now(timezone.utc)

    blob_path = (
        f"{ts:%Y/%m/%d/%H}/"
        f"bike_snapshot_{ts:%Y%m%d_%H%M%S}.json"
    )

    payload = {
        "meta": {
            "timestamp_utc": ts.isoformat(),
            "total_rows": len(rows)
        },
        "rentBikeStatus": {
            "row": rows
        }
    }

    container.upload_blob(
        name=blob_path,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        overwrite=True
    )

    logging.info(f"[UPLOADED] raw/{blob_path}")


# =========================================================
# 3. ⏰ Timer Trigger (5분 간격, 운영 안정형)
# =========================================================
@app.timer_trigger(
    schedule="0 */5 * * * *",   # ⏱ 5분마다
    arg_name="myTimer",
    run_on_startup=False,       # ❗ 운영에서는 반드시 False
    use_monitor=True            # ❗ 스케줄 상태 저장 (중요)
)
def bike_api_ingest(myTimer: func.TimerRequest) -> None:
    logging.info("=== BIKE API INGEST START ===")

    if myTimer.past_due:
        logging.warning("⚠️ Timer is past due")

    rows = fetch_all()
    if rows:
        upload_to_blob(rows)

    logging.info("=== BIKE API INGEST END ===")
