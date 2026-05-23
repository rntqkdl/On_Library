<div align="center">
  <img src="./assets/on_library_cover.png" alt="온서관 프로젝트 대표 이미지" width="100%" />
</div>

# 📚 온서관 On Library

> **책이 내게 오는 이동식 도서관 노선 최적화 MVP**  
> 진안군·임실군의 문화복지 접근성을 높이기 위한 데이터 기반 이동식 도서관 버스 시뮬레이션 서비스

<br/>

## 📌 프로젝트 소개

**온서관**은 교통소외지역의 고령층과 청소년이 도서관·문화복지 인프라에 접근하기 어려운 문제를 해결하기 위해 기획된 **이동식 도서관 버스 노선 최적화 MVP**입니다.

전북특별자치도 **진안군**과 **임실군**을 주요 대상 지역으로 설정하고, 각 지역의 대표 도서관을 출발 허브로 지정하여 면사무소, 마을회관, 학교, 보건소, 터미널, 경로당, 문화시설 등 생활거점을 순회하는 노선을 생성합니다.

본 프로젝트는 단순한 지도 시각화가 아니라, **실제 도로 기반 주행거리와 주행시간**을 반영하여 이동식 도서관 버스가 하루 안에 운영 가능한지 검증하는 것을 목표로 합니다.

또한 기존의 하드코딩 기반 후보지 점수화 방식을 개선하여, **연령별 인구 데이터, 버스정류장 접근성, 공공시설 위치 데이터, 외부 교통 API**를 함께 활용하는 데이터 기반 입지 선정 구조로 고도화하고 있습니다.

<br/>

## 👥 팀 소개

| 이름   | 소속                        | 담당                                    |
| ------ | --------------------------- | --------------------------------------- |
| 정세은 | 전북대학교 문헌정보학과     | 총괄 기획, 데이터 분석, 서비스 디자인   |
| 안성민 | 전북대학교 IT융합기전공학과 | 데이터 분석, 노선 최적화, MVP 모델 구현 |

<br/>

## 🎯 핵심 문제

지방 중소도시와 농촌 지역에서는 도서관이 존재하더라도 실제 이용자는 다음과 같은 어려움을 겪습니다.

- 고령층의 이동권 약화
- 청소년의 독서·학습 인프라 접근성 부족
- 면 단위 지역의 대중교통 배차 간격 문제
- 도서관·복지시설이 읍내 중심부에 집중되는 구조
- 정류장은 가까워도 실제 노선·배차·이동시간이 불편한 문제

따라서 본 프로젝트는 **사람이 도서관에 가는 방식**이 아니라  
**도서관이 사람에게 찾아가는 방식**으로 문제를 해결하고자 합니다.

<br/>

## 🚌 서비스 개요

### 온서관 MVP v1.0

온서관 MVP는 전북 진안군과 임실군의 대표 도서관을 허브로 두고, 이동식 도서관 버스가 생활거점을 순회하는 노선을 자동 생성합니다.

| 구분        | 내용                                                                                           |
| ----------- | ---------------------------------------------------------------------------------------------- |
| 서비스명    | 온서관 On Library                                                                              |
| 서비스 유형 | 이동식 도서관 버스 노선 최적화 MVP                                                             |
| 대상 지역   | 전북특별자치도 진안군, 임실군                                                                  |
| 핵심 사용자 | 고령층, 청소년, 도서관 운영자, 지자체 담당자                                                   |
| 분석 방식   | 공공데이터 기반 입지 선정 + Naver Maps API 기반 도로 경로 계산 + TAGO API 기반 교통소외 고도화 |
| 결과물      | 노선 지도 HTML, 노선 요약 CSV, 후보지 점수 CSV, Streamlit MVP 대시보드                         |

<br/>

## 🗺️ 고정 출발 허브

본 프로젝트의 노선은 각 지역의 대표 도서관에서 출발하고, 순회 후 다시 해당 도서관으로 복귀하는 **Hub-and-Spoke 구조**로 설계됩니다.

