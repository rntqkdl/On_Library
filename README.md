# 도서관 대중교통 접근성 진단 대시보드

서울·경기와 전북 농촌권인 진안·임실의 도서관-버스정류장 접근성 차이를 비교하고, 접근성 취약 도서관의 개선 우선순위를 제안하는 Streamlit MVP입니다.

인천 데이터 파일은 프로젝트에 남아 있어도 이번 분석에서는 사용하지 않습니다.

## 현재 폴더 구조

```text
C:\PB_Data
├─ data
├─ output
│  ├─ tables
│  ├─ maps
│  └─ figures
├─ raw_data
├─ scripts
│  ├─ build_accessibility_mvp.py
│  ├─ prepare_data.py
│  └─ run_mvp.ps1
├─ mvp_app.py
├─ requirements.txt
└─ README.md
```

## 데이터 파일 위치

분석 스크립트는 다음 위치를 자동 탐색합니다.

- `C:\PB_Data`
- `C:\PB_Data\raw_data`
- `C:\PB_Data\data`
- `C:\PB_Data\data\raw`

사용 데이터:

- 서울 인구: `2025 서울 연령별 인구수.xlsx`
- 경기 인구: `2025 경기 연령별 인구수.csv`
- 진안·임실 인구: `진안_202604_202604_연령별인구현황_월간.csv`, `임실_202604_202604_연령별인구현황_월간.csv`
- 서울 도서관: `서울특별시_도서관.csv`
- 경기 도서관: `경기도_도서관.csv`
- 전북 도서관: `전북_도서관 위치.xls`
- 서울 버스정류장: `전국 버스정류장 위치정보_(서울특별시).csv`
- 경기 버스정류장: `전국 버스정류장 위치정보_(경기도).csv`
- 전북 버스정류장: `전북_버스정류장_위치.xlsx`

## 설치 방법

```powershell
cd C:\PB_Data
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 분석 실행 방법

```powershell
python .\scripts\prepare_data.py
```

`prepare_data.py`는 `scripts\build_accessibility_mvp.py`를 호출해 접근성 분석 CSV, 지도 HTML, 그래프 PNG를 생성합니다.

## Streamlit 실행 방법

```powershell
streamlit run .\mvp_app.py
```

또는 한 번에 실행:

```powershell
.\scripts\run_mvp.ps1
```

## 산출물 위치

CSV:

- `output\tables\도서관별_접근성_분석결과.csv`
- `output\tables\지역별_접근성_요약.csv`
- `output\tables\권역별_접근성_요약.csv`
- `output\tables\도서관별_접근성_개선우선순위.csv`

지도:

- `output\maps\전체_도서관_접근성_지도.html`
- `output\maps\전북_진안_임실_도서관_접근성_지도.html`

그래프:

- `output\figures\그래프1_권역별_최근접정류장_평균거리.png`
- `output\figures\그래프2_권역별_도서관주변_정류장수.png`
- `output\figures\그래프3_지역별_60_79세_비율.png`
- `output\figures\그래프4_지역별_500m내_정류장수.png`
- `output\figures\그래프5_고령층비율_정류장접근성_비교.png`
- `output\figures\그래프6_접근성취약점수_TOP10.png`
- `output\figures\그래프7_취약점수_정류장수_산점도.png`

## 발표 시연 흐름

1. 서울·경기와 진안·임실의 접근성 차이 확인
2. 고령층 비율과 정류장 밀도 차이 확인
3. 지도에서 진안·임실 도서관 주변 정류장 분포 확인
4. 접근성 취약점수 TOP 도서관 확인
5. 도서관별 개선제안 확인
