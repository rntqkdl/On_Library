from __future__ import annotations

import math
import unicodedata
import warnings
from pathlib import Path
from typing import Iterable

import folium
import numpy as np
import pandas as pd

try:
    import matplotlib
    import matplotlib.pyplot as plt

    matplotlib.use("Agg")
    HAS_MATPLOTLIB = True
except Exception:  # pragma: no cover - local fallback for missing optional package
    plt = None
    HAS_MATPLOTLIB = False

try:
    from sklearn.neighbors import BallTree
except Exception:  # pragma: no cover - local fallback for missing optional package
    BallTree = None

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:  # pragma: no cover
    Image = None
    ImageDraw = None
    ImageFont = None

warnings.filterwarnings("ignore", category=UserWarning)

ROOT_DIR = Path(__file__).resolve().parents[1]
SEARCH_DIRS = [
    ROOT_DIR,
    ROOT_DIR / "raw_data",
    ROOT_DIR / "data",
    ROOT_DIR / "data" / "raw",
]

OUTPUT_DIR = ROOT_DIR / "output"
TABLE_DIR = OUTPUT_DIR / "tables"
MAP_DIR = OUTPUT_DIR / "maps"
FIGURE_DIR = OUTPUT_DIR / "figures"

CSV_ENCODINGS = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]
EARTH_RADIUS_M = 6371000.0

REGION_INFO = {
    "서울": {"area": "수도권(서울·경기)", "pop_keyword": "서울특별시"},
    "경기": {"area": "수도권(서울·경기)", "pop_keyword": "경기도"},
    "진안": {"area": "전북 농촌권(진안·임실)", "pop_keyword": "진안군"},
    "임실": {"area": "전북 농촌권(진안·임실)", "pop_keyword": "임실군"},
}

GRADE_COLORS = {
    "매우 높음": "#E76F51",
    "높음": "#F4A261",
    "보통": "#89D2FF",
    "낮음": "#2F80B7",
}


def norm_text(value: object) -> str:
    return unicodedata.normalize("NFC", str(value)).strip()


def compact_text(value: object) -> str:
    return norm_text(value).replace(" ", "").replace("_", "")