| 지역   | 출발 허브 도서관               |
| ------ | ------------------------------ |
| 진안군 | 전북특별자치도교육청진안도서관 |
| 임실군 | 임실군립도서관                 |

### 노선 운영 기준

| 항목              |                   기준 |
| ----------------- | ---------------------: |
| 지역별 차량 수    |                    3대 |
| 총 차량 수        |                    6대 |
| 차량당 정차지 수  |                    6개 |
| 하루 총 방문 거점 |                   36개 |
| 지점별 정차 시간  |                   30분 |
| 운영 가능 기준    | 총 운영시간 360분 이하 |

<br/>

## 🧑🏻‍💻 주요 기능

### 1. 지역 타당성 분석

진안군·임실군의 연령별 인구 데이터를 기반으로 고령층과 청소년 인구 구조를 분석합니다.

- 10대 인구 비율
- 60세 이상 인구 비율
- 읍·면 단위 고령층 분포
- 세대 불균형 지표
- 문화복지 접근성 개선 필요 지역 도출

<br/>

### 2. 데이터 기반 입지 적합성 분석

기존 MVP에서는 버스정류장명에 포함된 키워드를 기준으로 면사무소, 마을회관, 학교, 보건소, 터미널 등을 후보지로 분류하고, 시설 유형별 점수를 부여하는 방식으로 정차 후보지를 선정했습니다.

고도화 버전에서는 하드코딩된 후보지 점수화를 줄이고, 실제 공공데이터를 활용해 후보지의 입지 적합성을 계산합니다.

```text
입지 적합성 점수 =
수요지수 × 0.4
+ 접근성지수 × 0.3
+ 공공거점지수 × 0.2
+ 운영가능성지수 × 0.1
```

| 지표           | 의미                                             | 활용 데이터                                               |
| -------------- | ------------------------------------------------ | --------------------------------------------------------- |
| 수요지수       | 고령층·청소년 이용 가능성이 높은 지역인지 평가   | 연령별 인구 데이터                                        |
| 접근성지수     | 후보지 주변 대중교통 접근성이 좋은지 평가        | 버스정류장 위치 데이터                                    |
| 공공거점지수   | 주민 공동 이용 가능성이 높은 공공시설인지 평가   | 경로당, 마을회관, 학교, 보건시설, 문화시설, 터미널 데이터 |
| 운영가능성지수 | 이동식 도서관 버스가 정차·운영하기 적합한지 평가 | 시설 유형별 운영 기준값                                   |

<br/>

### 3. 생활거점 후보지 생성

온서관의 정차 후보지는 두 가지 방식으로 생성됩니다.

#### 3-1. 공공시설 데이터 기반 후보지

- 경로당
- 마을회관
- 노인복지시설
- 보건지소 및 진료소
- 학교
- 문화공간
- 문화 및 집회시설
- 주민복지시설
- 어린이놀이시설
- 터미널
- 의료기관
- 정신건강센터
- 약국

#### 3-2. 버스정류장 데이터 기반 자동 후보지

정류장명에 다음과 같은 키워드가 포함된 경우 생활거점 후보지로 자동 추출합니다.

- 면사무소
- 행정복지센터
- 마을회관
- 경로당
- 학교
- 보건소
- 의료원
- 터미널
- 도서관

이후 공공시설 후보지와 버스정류장 기반 후보지를 병합하고 중복을 제거한 뒤, 각 후보지의 수요지수, 접근성지수, 공공거점지수, 운영가능성지수를 계산하여 최종 입지 적합성 점수를 산정합니다.

<br/>

### 4. Naver Maps API 기반 실제 도로 경로 계산

Naver Directions API를 활용하여 단순 직선거리가 아닌 **실제 도로 기반 주행거리와 주행시간**을 계산합니다.

- 실제 도로 경로 PolyLine 생성
- 구간별 주행거리 계산
- 구간별 예상 주행시간 계산
- API 실패 시 Haversine 기반 fallback 처리
- 주소만 존재하는 공공시설은 Naver Geocoding API로 위도·경도 변환

