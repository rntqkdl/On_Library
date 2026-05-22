<div align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:4ECDC4,100:2C7BE5&height=320&section=header&text=ON%20LIBRARY&fontSize=80&fontColor=FFFFFF&animation=fadeIn" />
</div>

# 📚 온서관 On Library

> **책이 내게 오는 이동식 도서관 노선 최적화 MVP**  
> 진안군·임실군의 문화복지 접근성을 높이기 위한 데이터 기반 이동식 도서관 버스 시뮬레이션 서비스

<br/>

## 📌 프로젝트 소개

**온서관**은 교통소외지역의 고령층과 청소년이 도서관·문화복지 인프라에 접근하기 어려운 문제를 해결하기 위해 기획된 **이동식 도서관 버스 노선 최적화 MVP**입니다.

전북특별자치도 **진안군**과 **임실군**을 주요 대상 지역으로 설정하고, 각 지역의 대표 도서관을 출발 허브로 지정하여 면사무소, 마을회관, 학교, 보건소 등 생활거점을 순회하는 노선을 생성합니다.

본 프로젝트는 단순한 지도 시각화가 아니라, **실제 도로 기반 주행거리와 주행시간**을 반영하여 이동식 도서관 버스가 하루 안에 운영 가능한지 검증하는 것을 목표로 합니다.

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

| 구분        | 내용                                                             |
| ----------- | ---------------------------------------------------------------- |
| 서비스명    | 온서관 On Library                                                |
| 서비스 유형 | 이동식 도서관 버스 노선 최적화 MVP                               |
| 대상 지역   | 전북특별자치도 진안군, 임실군                                    |
| 핵심 사용자 | 고령층, 청소년, 도서관 운영자, 지자체 담당자                     |
| 분석 방식   | 공공데이터 기반 후보지 선정 + Naver Maps API 기반 도로 경로 계산 |
| 결과물      | 노선 지도 HTML, 노선 요약 CSV, Streamlit MVP 대시보드            |

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
- 읍면동별 고령층 분포
- 세대 불균형 지표

<br/>

### 2. 생활거점 후보지 선정

버스정류장 위치 데이터를 활용하여 이동식 도서관 버스가 방문할 수 있는 생활거점 후보지를 추출합니다.

후보지 예시:

- 면사무소
- 행정복지센터
- 마을회관
- 경로당
- 초·중·고등학교
- 보건소
- 터미널
- 시장

<br/>

### 3. Naver Maps API 기반 실제 도로 경로 계산

Naver Directions API를 활용하여 단순 직선거리가 아닌 **실제 도로 기반 주행거리와 주행시간**을 계산합니다.

- 실제 도로 경로 PolyLine 생성
- 구간별 주행거리 계산
- 구간별 예상 주행시간 계산
- API 실패 시 Haversine 기반 fallback 처리

<br/>

### 4. 허브 앤 스포크 노선 생성

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

### 5. Folium 지도 시각화

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

### 6. Streamlit MVP 대시보드

`mvp_app.py`를 통해 온서관 MVP를 웹 대시보드 형태로 시연할 수 있습니다.

대시보드 구성:

- 서비스 소개 Hero 영역
- KPI 카드
- 지역 선택
- 노선 선택
- 실제 도로 기반 지도 표시
- 노선별 운영표
- 구간별 상세표
- 총 운영시간 그래프
- 총 주행거리 그래프
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
├─ google_route_optimizer.py        # 노선 최적화 메인 코드
├─ mvp_app.py                       # Streamlit MVP 대시보드
├─ requirements.txt                 # Python 패키지 목록
├─ README.md                        # 프로젝트 설명 문서
├─ .env.example                     # 환경변수 예시 파일
├─ .gitignore
│
├─ data/
│  ├─ 전북_도서관 위치.csv           # 실행용 도서관 위치 데이터
│  ├─ 전북_버스정류장_위치.csv       # 실행용 버스정류장 위치 데이터
│  └─ raw/                          # 원본 공공데이터 모음
│
├─ output/
│  ├─ all_naver_route_map.html       # 전체 노선 지도
│  ├─ jinan_naver_route_map.html     # 진안군 노선 지도
│  ├─ imsil_naver_route_map.html     # 임실군 노선 지도
│  ├─ all_naver_route_summary.csv    # 전체 노선 요약표
│  └─ all_naver_route_result.csv     # 구간별 상세 결과
│
└─ scripts/
   ├─ prepare_data.py                # 원본 데이터 정제
   ├─ check_naver_api.py             # Naver API 연결 확인
   ├─ patch_naver_timeout.py         # API timeout 보정 스크립트
   ├─ build_accessibility_mvp.py     # 접근성 분석 보조 스크립트
   └─ run_mvp.ps1                    # Streamlit 실행 스크립트
