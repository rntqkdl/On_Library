from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit.components.v1 import html


ROOT_DIR = Path(__file__).resolve().parent
TABLE_DIR = ROOT_DIR / "output" / "tables"
MAP_DIR = ROOT_DIR / "output" / "maps"
FIGURE_DIR = ROOT_DIR / "output" / "figures"

ACCESS_CSV = TABLE_DIR / "도서관별_접근성_분석결과.csv"
PRIORITY_CSV = TABLE_DIR / "도서관별_접근성_개선우선순위.csv"
REGION_SUMMARY_CSV = TABLE_DIR / "지역별_접근성_요약.csv"
AREA_SUMMARY_CSV = TABLE_DIR / "권역별_접근성_요약.csv"

FULL_MAP = MAP_DIR / "전체_도서관_접근성_지도.html"
RURAL_MAP = MAP_DIR / "전북_진안_임실_도서관_접근성_지도.html"

FIGURES = [
    "그래프1_권역별_최근접정류장_평균거리.png",
    "그래프2_권역별_도서관주변_정류장수.png",
    "그래프3_지역별_60_79세_비율.png",
    "그래프4_지역별_500m내_정류장수.png",
    "그래프5_고령층비율_정류장접근성_비교.png",
    "그래프6_접근성취약점수_TOP10.png",
    "그래프7_취약점수_정류장수_산점도.png",
]