<br/>

### 5. TAGO 버스노선정보 API 연계

TAGO 버스노선정보 API는 향후 교통소외 보정지표를 고도화하기 위해 활용합니다.

현재 MVP에서는 정류장 위치 기반 접근성 분석을 우선 적용하고, TAGO API는 2차 고도화 단계에서 노선 수, 경유 정류장, 첫차·막차, 배차간격 데이터를 활용하여 교통소외지수를 정교화하는 데 사용합니다.

| 기능                         | 활용 데이터                             | 온서관 적용 방향                |
| ---------------------------- | --------------------------------------- | ------------------------------- |
| 도시코드 목록 조회           | 지역별 cityCode                         | 진안·임실 버스 데이터 호출 기준 |
| 노선번호 목록 조회           | 노선ID, 노선번호, 기점, 종점            | 후보지 주변 노선 수 산정        |
| 노선별 경유 정류소 목록 조회 | 정류소명, 정류소 순번, 위도, 경도       | 후보지 주변 실제 경유 노선 확인 |
| 노선정보항목 조회            | 첫차, 막차, 평일·토요일·일요일 배차간격 | 배차간격 기반 교통소외도 보정   |

<br/>

### 6. 허브 앤 스포크 노선 생성

각 지역의 대표 도서관을 허브로 하여 차량별 순회 노선을 생성합니다.

```text
진안 노선:
전북특별자치도교육청진안도서관
→ 생활거점 1
→ 생활거점 2
→ 생활거점 3
→ 생활거점 4
→ 생활거점 5
→ 생활거점 6
→ 전북특별자치도교육청진안도서관 복귀

임실 노선:
임실군립도서관
→ 생활거점 1
→ 생활거점 2
→ 생활거점 3
→ 생활거점 4
→ 생활거점 5
→ 생활거점 6
→ 임실군립도서관 복귀
```

<br/>

### 7. 실제 도로 기반 TSP 최적화

선정된 후보지를 대상으로 Naver Directions API를 통해 실제 도로 이동시간을 계산하고, 각 차량이 방문해야 할 정차지 순서를 최적화합니다.

```text
대표 도서관 허브
→ 후보 정차지 전체 방문
→ 대표 도서관 복귀
```

이 과정에서 총 이동시간이 가장 짧은 순서를 선택하여 이동식 도서관 버스의 순회 노선을 생성합니다.

<br/>

### 8. Folium 지도 시각화

생성된 노선을 HTML 지도 형태로 시각화합니다.

지도에는 다음 정보가 포함됩니다.

- 허브 도서관 H 마커
- 방문 순서 번호 마커
- 노선별 색상 구분
- Naver 실제 도로 경로 실선 표시
- Haversine fallback 구간 점선 표시
- 노선별 Layer Control
- 노선별 총 운영시간 요약 박스

<br/>

### 9. Streamlit MVP 대시보드

`mvp_app.py`를 통해 온서관 MVP를 웹 대시보드 형태로 시연할 수 있습니다.

대시보드 구성:

- 서비스 소개 Hero 영역
- KPI 카드
- 지역 선택
- 노선 선택
- 실제 도로 기반 지도 표시
- 노선별 운영표
- 구간별 상세표
- 후보지 선정 근거표
- 노선 운영 판단 근거표
- TAGO API 연계 현황
- CSV 다운로드

<br/>

## 🛠️ 기술 스택

### Data Analysis & Optimization

<div>
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white"/>
  <img src="https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white"/>
</div>

<br/>

### Map & Route API

<div>
  <img src="https://img.shields.io/badge/Naver%20Maps%20API-03C75A?style=for-the-badge&logo=naver&logoColor=white"/>
  <img src="https://img.shields.io/badge/TAGO%20API-005BAC?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Folium-77B829?style=for-the-badge&logo=leaflet&logoColor=white"/>
  <img src="https://img.shields.io/badge/Haversine-2C7BE5?style=for-the-badge"/>