```

<br/>

## 📊 사용 데이터

| 데이터                      | 활용 목적                       |
| --------------------------- | ------------------------------- |
| 전북 도서관 위치 데이터     | 진안·임실 대표 도서관 허브 설정 |
| 전북 버스정류장 위치 데이터 | 생활거점 후보지 및 정차지 선정  |
| 진안군 연령별 인구현황      | 고령층·청소년 수요 분석         |
| 임실군 연령별 인구현황      | 고령층·청소년 수요 분석         |
| 수도권 도서관·정류장 데이터 | 비교 분석 및 확장 가능성 검토   |

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

Naver Maps API를 사용하기 위해 `.env` 파일이 필요합니다.

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

NAVER_CLIENT_ID=your_api_key_id
NAVER_CLIENT_SECRET=your_api_key

NAVER_DIRECTION_OPTION=trafast
NAVER_API_SLEEP_SECONDS=0.5
NAVER_CONNECT_TIMEOUT=30
NAVER_READ_TIMEOUT=90
```

주의사항:

- `.env` 파일은 GitHub에 업로드하지 않습니다.
- `NAVER_CLIENT_ID`에는 Naver Cloud Maps Application의 API Key ID를 입력합니다.
- `NAVER_CLIENT_SECRET`에는 API Key를 입력합니다.
- Directions API와 Geocoding API가 활성화되어 있어야 합니다.

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

### 3. 노선 최적화 실행

테스트 실행:

```bash
python google_route_optimizer.py --region all --provider naver --buses 2 --stops-per-bus 5 --data-dir data --output-dir output --data-candidate-limit 5 --naver-direction-option trafast
```

최종 실행:

```bash
python google_route_optimizer.py --region all --provider naver --buses 3 --stops-per-bus 6 --data-dir data --output-dir output --data-candidate-limit 12 --naver-direction-option trafast
```

<br/>

### 4. MVP 대시보드 실행

```bash
streamlit run mvp_app.py
```

또는 Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_mvp.ps1
```

<br/>

## 🖥️ 결과물

노선 최적화 실행 후 `output/` 폴더에 다음 파일이 생성됩니다.

| 파일                          | 설명                               |
| ----------------------------- | ---------------------------------- |
| `all_naver_route_map.html`    | 진안·임실 전체 노선 지도           |
| `jinan_naver_route_map.html`  | 진안군 노선 지도                   |
| `imsil_naver_route_map.html`  | 임실군 노선 지도                   |
| `all_naver_route_summary.csv` | 노선별 총 주행거리·운영시간 요약   |
| `all_naver_route_result.csv`  | 구간별 도로거리·주행시간·경로 상세 |

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

## 🧪 MVP 시연 흐름

1. **문제 제기**  
   진안군·임실군은 고령층과 청소년의 문화복지 접근성 보완이 필요한 지역입니다.

2. **데이터 기반 후보지 선정**  
   도서관 위치, 버스정류장 위치, 연령별 인구 데이터를 활용하여 생활거점 후보지를 선정합니다.

3. **허브 설정**  
   진안군은 전북특별자치도교육청진안도서관, 임실군은 임실군립도서관을 출발 허브로 설정합니다.

4. **실제 도로 기반 노선 생성**  
   Naver Directions API를 활용하여 실제 도로 주행거리와 주행시간을 계산합니다.

5. **운영 가능성 검증**  
   차량당 6개 지점, 지점별 30분 정차 기준으로 360분 이하 운영 가능 여부를 검증합니다.

6. **MVP 대시보드 시연**  
   Streamlit을 통해 노선 지도, 운영표, 구간 상세표, 그래프를 확인합니다.

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

그 후 Naver API Key를 입력합니다.

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
python google_route_optimizer.py --region all --provider naver --buses 2 --stops-per-bus 5 --data-dir data --output-dir output --data-candidate-limit 5 --naver-direction-option trafast
```

<br/>

### 문제 5. 지도는 생성되지만 직선처럼 보임

원인:

- Naver path가 저장되지 않음
- fallback 구간이 많음
- route_path_json이 비어 있음

해결:

- `all_naver_route_result.csv`의 `source` 컬럼 확인
- `source=naver` 구간이 충분한지 확인
- Naver API 재실행

<br/>

## 🌱 기대 효과

온서관은 다음과 같은 효과를 기대합니다.

- 고령층 문화복지 접근성 개선
- 청소년 독서·학습 접근성 보완
- 면 단위 지역의 도서관 접근성 강화
- 고정식 도서관 중심 서비스의 공간적 한계 보완
- 지자체 이동형 문화복지 사업의 의사결정 지원
- 향후 승하차 수요·도서 대출 수요·운영비 데이터를 결합한 실증형 모델로 확장 가능

<br/>

## 🔮 향후 고도화 방향

- 기존 버스 노선 및 배차 데이터 연계
- 정류장별 승하차 인원 데이터 반영
- 경로당·마을회관·학교 위치 데이터 정밀화
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
