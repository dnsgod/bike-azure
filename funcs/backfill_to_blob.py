import os, json, time, datetime as dt
from pathlib import Path
from azure.storage.blob import BlobServiceClient
import requests

CONN_STR = os.getenv("AZURE_STORAGE_CONN_STR")
CONTAINER = "raw"

SRC_LOCAL_JSON = Path("data") / "example_source.json"  # (A) 복제용 소스 파일 경로
USE_API = False  # True로 바꾸면 (B) API 호출 모드

API_URL = "http://openapi.seoul.go.kr:8088/{key}/json/bikeList/1/1000/".format(
    key=os.getenv("SEOUL_BIKE_API_KEY", "")
)

def _blob_client():
    if not CONN_STR:
        raise RuntimeError("AZURE_STORAGE_CONN_STR is missing in .env")
    return BlobServiceClient.from_connection_string(CONN_STR)

def _upload_bytes(bsc, rel_path:str, data:bytes):
    container = bsc.get_container_client(CONTAINER)
    container.upload_blob(name=rel_path, data=data, overwrite=True)
    print(f"[UP] {rel_path}")

def make_path(ts:dt.datetime):
    y, m, d, h = ts.strftime("%Y/%m/%d/%H").split("/")
    fname = f"bike_snapshot_{ts.strftime('%Y-%m-%dT%H-%M-%S')}.json"
    return f"{y}/{m}/{d}/{h}/{fname}"

def run_backfill(count=8, mode="A"):
    """
    count: 만들 스냅샷 개수 (예: 8개면 1시간치 7.5분 간격으로 가정)
    mode: "A" 복제 / "B" API 호출
    """
    bsc = _blob_client()
    now = dt.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    for i in range(count):
        ts = now - dt.timedelta(minutes=5*i)  # 5분 간격 거꾸로 생성
        rel = make_path(ts)

        if mode.upper() == "B":
            # (B) 실제 API 호출
            resp = requests.get(API_URL, timeout=15)
            resp.raise_for_status()
            payload = resp.content
        else:
            # (A) 로컬 파일 복제
            if not SRC_LOCAL_JSON.exists():
                raise FileNotFoundError(f"Source JSON not found: {SRC_LOCAL_JSON}")
            payload = SRC_LOCAL_JSON.read_bytes()

            # 파일 안의 ts 값을 바꾸고 싶다면(선택), 간단 변환:
            try:
                j = json.loads(payload)
                j["_ingest_ts"] = ts.isoformat() + "Z"
                payload = json.dumps(j, ensure_ascii=False).encode("utf-8")
            except Exception:
                pass

        _upload_bytes(bsc, f"{CONTAINER}/{rel}".replace(f"{CONTAINER}/",""), payload)
        time.sleep(0.3)  # 과도한 요청 방지

if __name__ == "__main__":
    # 기본: 복제 모드(A)로 8개 업로드
    mode = "B" if (os.getenv("USE_API_MODE","0") == "1") else "A"
    run_backfill(count=8, mode=mode)