</div>

<br/>

### MVP Dashboard

<div>
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white"/>
  <img src="https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white"/>
</div>

<br/>

### Environment

<div>
  <img src="https://img.shields.io/badge/VSCode-007ACC?style=for-the-badge&logo=visualstudiocode&logoColor=white"/>
  <img src="https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white"/>
  <img src="https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white"/>
</div>

<br/>

## 📂 프로젝트 구조

```text
On_Library/
├─ naver_route_optimizer.py              # Naver API 기반 노선 최적화 메인 코드
├─ google_route_optimizer.py             # 기존 백업 코드
├─ mvp_app.py                            # Streamlit MVP 대시보드
├─ requirements.txt                      # Python 패키지 목록
├─ README.md                             # 프로젝트 설명 문서
├─ .env.example                          # 환경변수 예시 파일
├─ .gitignore
│
├─ assets/
│  └─ on_library_cover.png               # README 대표 이미지
│
├─ config/
│  ├─ on_library_config.yaml             # 운영 기준, 허브, 점수 가중치 설정
│  ├─ facility_scores.csv                # 시설 유형별 공공성·운영가능성 기준
│  └─ .gitkeep                           # 후보지 CSV는 실행 시 생성
│
├─ data/
│  ├─ .gitkeep
│  └─ raw/
│     └─ .gitkeep                        # 원본 데이터는 저장소에 포함하지 않음
│
├─ output/
│  └─ .gitkeep                           # 분석 산출물은 실행 시 생성
│
└─ scripts/
   ├─ prepare_data.py                    # 원본 데이터 정제
   ├─ check_naver_api.py                 # Naver API 연결 확인
   ├─ check_tago_api.py                  # TAGO API 연결 확인
   ├─ check_tago_citycodes.py            # TAGO 도시코드 확인
   ├─ build_site_candidates.py           # 데이터 기반 후보지 점수화
   ├─ build_mvp_decision_tables.py       # 후보지·노선 의사결정 테이블 생성
   ├─ build_tago_bus_context.py          # TAGO 노선 맥락 데이터 생성
   ├─ patch_naver_optimizer_candidates.py # 최적화 코드에 후보지 적용
   ├─ build_accessibility_mvp.py         # 접근성 분석 보조 스크립트
   └─ run_mvp.ps1                        # Streamlit 실행 스크립트
```

<br/>

## 📊 사용 데이터

본 프로젝트는 공공데이터를 기반으로 분석을 수행하되, 원본 데이터 파일은 저장소에 포함하지 않습니다.  
데이터는 사용자가 직접 공공데이터포털, 지자체 데이터 포털, Naver Maps API, TAGO API 등을 통해 내려받아 `data/raw/` 폴더에 배치해야 합니다.

| 데이터 범주            | 활용 목적                                               |
| ---------------------- | ------------------------------------------------------- |
| 도서관 위치 데이터     | 진안·임실 대표 도서관 허브 설정                         |
| 버스정류장 위치 데이터 | 후보지 주변 접근성 계산                                 |
| 연령별 인구 데이터     | 고령층·청소년 수요지수 계산                             |
| 경로당·마을회관 데이터 | 고령층 생활거점 후보지 생성                             |
| 학교·어린이시설 데이터 | 청소년·아동 생활거점 후보지 생성                        |
| 보건·의료시설 데이터   | 보건복지 거점 후보지 생성                               |
| 문화·복지시설 데이터   | 문화복지 생활거점 후보지 생성                           |
| 터미널·교통시설 데이터 | 교통거점 후보지 생성                                    |
| TAGO 버스노선정보 API  | 노선 수, 경유 정류장, 배차간격 기반 교통소외지수 고도화 |

<br/>

### 데이터 공개 범위

본 저장소에는 개인정보, 원본 공공데이터, API 응답 결과, 분석 산출물 CSV/HTML 파일을 포함하지 않습니다.

