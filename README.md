# 🚲 서울 따릉이 실시간 모니터링 시스템 (Azure 기반)

서울시 공공 API를 활용하여  
**따릉이 대여소 상태를 5분 단위로 수집 → 저장 → 분석 → 시각화**하는  
End-to-End 데이터 파이프라인 프로젝트입니다.

> ✔ 실시간 데이터 수집  
> ✔ 클라우드 기반 자동화  
> ✔ 운영 관점 모니터링 대시보드 구현

---

## 🔗 데모
- Streamlit 대시보드 (로컬 실행)
- 최신 스냅샷 / 지도 / 시간대 분석 / 재배치 후보 시각화

---

## 🏗 시스템 아키텍처

Seoul Open API
↓ (5분 주기)
Azure Functions (Timer Trigger)
↓
Azure Blob Storage (raw JSON)
↓
Azure Data Factory (ETL)
↓
Azure SQL Database
↓
Streamlit Dashboard

## 🧩 사용 기술 스택

| 구분 | 기술 |
|---|---|
| 수집 | Azure Functions (Python) |
| 저장 | Azure Blob Storage |
| ETL | Azure Data Factory |
| DB | Azure SQL Database |
| 시각화 | Streamlit, PyDeck |
| 언어 | Python, SQL |
| 기타 | Pandas, PyODBC |

---

## ⏱ 데이터 수집 방식

- **5분 간격 자동 수집**
- 서울시 따릉이 Open API 호출
- 전체 대여소(약 2,700개) 페이지네이션 처리
- UTC 기준 저장 → 시각화 시 KST 변환

---

## 📊 대시보드 기능

### 1️⃣ KPI 요약
- 전체 스테이션 수
- 평균 가용률
- 최신 수집 시각(KST)
- 데이터 소스(DB / CSV fallback)

### 2️⃣ 최신 스냅샷 테이블
- 대여소명
- 현재 자전거 수
- 가용률 / 점유율
- 위도 / 경도

### 3️⃣ 지도 시각화
- 가용률 기반 색상 / 크기 표현
- 혼잡 지역 직관적 파악

### 4️⃣ 시간대별 분석
- 시간대(KST) 기준 평균 가용률 / 점유율
- 운영 패턴 분석 가능

### 5️⃣ 재배치 후보 도출
- 가용률 임계치 이하 대여소 자동 필터링

---

## 🧠 설계 포인트 (중요)

- **DB 우선 → 실패 시 CSV fallback**
- Streamlit 캐시 전략으로 DB 부하 최소화
- UTC ↔ KST 명확한 시간대 분리
- PK 충돌 방지를 위한 스냅샷 설계
- 운영 환경 기준 자동화 구성

---

## ▶ 실행 방법

### 1. Azure Functions
```bash
func start

### 2. Streamlit
streamlit run app/app.py

## 📸 스크린샷
<img width="2555" height="996" alt="스크린샷 2025-12-15 130017" src="https://github.com/user-attachments/assets/b8a08870-87e1-4d93-a446-35bc67fa6d75" />
<img width="2548" height="1032" alt="스크린샷 2025-12-15 130008" src="https://github.com/user-attachments/assets/dc57e820-740e-4a8e-8d71-44d705dead70" />
<img width="2553" height="830" alt="스크린샷 2025-12-15 125959" src="https://github.com/user-attachments/assets/a5c76ecd-5b3a-4eb7-8f2b-bcdd3ff89a26" />
<img width="2544" height="920" alt="스크린샷 2025-12-15 125951" src="https://github.com/user-attachments/assets/f308780c-40de-427c-ab4a-ca79ab8111b7" />
<img width="2536" height="952" alt="스크린샷 2025-12-15 125745" src="https://github.com/user-attachments/assets/c4920a04-1b63-40ff-9047-acfb9b1596fe" />
<img width="2550" height="754" alt="스크린샷 2025-12-15 125733" src="https://github.com/user-attachments/assets/963c0154-c8d4-4394-87a5-f7bec98f6d5d" />
<img width="2545" height="1048" alt="스크린샷 2025-12-15 125724" src="https://github.com/user-attachments/assets/c61c2d4c-132c-41d2-940c-83f2988ba122" />
<img width="2550" height="896" alt="스크린샷 2025-12-15 125715" src="https://github.com/user-attachments/assets/796d4d1d-843f-45df-a793-284f059ce464" />

## 🔮 향후 개선 아이디어

Blob 이벤트 기반 파이프라인 트리거
이상치 감지(급격한 가용률 변화)
관리자용 재배치 알림
비용 최적화 (서버리스 조정)

