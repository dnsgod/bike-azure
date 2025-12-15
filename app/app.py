import os
from pathlib import Path

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pyodbc
from dotenv import load_dotenv

# -----------------------------
# Matplotlib 한글 깨짐 방지 (Windows)
# -----------------------------
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

st.set_page_config(page_title="따릉이 모니터링", layout="wide")

# -----------------------------
# 0) 환경변수 로드 (.env)
# -----------------------------
# 반드시 프로젝트 루트에서 실행: streamlit run app/app.py
load_dotenv()

SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DB     = os.getenv("SQL_DB")
SQL_UID    = os.getenv("SQL_UID")
SQL_PWD    = os.getenv("SQL_PWD")

ODBC_DRIVER_CANDIDATES = [
    "ODBC Driver 18 for SQL Server",
    "ODBC Driver 17 for SQL Server",
]

# -----------------------------
# 1) “표시용” 한글 컬럼 매핑
# -----------------------------
KOR_COLS = {
    "station_id": "대여소 ID",
    "station_name": "대여소명",
    "bike_count": "주차된 자전거 수",
    "bikes_available": "주차된 자전거 수",
    "rack_tot_cnt": "거치대 수",
    "parking_bike_tot_cnt": "주차된 자전거 수(원본)",
    "slots_available": "빈 거치대 수",
    "avail_ratio": "가용률",
    "occ_ratio": "점유율",
    "lat": "위도",
    "lon": "경도",
    "ts_utc": "수집시각(UTC)",
    "ts_kst_str": "수집시각(KST)",
}

KOR_COLS_EXTRA = {
    "hour_utc": "시간(UTC)",
    "hour_kst": "시간(KST)",
    "availability_pct": "평균 가용률(%)",
    "avg_slots_available": "평균 빈 거치대 수",
    "avg_rack_capacity": "평균 거치대 수",
    "need_relocation": "재배치 필요",
}

DISPLAY_COLS = {**KOR_COLS, **KOR_COLS_EXTRA}


def display_df(df: pd.DataFrame) -> pd.DataFrame:
    """화면 출력용: 컬럼명을 한글로 바꾼 뷰"""
    if df is None or df.empty:
        return df
    return df.rename(columns=DISPLAY_COLS)


# -----------------------------
# 2) ODBC 연결 문자열
# -----------------------------
def _pick_driver():
    drivers = [d.strip() for d in pyodbc.drivers()]
    for name in ODBC_DRIVER_CANDIDATES:
        if name in drivers:
            return name
    raise RuntimeError(f"SQL Server ODBC driver not found. installed={drivers}")