- 원본 데이터는 `data/raw/` 폴더에 사용자가 직접 배치합니다.
- 분석 결과는 `output/` 폴더에 생성되며 GitHub에는 업로드하지 않습니다.
- API 인증키는 `.env`에 저장하고, 저장소에는 `.env.example`만 포함합니다.
- 후보지 좌표와 점수 결과가 포함된 산출물은 재현 실행을 통해 생성합니다.
- `config/manual_candidates.csv`는 실행 과정에서 생성되는 후보지 결과 파일이므로 공개 저장소에서는 제외합니다.

<br/>

## ⚙️ 설치 가이드

### 1. 저장소 클론

```bash
git clone https://github.com/rntqkdl/On_Library.git
cd On_Library
```

<br/>

### 2. Python 가상환경 생성

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

<br/>

### 3. 패키지 설치

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

<br/>

## 🔐 환경변수 설정

Naver Maps API와 TAGO 버스노선정보 API를 사용하기 위해 `.env` 파일이 필요합니다.

### 1. `.env.example` 복사

Windows:

```powershell
copy .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

<br/>

### 2. `.env` 작성

```env
NAVER_REPRESENTATIVE_ACCOUNT=your_email@example.com
NAVER_MAPS_APP_NAME=my-map-service

NAVER_CLIENT_ID=your_naver_api_key_id
NAVER_CLIENT_SECRET=your_naver_api_key

NAVER_DIRECTION_OPTION=trafast
NAVER_API_SLEEP_SECONDS=0.5
NAVER_CONNECT_TIMEOUT=30
NAVER_READ_TIMEOUT=90

DATA_GO_KR_SERVICE_KEY=your_data_go_kr_decoding_service_key
```

주의사항:

- `.env` 파일은 GitHub에 업로드하지 않습니다.
- `NAVER_CLIENT_ID`에는 Naver Cloud Maps Application의 API Key ID를 입력합니다.
- `NAVER_CLIENT_SECRET`에는 Naver Cloud Maps Application의 API Key를 입력합니다.
- `DATA_GO_KR_SERVICE_KEY`에는 공공데이터포털의 **일반 인증키 Decoding 값**을 입력합니다.
- Python `requests.get(url, params=params)` 방식으로 호출할 경우 Decoding 키를 우선 사용합니다.
- 브라우저 주소창에 API URL을 직접 붙여넣을 경우 Encoding 키를 사용할 수 있습니다.
- TAGO 버스노선정보 API를 사용하려면 공공데이터포털에서 해당 API 활용 신청이 되어 있어야 합니다.

<br/>

## 🚀 실행 방법

### 1. 데이터 정제

```bash
python scripts/prepare_data.py
```

<br/>

### 2. Naver Maps API 연결 확인

```bash
python scripts/check_naver_api.py
```

정상 연결 시 예시:

```text
Directions API 연결 성공
도로 주행거리: 13.27 km
예상 주행시간: 15.7 분