def ensure_dirs() -> None:
    for directory in [TABLE_DIR, MAP_DIR, FIGURE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def iter_candidate_files() -> Iterable[Path]:
    seen: set[Path] = set()
    for directory in SEARCH_DIRS:
        if not directory.exists():
            continue
        for path in directory.glob("*"):
            if path.is_file() and path not in seen:
                seen.add(path)
                yield path


def find_file(tokens: list[str], suffixes: tuple[str, ...]) -> Path:
    normalized_tokens = [norm_text(token) for token in tokens]
    matches: list[Path] = []
    for path in iter_candidate_files():
        name = norm_text(path.name)
        if path.suffix.lower() in suffixes and all(token in name for token in normalized_tokens):
            if "인천" in name:
                continue
            matches.append(path)
    if not matches:
        raise FileNotFoundError(f"파일을 찾지 못했습니다. tokens={tokens}, suffixes={suffixes}")
    return sorted(matches, key=lambda item: (len(str(item)), str(item)))[0]


def read_csv_auto(path: Path, **kwargs) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in CSV_ENCODINGS:
        try:
            df = pd.read_csv(path, encoding=encoding, **kwargs)
            df.columns = [norm_text(column) for column in df.columns]
            return df
        except Exception as exc:  # noqa: BLE001 - try known Korean encodings
            last_error = exc
    raise ValueError(f"CSV 파일을 읽지 못했습니다: {path} / {last_error}")


def read_excel_header_auto(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, header=None)
    header_idx = 0
    for idx in range(min(30, len(raw))):
        row = [norm_text(value) for value in raw.iloc[idx].tolist()]
        joined = " ".join(row)
        if ("위도" in row and "경도" in row) or ("60~69세" in joined and "70~79세" in joined):
            header_idx = idx
            break
    columns = [norm_text(value) for value in raw.iloc[header_idx].tolist()]
    df = raw.iloc[header_idx + 1 :].copy()
    df.columns = columns
    df = df.dropna(how="all")
    df.columns = [norm_text(column) for column in df.columns]
    return df


def read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return read_csv_auto(path)
    if suffix in {".xlsx", ".xls"}:
        return read_excel_header_auto(path)
    raise ValueError(f"지원하지 않는 파일 형식입니다: {path}")


def pick_column(df: pd.DataFrame, candidates: list[str], context: str) -> str:
    normalized_columns = {norm_text(column): column for column in df.columns}
    for candidate in candidates:
        if candidate in normalized_columns:
            return normalized_columns[candidate]
    compact_candidates = [compact_text(candidate) for candidate in candidates]
    for column in df.columns:
        compact = compact_text(column)
        if any(candidate in compact for candidate in compact_candidates):
            return column
    raise KeyError(f"{context}에서 컬럼을 찾지 못했습니다. candidates={candidates}, columns={list(df.columns)}")


def find_metric_column(df: pd.DataFrame, includes: list[str], excludes: list[str] | None = None) -> str:
    excludes = excludes or []
    for column in df.columns:
        compact = compact_text(column)
        if all(compact_text(value) in compact for value in includes) and not any(
            compact_text(value) in compact for value in excludes
        ):
            return column
    raise KeyError(f"지표 컬럼을 찾지 못했습니다. includes={includes}, excludes={excludes}")


def to_number(value: object) -> float:
    if pd.isna(value):
        return 0.0
    text = norm_text(value).replace(",", "")
    parsed = pd.to_numeric(text, errors="coerce")
    return 0.0 if pd.isna(parsed) else float(parsed)


def clean_lat_lon(df: pd.DataFrame, lat_col: str, lon_col: str) -> pd.DataFrame:
    df = df.copy()
    df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
    df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
    df = df.dropna(subset=[lat_col, lon_col])
    df = df[df[lat_col].between(33, 39) & df[lon_col].between(124, 132)]
    return df.reset_index(drop=True)


def standardize_library(df: pd.DataFrame, region: str) -> pd.DataFrame:
    name_col = pick_column(df, ["도서관명"], f"{region} 도서관")
    lat_col = pick_column(df, ["위도"], f"{region} 도서관")
    lon_col = pick_column(df, ["경도"], f"{region} 도서관")
    local_col = pick_column(df, ["시군구명", "행정구역", "지역명"], f"{region} 도서관")
    address_col = next((col for col in ["소재지도로명주소", "주소", "도로명주소"] if col in df.columns), None)

    df = clean_lat_lon(df, lat_col, lon_col)
    out = pd.DataFrame(
        {
            "비교권역": REGION_INFO[region]["area"],
            "분석지역": region,
            "도서관명": df[name_col].astype(str).map(norm_text),
            "시군구": df[local_col].astype(str).map(norm_text),
            "주소": df[address_col].astype(str).map(norm_text) if address_col else "",
            "도서관_위도": df[lat_col].astype(float),
            "도서관_경도": df[lon_col].astype(float),
        }
    )
    return out.drop_duplicates(subset=["도서관명", "도서관_위도", "도서관_경도"]).reset_index(drop=True)


def standardize_bus(df: pd.DataFrame, region: str) -> pd.DataFrame:
    name_col = pick_column(df, ["정류장명"], f"{region} 버스정류장")
    lat_col = pick_column(df, ["위도"], f"{region} 버스정류장")
    lon_col = pick_column(df, ["경도"], f"{region} 버스정류장")
    city_col = next((col for col in ["도시명", "관리도시명", "시군구명"] if col in df.columns), None)

    df = clean_lat_lon(df, lat_col, lon_col)
    out = pd.DataFrame(
        {
            "분석지역": region,
            "정류장명": df[name_col].astype(str).map(norm_text),
            "버스정류장_위도": df[lat_col].astype(float),
            "버스정류장_경도": df[lon_col].astype(float),
            "지역텍스트": df[city_col].astype(str).map(norm_text) if city_col else "",
        }
    )
    return out.drop_duplicates(subset=["정류장명", "버스정류장_위도", "버스정류장_경도"]).reset_index(drop=True)


def filter_text_contains(df: pd.DataFrame, keywords: list[str]) -> pd.DataFrame:
    text_cols = [
        column
        for column in df.columns
        if not pd.api.types.is_numeric_dtype(df[column])
    ]
    if not text_cols:
        return df.iloc[0:0].copy()
    combined = df[text_cols].astype(str).agg(" ".join, axis=1).map(norm_text)
    mask = np.logical_or.reduce([combined.str.contains(keyword, na=False, regex=False) for keyword in keywords])
    return df[mask].copy()


def load_libraries() -> pd.DataFrame:
    seoul = standardize_library(read_table(find_file(["서울특별시", "도서관"], (".csv",))), "서울")
    gyeonggi = standardize_library(read_table(find_file(["경기도", "도서관"], (".csv",))), "경기")

    jeonbuk_raw = read_table(find_file(["전북", "도서관", "위치"], (".xls", ".xlsx", ".csv")))
    rural_rows = filter_text_contains(jeonbuk_raw, ["진안", "임실"])
    rural_frames = []
    for region in ["진안", "임실"]:
        rural_frames.append(standardize_library(filter_text_contains(rural_rows, [region]), region))
    return pd.concat([seoul, gyeonggi, *rural_frames], ignore_index=True)


def load_bus_stops() -> pd.DataFrame:
    seoul = standardize_bus(read_table(find_file(["버스정류장", "서울"], (".csv",))), "서울")
    gyeonggi = standardize_bus(read_table(find_file(["버스정류장", "경기도"], (".csv",))), "경기")

    jeonbuk_raw = read_table(find_file(["전북", "버스정류장", "위치"], (".xlsx", ".xls", ".csv")))
    rural_rows = filter_text_contains(jeonbuk_raw, ["진안", "임실"])
    rural_frames = []
    for region in ["진안", "임실"]:
        rural_frames.append(standardize_bus(filter_text_contains(rural_rows, [region]), region))
    return pd.concat([seoul, gyeonggi, *rural_frames], ignore_index=True)


def read_population(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return read_csv_auto(path)
    return read_excel_header_auto(path)


def population_for_region(region: str) -> dict[str, float]:
    if region == "서울":
        path = find_file(["2025", "서울", "연령별", "인구수"], (".xlsx", ".xls", ".csv"))
    elif region == "경기":
        path = find_file(["2025", "경기", "연령별", "인구수"], (".csv", ".xlsx", ".xls"))
    elif region == "진안":
        path = find_file(["진안", "연령별인구현황"], (".csv", ".xlsx", ".xls"))
    else:
        path = find_file(["임실", "연령별인구현황"], (".csv", ".xlsx", ".xls"))

    df = read_population(path)
    admin_col = pick_column(df, ["행정구역", "행정기관"], f"{region} 인구")
    total_col = find_metric_column(df, ["총인구수"], ["남", "여"])
    age60_col = find_metric_column(df, ["60~69"], ["남", "여"])
    age70_col = find_metric_column(df, ["70~79"], ["남", "여"])

    keyword = REGION_INFO[region]["pop_keyword"]
    rows = df[df[admin_col].astype(str).map(norm_text).str.contains(keyword, na=False, regex=False)]
    if rows.empty:
        raise RuntimeError(f"{region} 인구 행을 찾지 못했습니다: {path}")
    row = rows.iloc[0]
    total = to_number(row[total_col])
    age_60_79 = to_number(row[age60_col]) + to_number(row[age70_col])
    ratio = round(age_60_79 / total * 100, 2) if total else 0.0
    return {"총인구수": total, "60_79세": age_60_79, "60_79세_비율": ratio}


def build_population_table() -> pd.DataFrame:
    rows = []
    for region in ["서울", "경기", "진안", "임실"]:
        rows.append({"분석지역": region, **population_for_region(region)})
    return pd.DataFrame(rows)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    return EARTH_RADIUS_M * 2 * math.asin(math.sqrt(a))


def analyze_region(libraries: pd.DataFrame, buses: pd.DataFrame, region: str) -> pd.DataFrame:
    libs = libraries[libraries["분석지역"] == region].copy()
    stops = buses[buses["분석지역"] == region].copy()
    if libs.empty:
        raise RuntimeError(f"{region} 도서관 데이터가 없습니다.")
    if stops.empty:
        raise RuntimeError(f"{region} 버스정류장 데이터가 없습니다.")

    stop_coords_rad = np.radians(stops[["버스정류장_위도", "버스정류장_경도"]].to_numpy())
    lib_coords_rad = np.radians(libs[["도서관_위도", "도서관_경도"]].to_numpy())

    if BallTree is not None:
        tree = BallTree(stop_coords_rad, metric="haversine")
        distances_rad, indices = tree.query(lib_coords_rad, k=1)
        libs["최근접정류장거리_m"] = np.round(distances_rad[:, 0] * EARTH_RADIUS_M, 1)
        nearest = stops.iloc[indices[:, 0]].reset_index(drop=True)
        libs["최근접정류장명"] = nearest["정류장명"].to_numpy()
        libs["최근접정류장_위도"] = nearest["버스정류장_위도"].to_numpy()
        libs["최근접정류장_경도"] = nearest["버스정류장_경도"].to_numpy()

        for radius_m in [300, 500, 1000]:
            counts = tree.query_radius(lib_coords_rad, r=radius_m / EARTH_RADIUS_M, count_only=True)
            libs[f"{radius_m}m내_정류장수"] = counts.astype(int)
        return libs

    nearest_names: list[str] = []
    nearest_distances: list[float] = []
    nearest_lats: list[float] = []
    nearest_lons: list[float] = []
    radius_counts = {300: [], 500: [], 1000: []}

    stop_lat_rad = stop_coords_rad[:, 0]
    stop_lon_rad = stop_coords_rad[:, 1]
    for lib_lat_rad, lib_lon_rad in lib_coords_rad:
        dlat = stop_lat_rad - lib_lat_rad
        dlon = stop_lon_rad - lib_lon_rad
        a = np.sin(dlat / 2) ** 2 + np.cos(lib_lat_rad) * np.cos(stop_lat_rad) * np.sin(dlon / 2) ** 2
        distances_m = EARTH_RADIUS_M * 2 * np.arcsin(np.sqrt(a))
        nearest_idx = int(np.argmin(distances_m))
        nearest_row = stops.iloc[nearest_idx]
        nearest_names.append(str(nearest_row["정류장명"]))
        nearest_distances.append(round(float(distances_m[nearest_idx]), 1))
        nearest_lats.append(float(nearest_row["버스정류장_위도"]))
        nearest_lons.append(float(nearest_row["버스정류장_경도"]))
        for radius_m in [300, 500, 1000]:
            radius_counts[radius_m].append(int((distances_m <= radius_m).sum()))

    libs["최근접정류장거리_m"] = nearest_distances
    libs["최근접정류장명"] = nearest_names
    libs["최근접정류장_위도"] = nearest_lats
    libs["최근접정류장_경도"] = nearest_lons
    for radius_m in [300, 500, 1000]:
        libs[f"{radius_m}m내_정류장수"] = radius_counts[radius_m]
    return libs


def minmax_score(series: pd.Series, inverse: bool = False) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").fillna(0).astype(float)
    min_value = values.min()
    max_value = values.max()
    if max_value == min_value:
        return pd.Series(np.zeros(len(values)), index=series.index)
    scaled = (values - min_value) / (max_value - min_value) * 100
    return 100 - scaled if inverse else scaled


def add_scores(access_df: pd.DataFrame, bus_df: pd.DataFrame) -> pd.DataFrame:
    df = access_df.copy()
    bus_counts = bus_df.groupby("분석지역").size().rename("지역_정류장수")
    df = df.merge(bus_counts, on="분석지역", how="left")
    df["인구1만명당_정류장수"] = df["지역_정류장수"] / df["총인구수"].replace(0, np.nan) * 10000
    df["인구1만명당_정류장수"] = df["인구1만명당_정류장수"].fillna(0)

    df["거리_취약점수"] = minmax_score(df["최근접정류장거리_m"])
    df["500m정류장_부족점수"] = minmax_score(df["500m내_정류장수"], inverse=True)
    df["1000m정류장_부족점수"] = minmax_score(df["1000m내_정류장수"], inverse=True)
    df["고령층_수요점수"] = minmax_score(df["60_79세_비율"])
    df["인구대비정류장_부족점수"] = minmax_score(df["인구1만명당_정류장수"], inverse=True)

    df["접근성_취약점수"] = (
        df["거리_취약점수"] * 0.35
        + df["500m정류장_부족점수"] * 0.30
        + df["1000m정류장_부족점수"] * 0.15
        + df["고령층_수요점수"] * 0.15
        + df["인구대비정류장_부족점수"] * 0.05
    ).clip(0, 100).round(1)
    df["개선필요도"] = df["접근성_취약점수"].apply(grade_score)
    df["개선제안"] = df.apply(make_recommendation, axis=1)
    return df


def grade_score(score: float) -> str:
    if score >= 80:
        return "매우 높음"
    if score >= 60:
        return "높음"
    if score >= 40:
        return "보통"
    return "낮음"


def make_recommendation(row: pd.Series) -> str:
    messages: list[str] = []
    if row["최근접정류장거리_m"] > 300:
        messages.append("도서관 인근 정류장 신설 또는 노선 경유 조정 검토 필요")
    if row["500m내_정류장수"] <= 5:
        messages.append("도서관 주변 대중교통 선택지 부족으로 순환버스 또는 마을버스 연계 검토 필요")
    if row["60_79세_비율"] >= 35:
        messages.append("고령층 이용 수요를 고려한 셔틀, 예약형 교통, 정류장 접근 보행환경 개선 필요")
    return " / ".join(messages) if messages else "현재 접근성은 상대적으로 양호하나 지속 모니터링 필요"


def make_summary(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    rows = []
    for key, group in df.groupby(group_col):
        pop_unique = group[["분석지역", "총인구수", "60_79세"]].drop_duplicates("분석지역")
        total_pop = pop_unique["총인구수"].sum()
        age_pop = pop_unique["60_79세"].sum()
        rows.append(
            {
                group_col: key,
                "도서관수": int(len(group)),
                "평균_최근접거리_m": round(group["최근접정류장거리_m"].mean(), 1),
                "중앙값_최근접거리_m": round(group["최근접정류장거리_m"].median(), 1),
                "최대_최근접거리_m": round(group["최근접정류장거리_m"].max(), 1),
                "평균_300m내_정류장수": round(group["300m내_정류장수"].mean(), 1),
                "평균_500m내_정류장수": round(group["500m내_정류장수"].mean(), 1),
                "평균_1000m내_정류장수": round(group["1000m내_정류장수"].mean(), 1),
                "평균_접근성_취약점수": round(group["접근성_취약점수"].mean(), 1),
                "매우높음_도서관수": int((group["개선필요도"] == "매우 높음").sum()),
                "높음_도서관수": int((group["개선필요도"] == "높음").sum()),
                "총인구수": int(total_pop),
                "60_79세": int(age_pop),
                "60_79세_비율": round(age_pop / total_pop * 100, 2) if total_pop else 0,
            }
        )
    return pd.DataFrame(rows)


def save_tables(access_df: pd.DataFrame) -> None:
    access_columns = [
        "비교권역",
        "분석지역",
        "도서관명",
        "도서관_위도",
        "도서관_경도",
        "최근접정류장명",
        "최근접정류장거리_m",
        "300m내_정류장수",
        "500m내_정류장수",
        "1000m내_정류장수",
        "총인구수",
        "60_79세",
        "60_79세_비율",
        "거리_취약점수",
        "500m정류장_부족점수",
        "1000m정류장_부족점수",
        "고령층_수요점수",
        "인구대비정류장_부족점수",
        "접근성_취약점수",
        "개선필요도",
        "개선제안",
        "최근접정류장_위도",
        "최근접정류장_경도",
        "인구1만명당_정류장수",
    ]
    access_df[access_columns].to_csv(TABLE_DIR / "도서관별_접근성_분석결과.csv", index=False, encoding="utf-8-sig")
    make_summary(access_df, "분석지역").to_csv(TABLE_DIR / "지역별_접근성_요약.csv", index=False, encoding="utf-8-sig")
    make_summary(access_df, "비교권역").to_csv(TABLE_DIR / "권역별_접근성_요약.csv", index=False, encoding="utf-8-sig")
    access_df[access_columns].sort_values("접근성_취약점수", ascending=False).to_csv(
        TABLE_DIR / "도서관별_접근성_개선우선순위.csv",
        index=False,
        encoding="utf-8-sig",
    )


def set_korean_font() -> None:
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False


def annotate_bars(ax, fmt: str = "{:.1f}") -> None:
    for container in ax.containers:
        labels = []
        for value in container.datavalues:
            labels.append(fmt.format(value))
        ax.bar_label(container, labels=labels, padding=3, fontsize=9)


def finish_figure(fig, ax, note: str, path: Path) -> None:
    ax.text(0, -0.22, note, transform=ax.transAxes, fontsize=9, color="#555555", va="top")
    ax.margins(y=0.18)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def get_pil_font(size: int = 24):
    if ImageFont is None:
        return None
    font_path = Path(r"C:\Windows\Fonts\malgun.ttf")
    if font_path.exists():
        return ImageFont.truetype(str(font_path), size=size)
    return ImageFont.load_default()


def save_simple_png(title: str, rows: list[tuple[str, float]], note: str, path: Path, horizontal: bool = False) -> None:
    if Image is None or ImageDraw is None:
        raise RuntimeError("matplotlib 또는 pillow가 필요합니다. `pip install -r requirements.txt`를 실행하세요.")
    width, height = 1600, 950
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = get_pil_font(42)
    label_font = get_pil_font(24)
    small_font = get_pil_font(20)
    draw.text((70, 45), title, fill="#174A7C", font=title_font)
    if not rows:
        image.save(path, dpi=(300, 300))
        return

    values = [max(float(value), 0.0) for _, value in rows]
    max_value = max(values) if max(values) > 0 else 1
    plot_left, plot_top, plot_right, plot_bottom = 220, 150, 1480, 760

    if horizontal:
        bar_gap = 12
        bar_height = max(26, int((plot_bottom - plot_top) / len(rows) - bar_gap))
        for idx, (label, value) in enumerate(rows):
            y = plot_top + idx * (bar_height + bar_gap)
            bar_width = int((plot_right - plot_left) * float(value) / max_value)
            draw.text((40, y + 2), label[:12], fill="#222222", font=small_font)
            draw.rectangle([plot_left, y, plot_left + bar_width, y + bar_height], fill="#E76F51")
            draw.text((plot_left + bar_width + 12, y + 2), f"{value:.1f}", fill="#222222", font=small_font)
    else:
        bar_gap = 28
        bar_width = max(45, int((plot_right - plot_left) / len(rows) - bar_gap))
        baseline = plot_bottom
        for idx, (label, value) in enumerate(rows):
            x = plot_left + idx * (bar_width + bar_gap)
            bar_height = int((plot_bottom - plot_top) * float(value) / max_value)
            color = ["#89D2FF", "#2F80B7", "#174A7C", "#F4A261", "#E76F51"][idx % 5]
            draw.rectangle([x, baseline - bar_height, x + bar_width, baseline], fill=color)
            draw.text((x, baseline - bar_height - 34), f"{value:.1f}", fill="#222222", font=small_font)
            draw.text((x, baseline + 14), label[:10], fill="#222222", font=small_font)

    draw.line([plot_left, plot_bottom, plot_right, plot_bottom], fill="#555555", width=2)
    draw.text((70, 835), note, fill="#555555", font=label_font)
    image.save(path, dpi=(300, 300))


def save_scatter_png(title: str, points: list[tuple[str, float, float]], note: str, path: Path) -> None:
    if Image is None or ImageDraw is None:
        raise RuntimeError("matplotlib 또는 pillow가 필요합니다. `pip install -r requirements.txt`를 실행하세요.")
    width, height = 1600, 950
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = get_pil_font(42)
    label_font = get_pil_font(24)
    small_font = get_pil_font(20)
    draw.text((70, 45), title, fill="#174A7C", font=title_font)
    if not points:
        image.save(path, dpi=(300, 300))
        return
    xs = [point[1] for point in points]
    ys = [point[2] for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    if min_x == max_x:
        max_x += 1
    if min_y == max_y:
        max_y += 1
    left, top, right, bottom = 170, 150, 1480, 760
    draw.rectangle([left, top, right, bottom], outline="#cccccc", width=2)
    for label, x_value, y_value in points:
        x = left + int((x_value - min_x) / (max_x - min_x) * (right - left))
        y = bottom - int((y_value - min_y) / (max_y - min_y) * (bottom - top))
        draw.ellipse([x - 9, y - 9, x + 9, y + 9], fill="#F4A261", outline="#174A7C", width=2)
        draw.text((x + 12, y - 10), label[:10], fill="#222222", font=small_font)
    draw.text((70, 835), note, fill="#555555", font=label_font)
    image.save(path, dpi=(300, 300))


def save_figures_pil(access_df: pd.DataFrame) -> None:
    region_summary = make_summary(access_df, "분석지역")
    area_summary = make_summary(access_df, "비교권역")
    save_simple_png(
        "권역별 최근접 버스정류장 평균거리",
        list(zip(area_summary["비교권역"], area_summary["평균_최근접거리_m"])),
        "해석: 평균 거리가 길수록 도서관 접근성이 취약할 가능성이 큽니다.",
        FIGURE_DIR / "그래프1_권역별_최근접정류장_평균거리.png",
    )
    save_simple_png(
        "권역별 도서관 주변 정류장 수",
        list(zip(area_summary["비교권역"], area_summary["평균_500m내_정류장수"])),
        "해석: 500m 내 정류장 수가 적을수록 대중교통 선택지가 부족합니다.",
        FIGURE_DIR / "그래프2_권역별_도서관주변_정류장수.png",
    )
    save_simple_png(
        "지역별 60~79세 인구 비율",
        list(zip(region_summary["분석지역"], region_summary["60_79세_비율"])),
        "해석: 고령층 비율이 높을수록 도서관 접근성 개선 수요가 커질 수 있습니다.",
        FIGURE_DIR / "그래프3_지역별_60_79세_비율.png",
    )
    save_simple_png(
        "지역별 도서관 500m 내 평균 정류장 수",
        list(zip(region_summary["분석지역"], region_summary["평균_500m내_정류장수"])),
        "해석: 500m 내 정류장 수는 도보 접근 가능한 대중교통 선택지를 보여줍니다.",
        FIGURE_DIR / "그래프4_지역별_500m내_정류장수.png",
    )
    save_scatter_png(
        "고령층 비율과 정류장 접근성 비교",
        [(row["분석지역"], row["평균_500m내_정류장수"], row["60_79세_비율"]) for _, row in region_summary.iterrows()],
        "해석: 왼쪽 위에 가까울수록 고령층 수요 대비 정류장 접근성이 취약합니다.",
        FIGURE_DIR / "그래프5_고령층비율_정류장접근성_비교.png",
    )
    top10 = access_df.sort_values("접근성_취약점수", ascending=False).head(10)
    save_simple_png(
        "접근성 취약점수 TOP10",
        list(zip(top10["도서관명"], top10["접근성_취약점수"])),
        "해석: 점수가 높을수록 개선 우선순위가 높습니다.",
        FIGURE_DIR / "그래프6_접근성취약점수_TOP10.png",
        horizontal=True,
    )
    save_scatter_png(
        "정류장 수와 접근성 취약점수",
        [(row["도서관명"], row["500m내_정류장수"], row["접근성_취약점수"]) for _, row in access_df.iterrows()],
        "해석: 왼쪽 위 도서관은 주변 정류장이 적고 취약점수가 높습니다.",
        FIGURE_DIR / "그래프7_취약점수_정류장수_산점도.png",
    )


def save_figures(access_df: pd.DataFrame) -> None:
    if not HAS_MATPLOTLIB:
        save_figures_pil(access_df)
        return

    set_korean_font()
    region_summary = make_summary(access_df, "분석지역")
    area_summary = make_summary(access_df, "비교권역")

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(area_summary["비교권역"], area_summary["평균_최근접거리_m"], color=["#89D2FF", "#F4A261"])
    ax.set_title("권역별 최근접 버스정류장 평균거리")
    ax.set_ylabel("평균 거리(m)")
    annotate_bars(ax)
    finish_figure(fig, ax, "해석: 평균 거리가 길수록 도서관 접근성이 취약할 가능성이 큽니다.", FIGURE_DIR / "그래프1_권역별_최근접정류장_평균거리.png")

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(area_summary))
    width = 0.24
    ax.bar(x - width, area_summary["평균_300m내_정류장수"], width, label="300m", color="#89D2FF")
    ax.bar(x, area_summary["평균_500m내_정류장수"], width, label="500m", color="#2F80B7")
    ax.bar(x + width, area_summary["평균_1000m내_정류장수"], width, label="1000m", color="#174A7C")
    ax.set_xticks(x, area_summary["비교권역"])
    ax.set_title("권역별 도서관 주변 정류장 수")
    ax.set_ylabel("평균 정류장 수")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
    annotate_bars(ax)
    finish_figure(fig, ax, "해석: 반경별 정류장 수가 적을수록 대중교통 선택지가 부족합니다.", FIGURE_DIR / "그래프2_권역별_도서관주변_정류장수.png")

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(region_summary["분석지역"], region_summary["60_79세_비율"], color="#2F80B7")
    ax.set_title("지역별 60~79세 인구 비율")
    ax.set_ylabel("비율(%)")
    annotate_bars(ax)
    finish_figure(fig, ax, "해석: 고령층 비율이 높을수록 도서관 접근성 개선 수요가 커질 수 있습니다.", FIGURE_DIR / "그래프3_지역별_60_79세_비율.png")

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(region_summary["분석지역"], region_summary["평균_500m내_정류장수"], color="#89D2FF")
    ax.set_title("지역별 도서관 500m 내 평균 정류장 수")
    ax.set_ylabel("평균 정류장 수")
    annotate_bars(ax)
    finish_figure(fig, ax, "해석: 500m 내 정류장 수는 도보 접근 가능한 대중교통 선택지를 보여줍니다.", FIGURE_DIR / "그래프4_지역별_500m내_정류장수.png")

    fig, ax = plt.subplots(figsize=(8, 5))
    sizes = (region_summary["평균_접근성_취약점수"] + 20) * 8
    ax.scatter(
        region_summary["평균_500m내_정류장수"],
        region_summary["60_79세_비율"],
        s=sizes,
        color="#F4A261",
        edgecolor="#174A7C",
    )
    for _, row in region_summary.iterrows():
        ax.annotate(row["분석지역"], (row["평균_500m내_정류장수"], row["60_79세_비율"]), xytext=(6, 4), textcoords="offset points")
    ax.set_title("고령층 비율과 정류장 접근성 비교")
    ax.set_xlabel("500m 내 평균 정류장 수")
    ax.set_ylabel("60~79세 비율(%)")
    finish_figure(fig, ax, "해석: 왼쪽 위에 가까울수록 고령층 수요 대비 정류장 접근성이 취약합니다.", FIGURE_DIR / "그래프5_고령층비율_정류장접근성_비교.png")

    top10 = access_df.sort_values("접근성_취약점수", ascending=False).head(10).sort_values("접근성_취약점수")
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(top10["도서관명"], top10["접근성_취약점수"], color="#E76F51")
    ax.set_title("접근성 취약점수 TOP10")
    ax.set_xlabel("취약점수")
    for idx, value in enumerate(top10["접근성_취약점수"]):
        ax.text(value + 1, idx, f"{value:.1f}", va="center", fontsize=9)
    finish_figure(fig, ax, "해석: 점수가 높을수록 개선 우선순위가 높습니다.", FIGURE_DIR / "그래프6_접근성취약점수_TOP10.png")

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = access_df["개선필요도"].map(GRADE_COLORS)
    ax.scatter(access_df["500m내_정류장수"], access_df["접근성_취약점수"], c=colors, alpha=0.75, edgecolor="#333333", linewidth=0.3)
    ax.set_title("정류장 수와 접근성 취약점수")
    ax.set_xlabel("500m 내 정류장 수")
    ax.set_ylabel("접근성 취약점수")
    finish_figure(fig, ax, "해석: 왼쪽 위 도서관은 주변 정류장이 적고 취약점수가 높습니다.", FIGURE_DIR / "그래프7_취약점수_정류장수_산점도.png")


def popup_html(row: pd.Series) -> str:
    return (
        f"<b>{row['도서관명']}</b><br>"
        f"분석지역: {row['분석지역']}<br>"
        f"최근접 정류장 거리: {row['최근접정류장거리_m']:.1f}m<br>"
        f"500m 내 정류장 수: {int(row['500m내_정류장수'])}개<br>"
        f"60~79세 비율: {row['60_79세_비율']:.2f}%<br>"
        f"접근성 취약점수: {row['접근성_취약점수']:.1f}<br>"
        f"개선필요도: {row['개선필요도']}<br>"
        f"개선제안: {row['개선제안']}"
    )


def add_bus_points(map_obj: folium.Map, bus_df: pd.DataFrame, name: str, color: str = "#174A7C") -> None:
    layer = folium.FeatureGroup(name=name, show=False)
    for row in bus_df.itertuples(index=False):
        folium.CircleMarker(
            location=[row.버스정류장_위도, row.버스정류장_경도],
            radius=1.4,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.25,
            opacity=0.25,
            tooltip=getattr(row, "정류장명"),
        ).add_to(layer)
    layer.add_to(map_obj)


def save_maps(access_df: pd.DataFrame, bus_df: pd.DataFrame) -> None:
    center = [access_df["도서관_위도"].mean(), access_df["도서관_경도"].mean()]
    m = folium.Map(location=center, zoom_start=8, tiles="OpenStreetMap")
    add_bus_points(m, bus_df, "버스정류장")

    library_layer = folium.FeatureGroup(name="도서관", show=True)
    for _, row in access_df.iterrows():
        color = GRADE_COLORS.get(row["개선필요도"], "#89D2FF")
        folium.CircleMarker(
            location=[row["도서관_위도"], row["도서관_경도"]],
            radius=7,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            popup=folium.Popup(popup_html(row), max_width=420),
            tooltip=f"{row['도서관명']} ({row['개선필요도']})",
        ).add_to(library_layer)
    library_layer.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    m.save(MAP_DIR / "전체_도서관_접근성_지도.html")

    rural = access_df[access_df["분석지역"].isin(["진안", "임실"])].copy()
    rural_bus = bus_df[bus_df["분석지역"].isin(["진안", "임실"])].copy()
    center = [rural["도서관_위도"].mean(), rural["도서관_경도"].mean()]
    detail = folium.Map(location=center, zoom_start=10, tiles="OpenStreetMap")
    add_bus_points(detail, rural_bus, "진안·임실 버스정류장", "#2F80B7")

    for _, row in rural.iterrows():
        color = GRADE_COLORS.get(row["개선필요도"], "#89D2FF")
        folium.Marker(
            location=[row["도서관_위도"], row["도서관_경도"]],
            popup=folium.Popup(popup_html(row), max_width=420),
            tooltip=f"{row['도서관명']} ({row['개선필요도']})",
            icon=folium.Icon(color="red" if row["개선필요도"] in ["매우 높음", "높음"] else "blue", icon="book"),
        ).add_to(detail)
        folium.Circle([row["도서관_위도"], row["도서관_경도"]], radius=300, color=color, weight=2, fill=False).add_to(detail)
        folium.Circle([row["도서관_위도"], row["도서관_경도"]], radius=500, color=color, weight=2, fill=False, dash_array="6,6").add_to(detail)
        folium.PolyLine(
            [[row["도서관_위도"], row["도서관_경도"]], [row["최근접정류장_위도"], row["최근접정류장_경도"]]],
            color="#E76F51",
            weight=3,
            tooltip=f"최근접 정류장: {row['최근접정류장명']} ({row['최근접정류장거리_m']:.1f}m)",
        ).add_to(detail)
    folium.LayerControl(collapsed=False).add_to(detail)
    detail.save(MAP_DIR / "전북_진안_임실_도서관_접근성_지도.html")


def build_accessibility() -> pd.DataFrame:
    ensure_dirs()
    libraries = load_libraries()
    buses = load_bus_stops()
    population = build_population_table()

    frames = [analyze_region(libraries, buses, region) for region in ["서울", "경기", "진안", "임실"]]
    access_df = pd.concat(frames, ignore_index=True)
    access_df = access_df.merge(population, on="분석지역", how="left")
    access_df = add_scores(access_df, buses)
    access_df = access_df.sort_values(["접근성_취약점수", "최근접정류장거리_m"], ascending=False).reset_index(drop=True)

    save_tables(access_df)
    save_figures(access_df)
    save_maps(access_df, buses)
    return access_df


def main() -> None:
    access_df = build_accessibility()
    print(f"도서관 접근성 분석 완료: {len(access_df)}개 도서관")
    print(f"CSV: {TABLE_DIR}")
    print(f"지도: {MAP_DIR}")
    print(f"그래프: {FIGURE_DIR}")


if __name__ == "__main__":
    main()