st.set_page_config(page_title="도서관 대중교통 접근성 진단 대시보드", layout="wide")

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.4rem; }
    .hero {
        border: 1px solid #d6e8f5;
        border-radius: 8px;
        padding: 20px 24px;
        background: #f5fbff;
        margin-bottom: 18px;
    }
    .hero h1 { margin: 0 0 8px 0; font-size: 2rem; letter-spacing: 0; color: #174A7C; }
    .hero p { margin: 4px 0; color: #334155; }
    div[data-testid="stMetric"] {
        border: 1px solid #d6e8f5;
        border-radius: 8px;
        padding: 12px 14px;
        background: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    required = [ACCESS_CSV, PRIORITY_CSV, REGION_SUMMARY_CSV, AREA_SUMMARY_CSV]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(", ".join(missing))
    return (
        pd.read_csv(ACCESS_CSV, encoding="utf-8-sig"),
        pd.read_csv(PRIORITY_CSV, encoding="utf-8-sig"),
        pd.read_csv(REGION_SUMMARY_CSV, encoding="utf-8-sig"),
        pd.read_csv(AREA_SUMMARY_CSV, encoding="utf-8-sig"),
    )


def read_map(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(str(path))
    return path.read_text(encoding="utf-8")


def grade_style(row: pd.Series) -> list[str]:
    grade = row.get("개선필요도", "")
    colors = {
        "매우 높음": "background-color: #fde8e0;",
        "높음": "background-color: #fff1d9;",
        "보통": "background-color: #eef9ff;",
        "낮음": "background-color: #f3f8fc;",
    }
    return [colors.get(grade, "") for _ in row]


def filter_data(df: pd.DataFrame, area: str, region: str, grade: str) -> pd.DataFrame:
    filtered = df.copy()
    if area != "전체":
        filtered = filtered[filtered["비교권역"] == area]
    if region != "전체":
        filtered = filtered[filtered["분석지역"] == region]
    if grade != "전체":
        filtered = filtered[filtered["개선필요도"] == grade]
    return filtered


def metric_cards(df: pd.DataFrame) -> None:
    cols = st.columns(5)
    cols[0].metric("분석 도서관 수", f"{len(df):,}개")
    cols[1].metric("평균 최근접 거리", f"{df['최근접정류장거리_m'].mean():.1f}m")
    cols[2].metric("500m 내 평균 정류장", f"{df['500m내_정류장수'].mean():.1f}개")
    cols[3].metric("평균 60~79세 비율", f"{df['60_79세_비율'].mean():.1f}%")
    cols[4].metric("평균 취약점수", f"{df['접근성_취약점수'].mean():.1f}점")


def show_figures() -> None:
    st.subheader("권역 및 지역 비교 그래프")
    first_row = st.columns(2)
    for idx, figure in enumerate(FIGURES[:2]):
        path = FIGURE_DIR / figure
        if path.exists():
            first_row[idx].image(str(path), use_container_width=True)
    second_row = st.columns(2)
    for idx, figure in enumerate(FIGURES[2:4]):
        path = FIGURE_DIR / figure
        if path.exists():
            second_row[idx].image(str(path), use_container_width=True)
    third_row = st.columns(2)
    for idx, figure in enumerate(FIGURES[4:6]):
        path = FIGURE_DIR / figure
        if path.exists():
            third_row[idx].image(str(path), use_container_width=True)
    scatter_path = FIGURE_DIR / FIGURES[6]
    if scatter_path.exists():
        st.image(str(scatter_path), use_container_width=True)


def map_for_selection(area: str, region: str) -> Path:
    if area == "전북 농촌권(진안·임실)" or region in {"진안", "임실"}:
        return RURAL_MAP
    return FULL_MAP


st.markdown(
    """
    <section class="hero">
        <h1>도서관 대중교통 접근성 진단 대시보드</h1>
        <p>서울·경기와 전북 농촌권인 진안·임실의 도서관-버스정류장 접근성 차이를 비교합니다.</p>
        <p>최근접 정류장 거리, 반경별 정류장 수, 60~79세 인구 비율을 결합해 개선 우선순위를 제안합니다.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

try:
    access_df, priority_df, region_summary, area_summary = load_tables()
except FileNotFoundError as exc:
    st.error(f"분석 산출물이 없습니다: {exc}")
    st.info("먼저 `python scripts\\prepare_data.py` 또는 `scripts\\run_mvp.ps1`을 실행하세요.")
    st.stop()

with st.sidebar:
    st.header("필터")
    selected_area = st.selectbox("비교권역 선택", ["전체", "수도권(서울·경기)", "전북 농촌권(진안·임실)"])
    selected_region = st.selectbox("지역 선택", ["전체", "서울", "경기", "진안", "임실"])
    selected_grade = st.selectbox("개선 필요도 선택", ["전체", "매우 높음", "높음", "보통", "낮음"])

filtered = filter_data(access_df, selected_area, selected_region, selected_grade)
filtered_priority = filter_data(priority_df, selected_area, selected_region, selected_grade)

if filtered.empty:
    st.warning("선택한 조건에 해당하는 도서관이 없습니다.")
    st.stop()

metric_cards(filtered)

st.subheader("권역별 접근성 요약")
st.dataframe(area_summary, use_container_width=True, hide_index=True)

st.subheader("지역별 접근성 요약")
st.dataframe(region_summary, use_container_width=True, hide_index=True)

show_figures()

st.subheader("도서관별 개선 우선순위")
priority_cols = [
    "비교권역",
    "분석지역",
    "도서관명",
    "최근접정류장명",
    "최근접정류장거리_m",
    "300m내_정류장수",
    "500m내_정류장수",
    "1000m내_정류장수",
    "60_79세_비율",
    "접근성_취약점수",
    "개선필요도",
    "개선제안",
]
st.dataframe(
    filtered_priority[priority_cols].style.apply(grade_style, axis=1),
    use_container_width=True,
    hide_index=True,
)

st.subheader("접근성 지도")
try:
    html(read_map(map_for_selection(selected_area, selected_region)), height=720, scrolling=True)
except FileNotFoundError as exc:
    st.warning(f"지도 파일이 없습니다: {exc}")

st.subheader("도서관 상세 진단")
library_options = filtered_priority["도서관명"].tolist()
selected_library = st.selectbox("도서관 선택", library_options)
detail = filtered_priority[filtered_priority["도서관명"] == selected_library].iloc[0]

detail_cols = st.columns(4)
detail_cols[0].metric("최근접 정류장 거리", f"{detail['최근접정류장거리_m']:.1f}m")
detail_cols[1].metric("500m 내 정류장 수", f"{int(detail['500m내_정류장수'])}개")
detail_cols[2].metric("60~79세 비율", f"{detail['60_79세_비율']:.1f}%")
detail_cols[3].metric("취약점수", f"{detail['접근성_취약점수']:.1f}점")

st.markdown(
    f"""
    - **비교권역:** {detail['비교권역']}
    - **분석지역:** {detail['분석지역']}
    - **최근접 정류장:** {detail['최근접정류장명']}
    - **300m / 500m / 1000m 내 정류장 수:** {int(detail['300m내_정류장수'])}개 / {int(detail['500m내_정류장수'])}개 / {int(detail['1000m내_정류장수'])}개
    - **개선필요도:** {detail['개선필요도']}
    - **개선제안:** {detail['개선제안']}
    """
)

download_left, download_right = st.columns(2)
with download_left:
    st.download_button(
        "도서관별 분석결과 CSV 다운로드",
        ACCESS_CSV.read_bytes(),
        file_name="도서관별_접근성_분석결과.csv",
        mime="text/csv",
    )
with download_right:
    st.download_button(
        "개선우선순위 CSV 다운로드",
        PRIORITY_CSV.read_bytes(),
        file_name="도서관별_접근성_개선우선순위.csv",
        mime="text/csv",
    )