Geocoding API 연결 성공
```

<br/>

### 3. TAGO 버스노선정보 API 연결 확인

```bash
python scripts/check_tago_api.py
```

<br/>

### 4. TAGO 도시코드 확인

```bash
python scripts/check_tago_citycodes.py
```

<br/>

### 5. 데이터 기반 후보지 점수화

```bash
python scripts/build_site_candidates.py
```

실행 후 아래 파일이 생성됩니다.

| 파일                                         | 설명                                             |
| -------------------------------------------- | ------------------------------------------------ |
| `config/manual_candidates.csv`               | 노선 최적화에 투입할 최종 후보지 목록            |
| `output/site_selection_candidate_scores.csv` | 후보지별 수요·접근성·공공성·운영가능성 점수 결과 |
| `output/geocode_cache.json`                  | 주소 기반 좌표 변환 캐시                         |

<br/>

### 6. 후보지 설정을 노선 최적화 코드에 적용

```bash
python scripts/patch_naver_optimizer_candidates.py
```

<br/>

### 7. 노선 최적화 실행

테스트 실행:

```bash
python naver_route_optimizer.py --region all --provider naver --data-dir data --output-dir output --data-candidate-limit 8 --naver-direction-option trafast
```

최종 실행:

```bash
python naver_route_optimizer.py --region all --provider naver --data-dir data --output-dir output --data-candidate-limit 12 --naver-direction-option trafast
```

<br/>

### 8. MVP 의사결정 테이블 생성

```bash
python scripts/build_mvp_decision_tables.py
```

실행 후 아래 파일이 생성됩니다.

| 파일                                      | 설명                  |
| ----------------------------------------- | --------------------- |
| `output/mvp_candidate_decision_table.csv` | 후보지 선정 근거표    |
| `output/mvp_route_decision_summary.csv`   | 노선 운영 판단 요약표 |

<br/>

### 9. TAGO 노선 맥락 데이터 생성

```bash
python scripts/build_tago_bus_context.py
```

실행 후 아래 파일이 생성됩니다.

| 파일                               | 설명                              |
| ---------------------------------- | --------------------------------- |
| `output/tago_citycodes.csv`        | TAGO 도시코드 목록                |
| `output/tago_target_citycodes.csv` | 진안·임실·전북 관련 도시코드 후보 |
| `output/tago_route_list.csv`       | TAGO 노선 목록 조회 결과          |

<br/>

### 10. MVP 대시보드 실행

```bash
streamlit run mvp_app.py
```

또는 Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_mvp.ps1
```

<br/>

## 🖥️ 결과물

노선 최적화 및 대시보드 실행 과정에서 `output/` 폴더에 다음 파일이 생성됩니다.  
해당 결과물은 재현 가능한 산출물이므로 GitHub에는 업로드하지 않습니다.

| 파일                                  | 설명                               |
| ------------------------------------- | ---------------------------------- |
| `all_naver_route_map.html`            | 진안·임실 전체 노선 지도           |
| `jinan_naver_route_map.html`          | 진안군 노선 지도                   |
| `imsil_naver_route_map.html`          | 임실군 노선 지도                   |
| `all_naver_route_summary.csv`         | 노선별 총 주행거리·운영시간 요약   |
| `all_naver_route_result.csv`          | 구간별 도로거리·주행시간·경로 상세 |
| `site_selection_candidate_scores.csv` | 후보지별 입지 적합성 점수          |
| `mvp_candidate_decision_table.csv`    | 후보지 선정 근거표                 |
| `mvp_route_decision_summary.csv`      | 노선 운영 판단 요약표              |
| `tago_route_list.csv`                 | TAGO 버스노선정보 API 조회 결과    |
| `geocode_cache.json`                  | 주소 기반 좌표 변환 결과 캐시      |

<br/>

## 📈 운영 가능성 판단 기준

온서관 MVP는 다음 기준으로 노선 운영 가능성을 판단합니다.

```text
총 운영시간 = 총 도로 주행시간 + 총 정차시간
```

| 기준                | 판정      |
| ------------------- | --------- |
| 총 운영시간 ≤ 360분 | 운영 가능 |
| 총 운영시간 > 360분 | 조정 필요 |

<br/>

## 🧠 핵심 알고리즘

### 1. 다기준 입지 적합성 분석

온서관은 후보지를 단순 거리 기준으로 선정하지 않고, 여러 공공데이터를 결합하여 입지 적합성 점수를 계산합니다.

```text
입지 적합성 점수 =
수요지수 × 0.4
+ 접근성지수 × 0.3
+ 공공거점지수 × 0.2
+ 운영가능성지수 × 0.1
```

- **수요지수**: 후보지가 속한 읍·면의 고령층·청소년 비율을 반영합니다.
- **접근성지수**: 후보지와 가장 가까운 버스정류장 거리, 500m 내 정류장 수를 반영합니다.
- **공공거점지수**: 경로당, 마을회관, 학교, 보건시설, 터미널 등 공공시설 유형을 반영합니다.
- **운영가능성지수**: 이동식 도서관 버스가 정차·운영하기 적합한 시설 유형인지를 반영합니다.