def make_conn_str() -> str:
    missing = [k for k, v in {
        "SQL_SERVER": SQL_SERVER,
        "SQL_DB": SQL_DB,
        "SQL_UID": SQL_UID,
        "SQL_PWD": SQL_PWD,
    }.items() if not v]
    if missing:
        raise RuntimeError(f".env missing keys: {missing}")

    driver = _pick_driver()
    return (
        f"Driver={{{driver}}};"
        f"Server={SQL_SERVER};"
        f"Database={SQL_DB};"
        f"Uid={SQL_UID};"
        f"Pwd={SQL_PWD};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )


# -----------------------------
# 3) 공통 전처리
# -----------------------------
def coerce_and_enrich(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    # 숫자형 강제
    for col in ["rack_tot_cnt", "parking_bike_tot_cnt", "slots_available", "lat", "lon"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # bike_count 통일
    if "parking_bike_tot_cnt" in df.columns:
        df["bike_count"] = pd.to_numeric(df["parking_bike_tot_cnt"], errors="coerce")
    elif "bikes_available" in df.columns:
        df["bike_count"] = pd.to_numeric(df["bikes_available"], errors="coerce")

    # ratio 계산
    if "rack_tot_cnt" in df.columns:
        cap = pd.to_numeric(df["rack_tot_cnt"], errors="coerce")
        if "slots_available" in df.columns:
            df["avail_ratio"] = (pd.to_numeric(df["slots_available"], errors="coerce") / cap).replace([np.inf, -np.inf], np.nan)
        elif "bike_count" in df.columns:
            df["avail_ratio"] = ((cap - df["bike_count"]) / cap).replace([np.inf, -np.inf], np.nan)

        if "bike_count" in df.columns:
            df["occ_ratio"] = (df["bike_count"] / cap).replace([np.inf, -np.inf], np.nan)

    # UTC → KST 표시용 문자열 (+09:00 제거)
    if "ts_utc" in df.columns:
        ts = pd.to_datetime(df["ts_utc"], utc=True, errors="coerce")
        df["ts_kst"] = ts.dt.tz_convert("Asia/Seoul")
        df["ts_kst_str"] = df["ts_kst"].dt.strftime("%Y-%m-%d %H:%M:%S")

    return df


# -----------------------------
# 4) DB 조회 (운영형)
#   - 커넥션은 매번 새로 열고 닫음 (끊김 방지)
#   - 최근 N분만 조회해서 부하/끊김 감소
# -----------------------------
DEFAULT_LOOKBACK_MINUTES = 60  # 최근 60분 데이터만 읽기(필요시 조정)

@st.cache_data(ttl=60)
def load_from_sql(lookback_minutes: int = DEFAULT_LOOKBACK_MINUTES):
    conn_str = make_conn_str()
    try:
        with pyodbc.connect(conn_str) as cn:
            # 최근 N분만
            q_recent = f"""
            SELECT *
            FROM dbo.bike_status
            WHERE ts_utc >= DATEADD(minute, -{int(lookback_minutes)}, SYSUTCDATETIME());
            """
            recent = pd.read_sql(q_recent, cn)

            # 분석 뷰 (있으면)
            try:
                peak = pd.read_sql("SELECT * FROM dbo.vw_station_peak_hours;", cn)
            except Exception:
                peak = pd.DataFrame()

            try:
                reloc = pd.read_sql("SELECT * FROM dbo.vw_relocation_candidate;", cn)
            except Exception:
                reloc = pd.DataFrame()

        return recent, peak, reloc

    except Exception as e:
        st.warning(f"DB 조회 실패 → CSV 모드로 전환합니다. 사유: {e}")
        return None, None, None


# -----------------------------
# 5) CSV 백업 읽기 (fallback)
# -----------------------------
@st.cache_data(ttl=60)
def load_from_csv():
    csv_path = Path("data") / "bike_status_all.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV가 없습니다: {csv_path}")
    return pd.read_csv(csv_path, encoding="utf-8-sig")


# -----------------------------
# 6) UI 상단 + 로딩
# -----------------------------
left, mid, right = st.columns([1, 1, 1])
with left:
    st.markdown("### 🚲 따릉이 모니터링 (DB 우선 / 운영형)")
with mid:
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.success("데이터 캐시가 초기화되었습니다. 1분 내 최신 데이터로 다시 로드됩니다.")

# 사이드바에서 lookback 조절 가능(연결 끊김/부하 줄이기)
st.sidebar.header("데이터 로딩 범위")
lookback = st.sidebar.slider("최근 조회 범위(분)", min_value=10, max_value=360, value=DEFAULT_LOOKBACK_MINUTES, step=10)

recent_df, peak_df, reloc_df = load_from_sql(lookback)

source_label = "SQL (DB 직연결)"
if recent_df is None:
    # CSV로 전환
    try:
        all_df = load_from_csv()
        all_df = coerce_and_enrich(all_df)

        # CSV는 전체에서 최신 스냅샷만 만들기
        latest_df = (
            all_df.sort_values("ts_utc", ascending=False)
            .groupby("station_id", as_index=False)
            .first()
        )

        peak_df = pd.DataFrame()
        reloc_df = pd.DataFrame()
        source_label = "CSV (백업)"
    except Exception as e:
        st.error(f"데이터를 불러올 수 없습니다: {e}")
        st.stop()
else:
    # DB에서 온 recent_df를 "스테이션별 최신 스냅샷"으로 축약
    recent_df = coerce_and_enrich(recent_df)
    latest_df = (
        recent_df.sort_values("ts_utc", ascending=False)
        .groupby("station_id", as_index=False)
        .first()
    )
    peak_df = coerce_and_enrich(peak_df)
    reloc_df = coerce_and_enrich(reloc_df)


# -----------------------------
# 7) KPI
# -----------------------------
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("스테이션 수", f"{latest_df['station_id'].nunique():,}" if "station_id" in latest_df.columns else "N/A")
with k2:
    st.metric("평균 가용률", f"{np.nanmean(latest_df['avail_ratio']):.2f}" if "avail_ratio" in latest_df.columns else "N/A")
with k3:
    if "ts_kst_str" in latest_df.columns and latest_df["ts_kst_str"].notna().any():
        st.metric("최신 시각(KST)", latest_df["ts_kst_str"].max())
    else:
        st.metric("최신 시각(KST)", "N/A")
with k4:
    st.metric("데이터 소스", source_label)

st.divider()


# -----------------------------
# 8) 필터
# -----------------------------
st.sidebar.header("필터")
name_query = st.sidebar.text_input("대여소명 검색", value="")

avail_max = float(latest_df["avail_ratio"].quantile(0.95)) if "avail_ratio" in latest_df.columns else 1.0
thresh = st.sidebar.slider("가용률 임계치(이하만 보기)", 0.0, 1.0, min(0.2, avail_max), 0.05)

ids = sorted(latest_df["station_id"].dropna().unique().tolist()) if "station_id" in latest_df.columns else []
sel_ids = st.sidebar.multiselect("대여소 선택", options=ids, default=[])

f = latest_df.copy()
if name_query.strip() and "station_name" in f.columns:
    q = name_query.strip().lower()
    f = f[f["station_name"].astype(str).str.lower().str.contains(q)]
if sel_ids:
    f = f[f["station_id"].isin(sel_ids)]
if "avail_ratio" in f.columns:
    f = f[f["avail_ratio"].astype(float) <= thresh]
if "ts_kst" in f.columns:
    f = f.sort_values("ts_kst", ascending=False)


# -----------------------------
# 9) 탭 UI
# -----------------------------
tab1, tab2, tab3, tab4 = st.tabs(["📋 표", "🗺️ 지도", "📈 시간대 혼잡도", "📦 재배치 후보"])

# 📋 표
with tab1:
    st.markdown("### 최신 스냅샷 (필터 적용)")
    show_cols = [c for c in ["station_id","station_name","bike_count","slots_available","avail_ratio","occ_ratio","rack_tot_cnt","ts_kst_str","lat","lon"] if c in f.columns]
    st.dataframe(display_df(f[show_cols]).head(800), use_container_width=True)

# 🗺️ 지도
with tab2:
    st.markdown("### 위치 분포 (가용률 색/크기)")
    try:
        import pydeck as pdk

        m = f.dropna(subset=["lat", "lon"]).copy()
        if "avail_ratio" in m.columns:
            norm = m["avail_ratio"].clip(0, 1).fillna(0.5)
            m["r"] = (255 * (1 - norm)).astype(int)
            m["g"] = (80 * (1 - abs(norm - 0.5) * 2)).astype(int)
            m["b"] = (255 * norm).astype(int)
            m["size"] = (300 * (1 - norm) + 50).astype(int)
        else:
            m["r"], m["g"], m["b"], m["size"] = 100, 100, 200, 80

        view_state = pdk.ViewState(
            latitude=float(m["lat"].median()) if len(m) else 37.5665,
            longitude=float(m["lon"].median()) if len(m) else 126.9780,
            zoom=11,
        )

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=m,
            get_position="[lon, lat]",
            get_fill_color="[r, g, b]",
            get_radius="size",
            pickable=True,
        )

        st.pydeck_chart(
            pdk.Deck(
                layers=[layer],
                initial_view_state=view_state,
                tooltip={"text": "{station_name}\n가용률: {avail_ratio}"},
            )
        )
    except Exception:
        st.info("pydeck을 사용할 수 없어 st.map으로 대체합니다.")
        if {"lat", "lon"}.issubset(f.columns):
            st.map(f.rename(columns={"lat": "latitude", "lon": "longitude"})[["latitude", "longitude"]])

# 📈 시간대 혼잡도
with tab3:
    st.markdown("### 시간대별 평균 가용률/점유율 (KST 기준)")
    if not peak_df.empty:
        peak_work = peak_df.copy()
        if "hour_utc" in peak_work.columns:
            h = pd.to_numeric(peak_work["hour_utc"], errors="coerce")
            peak_work["hour_kst"] = (h + 9) % 24
        else:
            peak_work["hour_kst"] = np.nan

        peak_work = peak_work.sort_values("hour_kst")
        st.dataframe(display_df(peak_work), use_container_width=True, height=320)

        if "availability_pct" in peak_work.columns:
            fig = plt.figure()
            plt.plot(peak_work["hour_kst"], peak_work["availability_pct"])
            plt.title("시간대별 평균 가용률 (KST)")
            plt.xlabel("시간 (KST)")
            plt.ylabel("평균 가용률(%)")
            plt.xticks(range(0, 24, 2))
            st.pyplot(fig)
    else:
        st.info("vw_station_peak_hours 뷰가 없어 차트를 표시할 수 없습니다.")

# 📦 재배치 후보
with tab4:
    st.markdown("### 재배치 후보")
    if not reloc_df.empty:
        st.dataframe(display_df(reloc_df), use_container_width=True)
    else:
        st.info("vw_relocation_candidate 뷰가 비어 있습니다.")

# CSV 다운로드
st.download_button(
    "📥 현재 목록 CSV로 다운로드 (한글 컬럼)",
    display_df(f).to_csv(index=False).encode("utf-8-sig"),
    "bike_status_current_kor.csv",
)

st.caption("데이터 소스: Azure SQL (최근 N분 조회 → 최신 스냅샷), 표시: UTC→KST / 실패 시 CSV")