<br/>

### 2. 실제 도로 기반 TSP 최적화

선정된 후보지를 대상으로 Naver Directions API를 통해 실제 도로 이동시간을 계산하고, 각 차량이 방문해야 할 정차지 순서를 최적화합니다.

```text
대표 도서관 허브
→ 후보 정차지 전체 방문
→ 대표 도서관 복귀
```

이 과정에서 총 이동시간이 가장 짧은 순서를 선택하여 이동식 도서관 버스의 순회 노선을 생성합니다.

<br/>

### 3. 후보지 선정 근거표

MVP 대시보드에서는 각 후보지의 선정 근거를 표로 제공합니다.

| 항목           | 설명                                        |
| -------------- | ------------------------------------------- |
| 수요지수       | 고령층·청소년 수요 반영                     |
| 접근성지수     | 최근접 정류장 거리와 500m 내 정류장 수 반영 |
| 공공거점지수   | 공공시설 유형에 따른 주민 이용 가능성 반영  |
| 운영가능성지수 | 이동식 도서관 정차 가능성 반영              |
| 선정근거       | 점수 기준을 해석한 설명 문장                |

<br/>

### 4. 교통소외 보정지표 고도화

TAGO 버스노선정보 API를 활용하면 후보지 주변의 실제 노선 수, 경유 정류장, 첫차·막차, 배차간격을 반영할 수 있습니다.

향후에는 다음과 같은 교통소외지표를 추가할 수 있습니다.

```text
교통소외지수 =
배차간격 점수
+ 노선 수 부족 점수
+ 경유 정류장 부족 점수
+ 첫차·막차 접근성 점수
```

이를 통해 단순히 정류장이 가까운지뿐 아니라, 실제로 버스를 이용하기 편한 지역인지까지 반영할 수 있습니다.

<br/>

## 🧪 MVP 시연 흐름

1. **문제 제기**  
   진안군·임실군은 고령층과 청소년의 문화복지 접근성 보완이 필요한 지역입니다.

2. **데이터 기반 후보지 선정**  
   도서관 위치, 버스정류장 위치, 연령별 인구, 공공시설 데이터를 활용하여 생활거점 후보지를 선정합니다.

3. **입지 적합성 점수화**  
   수요지수, 접근성지수, 공공거점지수, 운영가능성지수를 결합하여 후보지 우선순위를 산정합니다.

4. **허브 설정**  
   진안군은 전북특별자치도교육청진안도서관, 임실군은 임실군립도서관을 출발 허브로 설정합니다.

5. **실제 도로 기반 노선 생성**  
   Naver Directions API를 활용하여 실제 도로 주행거리와 주행시간을 계산합니다.

6. **운영 가능성 검증**  
   차량당 6개 지점, 지점별 30분 정차 기준으로 360분 이하 운영 가능 여부를 검증합니다.

7. **후보지 선정 근거 확인**  
   Streamlit 대시보드에서 각 후보지의 수요·접근성·공공성·운영가능성 점수와 선정근거를 확인합니다.

8. **TAGO API 연계 현황 확인**  
   TAGO API를 통해 도시코드와 노선 목록을 확인하고, 향후 배차간격 기반 교통소외지수로 확장합니다.

<br/>

## 🔧 문제 해결

### 문제 1. `ModuleNotFoundError`

원인: 패키지가 설치되지 않았거나 가상환경이 활성화되지 않음

해결:

```bash
pip install -r requirements.txt
```

<br/>

### 문제 2. `.env` 파일을 찾을 수 없음

원인: 프로젝트 루트에 `.env` 파일이 없음

해결:

```bash
copy .env.example .env
```

그 후 Naver API Key와 공공데이터포털 인증키를 입력합니다.

<br/>

### 문제 3. Naver API 401 오류

원인:

- API Key ID 또는 API Key 입력 오류
- Maps Application에 Directions API가 활성화되지 않음
- 잘못된 Application의 키 사용

해결:

- Naver Cloud Console에서 `my-map-service` Application 확인
- Directions 5, Geocoding 활성화 확인
- `.env`의 `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` 재확인

<br/>

### 문제 4. Naver API Timeout 오류

원인: 다중 경로 요청 중 API 응답 지연

해결:

`.env`에서 timeout과 sleep 값을 조정합니다.

```env
NAVER_API_SLEEP_SECONDS=0.5
NAVER_CONNECT_TIMEOUT=30
NAVER_READ_TIMEOUT=90
```

테스트 시에는 후보지 수를 줄여 실행합니다.

```bash
python naver_route_optimizer.py --region all --provider naver --data-dir data --output-dir output --data-candidate-limit 8 --naver-direction-option trafast
```

<br/>

### 문제 5. TAGO API 인증 오류

원인:

- 공공데이터포털 인증키 입력 오류
- Encoding/Decoding 키 사용 방식 오류
- 해당 API 활용 신청 미완료
- 활용 기간 만료
- 요청 제한 초과

해결:

- Python `requests.get(url, params=params)` 방식에서는 일반적으로 **Decoding 키**를 우선 사용합니다.
- 브라우저 URL 직접 호출 시에는 Encoding 키를 사용할 수 있습니다.
- 공공데이터포털에서 TAGO 버스노선정보 API 활용 신청 상태를 확인합니다.
- `.env`의 `DATA_GO_KR_SERVICE_KEY` 값을 재확인합니다.

<br/>

### 문제 6. 지도는 생성되지만 직선처럼 보임

원인:

- Naver path가 저장되지 않음
- fallback 구간이 많음
- route_path_json이 비어 있음

해결:

- `all_naver_route_result.csv`의 `source` 컬럼 확인
- `source=naver` 구간이 충분한지 확인
- Naver API 재실행

<br/>

### 문제 7. 후보지 선정 근거표가 보이지 않음

원인:

- `mvp_candidate_decision_table.csv`가 생성되지 않음
- `build_mvp_decision_tables.py` 실행 전 대시보드를 먼저 실행함

해결:

```bash
python scripts/build_mvp_decision_tables.py
```

<br/>

## 🌱 기대 효과

온서관은 다음과 같은 효과를 기대합니다.

- 고령층 문화복지 접근성 개선
- 청소년 독서·학습 접근성 보완
- 면 단위 지역의 도서관 접근성 강화
- 고정식 도서관 중심 서비스의 공간적 한계 보완
- 지자체 이동형 문화복지 사업의 의사결정 지원
- 공공시설 데이터를 활용한 생활거점 중심 노선 설계
- 후보지 선정 근거표를 통한 의사결정 투명성 강화
- 향후 승하차 수요·도서 대출 수요·배차간격·운영비 데이터를 결합한 실증형 모델로 확장 가능

<br/>

## 🔮 향후 고도화 방향

- TAGO API 기반 기존 버스 노선 및 배차 데이터 연계
- 정류장별 승하차 인원 데이터 반영
- 경로당·마을회관·학교 위치 데이터 정밀화
- 공영주차장·도로폭 데이터를 활용한 정차 가능성 보정
- 도서 대출 수요 기반 도서 큐레이션
- 전기·수소버스 운영비 및 탄소 감축 효과 분석
- 지자체 실증사업용 관리자 대시보드 고도화

<br/>

## 🧩 Repository

- GitHub Repository: https://github.com/rntqkdl/On_Library

<br/>

## 📞 Contact

| 담당                                  | 이름   | 소속                        | 이메일                 |
| ------------------------------------- | ------ | --------------------------- | ---------------------- |
| 총괄 기획·데이터 분석·서비스 디자인   | 정세은 | 전북대학교 문헌정보학과     | jeongseeun21@gmail.com |
| 데이터 분석·노선 최적화·MVP 모델 구현 | 안성민 | 전북대학교 IT융합기전공학과 | tjdals2299@gmail.com   |

<br/>

## 📝 Copyright

Copyright 2026. On Library. All rights reserved.
