from __future__ import annotations

import json
import math
import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from dotenv import load_dotenv


ROOT = Path(r"C:\PB_Data")
RAW_DIR = ROOT / "data" / "raw"
DATA_DIR = ROOT / "data"
CONFIG_DIR = ROOT / "config"
OUTPUT_DIR = ROOT / "output"

BUS_STOP_FILE = RAW_DIR / "전북_버스정류장_위치.xlsx"
JINAN_POP_FILE = RAW_DIR / "진안_202604_202604_연령별인구현황_월간.csv"
IMSIL_POP_FILE = RAW_DIR / "임실_202604_202604_연령별인구현황_월간.csv"

FACILITY_SCORE_FILE = CONFIG_DIR / "facility_scores.csv"
OUT_CANDIDATES = CONFIG_DIR / "manual_candidates.csv"
OUT_DEBUG = OUTPUT_DIR / "site_selection_candidate_scores.csv"
GEOCODE_CACHE = OUTPUT_DIR / "geocode_cache.json"

NAVER_GEOCODE_URL = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"

REGION_FILES = {
    "imsil": {
        "label": "임실군",
        "patterns": [
            "전북특별자치도 임실군_노인복지시설현황_20251203.csv",
            "전북특별자치도 임실군_본청 및 읍면사무소 현황_20251103.csv",
            "전북특별자치도 임실군_주민복지시설현황_20251103.csv",
            "전북특별자치도 임실군_어린이놀이시설현황_20251212.csv",
            "전북특별자치도 임실군_보건지소및진료소_20241004.csv",
            "전북특별자치도 임실군_문화공간_20250729.csv",
            "전북특별자치도 임실군_문화 및 집회시설_20251103.csv",
            "전북특별자치도 임실군_마을회관_20241010.csv",
            "전북특별자치도 임실군_터미널현황_20231106.csv",
            "전북특별자치도 임실군_학교현황_20231106.csv",
            "전북특별자치도 임실군_약국_20251208.csv",
        ],
    },
    "jinan": {
        "label": "진안군",
        "patterns": [
            "전북특별자치도 진안군_경로당 현황_20251202.csv",
            "전북특별자치도 진안군_다중이용시설 현황_20251202.csv",
            "전북특별자치도 진안군_의료기관 현황_20221202.csv",
            "전북특별자치도 진안군_정신건강센터 현황_20220817.csv",
        ],
    },
}


def norm(value: object) -> str:
    return unicodedata.normalize("NFC", str(value)).strip()


def compact(value: object) -> str:
    return re.sub(r"\s+", "", norm(value))


def read_csv_auto(path: Path) -> pd.DataFrame:
    last_error = None
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            df = pd.read_csv(path, encoding=enc)
            df.columns = [norm(c) for c in df.columns]
            return df
        except Exception as e:
            last_error = e
    raise RuntimeError(f"CSV 읽기 실패: {path} / {last_error}")


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return read_csv_auto(path)
    df = pd.read_excel(path)
    df.columns = [norm(c) for c in df.columns]
    return df


def pick_col(df: pd.DataFrame, keywords: list[str]) -> Optional[str]:
    cols = list(df.columns)
    for col in cols:
        c = compact(col)
        if any(compact(k) == c for k in keywords):
            return col
    for col in cols:
        c = compact(col)
        if any(compact(k) in c for k in keywords):
            return col
    return None


def to_num(value: object) -> float:
    if pd.isna(value):
        return 0.0
    text = str(value).replace(",", "").strip()
    val = pd.to_numeric(text, errors="coerce")
    return 0.0 if pd.isna(val) else float(val)


def load_env() -> None:
    load_dotenv(ROOT / ".env")


def naver_headers() -> dict[str, str]:
    client_id = os.getenv("NAVER_CLIENT_ID", "").strip()
    client_secret = os.getenv("NAVER_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET이 .env에 필요합니다.")
    return {
        "x-ncp-apigw-api-key-id": client_id,
        "x-ncp-apigw-api-key": client_secret,
    }


def load_geocode_cache() -> dict[str, list[float]]:
    if GEOCODE_CACHE.exists():
        try:
            return json.loads(GEOCODE_CACHE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_geocode_cache(cache: dict[str, list[float]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    GEOCODE_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def geocode(address: str, cache: dict[str, list[float]]) -> tuple[Optional[float], Optional[float]]:
    address = norm(address)
    if not address:
        return None, None
    if address in cache:
        return float(cache[address][0]), float(cache[address][1])

    try:
        r = requests.get(
            NAVER_GEOCODE_URL,
            headers=naver_headers(),
            params={"query": address},
            timeout=(10, 30),
        )
        time.sleep(float(os.getenv("NAVER_API_SLEEP_SECONDS", "0.5")))
        if r.status_code != 200:
            print(f"[geocode skip] {address} / HTTP {r.status_code}")
            return None, None

        data = r.json()
        addresses = data.get("addresses", [])
        if not addresses:
            print(f"[geocode empty] {address}")
            return None, None

        item = addresses[0]
        lat, lon = float(item["y"]), float(item["x"])
        cache[address] = [lat, lon]
        return lat, lon

    except Exception as e:
        print(f"[geocode error] {address} / {e}")
        return None, None


def infer_region_from_file(path: Path) -> Optional[str]:
    name = norm(path.name)
    if "진안군" in name:
        return "jinan"
    if "임실군" in name:
        return "imsil"
    return None


def infer_facility_type_from_file(path: Path) -> str:
    name = norm(path.name)
    if "읍면사무소" in name or "본청" in name:
        return "town_office"
    if "마을회관" in name or "경로당" in name or "노인복지" in name:
        return "village_center"
    if "학교" in name:
        return "school"
    if "보건" in name or "의료" in name or "정신건강" in name:
        return "health_center"
    if "터미널" in name:
        return "terminal"
    if "문화" in name or "다중이용" in name:
        return "culture_space"
    if "주민복지" in name:
        return "welfare_center"
    if "어린이놀이" in name:
        return "playground"
    if "약국" in name:
        return "pharmacy"
    return "default"


def extract_eupmyeon(text: object) -> str:
    s = norm(text)
    m = re.search(r"([가-힣]+(?:읍|면))", s)
    return m.group(1) if m else ""


def find_name_address_lat_lon(df: pd.DataFrame, region_label: str) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    name_col = pick_col(df, ["시설명", "명칭", "기관명", "학교명", "약국명", "시설", "업소명", "터미널명", "이름"])
    addr_col = pick_col(df, ["주소", "소재지", "소재지주소", "도로명주소", "지번주소", "위치"])
    lat_col = pick_col(df, ["위도", "lat", "latitude", "Y좌표", "GPSY"])
    lon_col = pick_col(df, ["경도", "lon", "longitude", "X좌표", "GPSX"])
    return name_col, addr_col, lat_col, lon_col


def load_bus_stops() -> pd.DataFrame:
    df = read_table(BUS_STOP_FILE)
    name_col = pick_col(df, ["정류장명"])
    city_col = pick_col(df, ["도시명", "시군구명", "관리도시명"])
    lat_col = pick_col(df, ["위도", "lat"])
    lon_col = pick_col(df, ["경도", "lon"])

    if not all([name_col, city_col, lat_col, lon_col]):
        raise RuntimeError(f"버스정류장 컬럼 확인 필요: {list(df.columns)}")

    out = pd.DataFrame({
        "정류장명": df[name_col].astype(str).map(norm),
        "도시명": df[city_col].astype(str).map(norm),
        "lat": pd.to_numeric(df[lat_col], errors="coerce"),
        "lon": pd.to_numeric(df[lon_col], errors="coerce"),
    }).dropna(subset=["lat", "lon"])

    out = out[out["lat"].between(33, 39) & out["lon"].between(124, 132)].copy()
    return out


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def access_metrics(lat: float, lon: float, bus_df: pd.DataFrame, region_label: str) -> tuple[float, int]:
    region_short = region_label.replace("군", "")
    stops = bus_df[bus_df["도시명"].astype(str).str.contains(region_short, na=False)].copy()
    if stops.empty:
        return 999.0, 0

    distances = [
        haversine_km(lat, lon, float(row.lat), float(row.lon))
        for row in stops.itertuples(index=False)
    ]
    nearest = min(distances) if distances else 999.0
    count_500m = sum(d <= 0.5 for d in distances)
    return nearest, count_500m


def load_population_scores() -> dict[tuple[str, str], float]:
    """
    읍면 단위까지 안정적으로 못 잡는 경우도 있으므로,
    읍면별 행을 찾으면 읍면 점수를 만들고,
    못 찾으면 지역 전체 평균 점수를 사용한다.
    """
    result: dict[tuple[str, str], float] = {}

    for region_key, path in {"jinan": JINAN_POP_FILE, "imsil": IMSIL_POP_FILE}.items():
        df = read_csv_auto(path)
        admin_col = pick_col(df, ["행정구역", "행정기관"])
        total_col = pick_col(df, ["총인구수", "계"])
        if not admin_col or not total_col:
            print(f"[population skip] {path.name}: 컬럼 확인 필요")
            continue

        age_cols = list(df.columns)

        def cols_contains(tokens: list[str]) -> list[str]:
            found = []
            for col in age_cols:
                c = compact(col)
                if any(t in c for t in tokens) and "남" not in c and "여" not in c:
                    found.append(col)
            return found

        elderly_cols = cols_contains(["60~69", "70~79", "80~89", "90~99", "100"])
        youth_cols = cols_contains(["10~19", "10세"])

        rows = []
        for _, row in df.iterrows():
            admin = norm(row[admin_col])
            total = to_num(row[total_col])
            if total <= 0:
                continue

            elderly = sum(to_num(row[c]) for c in elderly_cols)
            youth = sum(to_num(row[c]) for c in youth_cols)

            demand_raw = (elderly / total * 100) * 0.7 + (youth / total * 100) * 0.3
            eupmyeon = extract_eupmyeon(admin)
            rows.append((eupmyeon or "지역전체", demand_raw))

        if not rows:
            continue

        values = [v for _, v in rows]
        min_v, max_v = min(values), max(values)

        for eupmyeon, raw in rows:
            if max_v == min_v:
                score = 3.0
            else:
                score = 1 + (raw - min_v) / (max_v - min_v) * 4
            result[(region_key, eupmyeon)] = round(score, 3)

        # 지역 전체 fallback
        avg_raw = sum(values) / len(values)
        if max_v == min_v:
            avg_score = 3.0
        else:
            avg_score = 1 + (avg_raw - min_v) / (max_v - min_v) * 4
        result[(region_key, "지역전체")] = round(avg_score, 3)

    return result


def build_facility_rows() -> pd.DataFrame:
    rows = []
    cache = load_geocode_cache()

    for region_key, info in REGION_FILES.items():
        region_label = info["label"]

        for filename in info["patterns"]:
            path = RAW_DIR / filename
            if not path.exists():
                print(f"[missing] {filename}")
                continue

            facility_type = infer_facility_type_from_file(path)
            df = read_csv_auto(path)

            name_col, addr_col, lat_col, lon_col = find_name_address_lat_lon(df, region_label)

            if not name_col:
                print(f"[skip] {filename}: 시설명 컬럼 없음")
                continue

            for _, row in df.iterrows():
                name = norm(row.get(name_col, ""))
                if not name or name.lower() == "nan":
                    continue

                address = norm(row.get(addr_col, "")) if addr_col else ""
                if not address:
                    address = f"전북특별자치도 {region_label} {name}"

                lat = to_num(row.get(lat_col, 0)) if lat_col else 0.0
                lon = to_num(row.get(lon_col, 0)) if lon_col else 0.0

                if not (33 <= lat <= 39 and 124 <= lon <= 132):
                    lat, lon = geocode(address, cache)
                    if lat is None or lon is None:
                        continue

                rows.append({
                    "region_key": region_key,
                    "region_label": region_label,
                    "name": name,
                    "address": address,
                    "facility_type": facility_type,
                    "lat": float(lat),
                    "lon": float(lon),
                    "source_file": filename,
                    "eupmyeon": extract_eupmyeon(address) or extract_eupmyeon(name),
                })

    save_geocode_cache(cache)
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["dedup_key"] = df["region_key"] + "_" + df["name"].str.replace(" ", "", regex=False)
    df = df.drop_duplicates(subset=["dedup_key"]).drop(columns=["dedup_key"])
    return df


def add_bus_stop_candidates(bus_df: pd.DataFrame) -> pd.DataFrame:
    keywords = {
        "town_office": ["면사무소", "군청", "행정복지센터", "주민센터"],
        "village_center": ["마을회관", "경로당", "회관"],
        "school": ["초교", "초등학교", "중학교", "고등학교", "학교"],
        "health_center": ["보건", "의료원", "보건소", "진료소"],
        "terminal": ["터미널", "버스정류소"],
        "library": ["도서관"],
    }

    rows = []
    for region_key, region_label in [("jinan", "진안군"), ("imsil", "임실군")]:
        region_short = region_label.replace("군", "")
        region_stops = bus_df[bus_df["도시명"].astype(str).str.contains(region_short, na=False)].copy()

        for _, row in region_stops.iterrows():
            name = norm(row["정류장명"])
            facility_type = None
            for ftype, keys in keywords.items():
                if any(k in name for k in keys):
                    facility_type = ftype
                    break
            if not facility_type:
                continue

            rows.append({
                "region_key": region_key,
                "region_label": region_label,
                "name": name,
                "address": f"전북특별자치도 {region_label} {name}",
                "facility_type": facility_type,
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "source_file": "전북_버스정류장_위치",
                "eupmyeon": extract_eupmyeon(name),
            })

    return pd.DataFrame(rows)


def score_candidates(candidates: pd.DataFrame, bus_df: pd.DataFrame) -> pd.DataFrame:
    facility_scores = pd.read_csv(FACILITY_SCORE_FILE, encoding="utf-8-sig")
    score_map = facility_scores.set_index("facility_type").to_dict("index")
    default_score = score_map.get("default", {"public_score": 3.5, "operation_score": 3.0})

    demand_scores = load_population_scores()

    scored = []
    for _, row in candidates.iterrows():
        region_key = row["region_key"]
        region_label = row["region_label"]
        ftype = row["facility_type"]
        lat, lon = float(row["lat"]), float(row["lon"])

        nearest_km, nearby_count = access_metrics(lat, lon, bus_df, region_label)

        distance_score = max(0.0, min(1.0, 1 - nearest_km / 1.0))
        count_score = max(0.0, min(1.0, nearby_count / 5))
        access_score = 1 + (distance_score * 0.6 + count_score * 0.4) * 4

        eupmyeon = row.get("eupmyeon") or "지역전체"
        demand_score = demand_scores.get((region_key, eupmyeon), demand_scores.get((region_key, "지역전체"), 3.0))

        fs = score_map.get(ftype, default_score)
        public_score = float(fs.get("public_score", 3.5))
        operation_score = float(fs.get("operation_score", 3.0))

        final_score = (
            demand_score * 0.4
            + access_score * 0.3
            + public_score * 0.2
            + operation_score * 0.1
        )

        out = dict(row)
        out.update({
            "nearest_bus_stop_km": round(nearest_km, 3),
            "nearby_bus_stop_count_500m": int(nearby_count),
            "demand_score": round(demand_score, 3),
            "access_score": round(access_score, 3),
            "public_score": round(public_score, 3),
            "operation_score": round(operation_score, 3),
            "final_score": round(final_score, 3),
        })
        scored.append(out)

    return pd.DataFrame(scored).sort_values(["region_key", "final_score"], ascending=[True, False])


def main() -> None:
    load_env()
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    bus_df = load_bus_stops()
    facility_df = build_facility_rows()
    bus_candidate_df = add_bus_stop_candidates(bus_df)

    all_candidates = pd.concat([facility_df, bus_candidate_df], ignore_index=True)
    all_candidates = all_candidates.dropna(subset=["lat", "lon"])
    all_candidates["dedup_key"] = (
        all_candidates["region_key"].astype(str)
        + "_"
        + all_candidates["name"].astype(str).str.replace(" ", "", regex=False)
    )
    all_candidates = all_candidates.drop_duplicates(subset=["dedup_key"]).drop(columns=["dedup_key"])

    scored = score_candidates(all_candidates, bus_df)

    # optimizer 기존 StopCandidate 공식에 맞추기 위한 매핑:
    # demand_score = 수요
    # parking_score = 접근성
    # public_score = 공공성
    # access_score = 운영가능성
    optimizer_df = pd.DataFrame({
        "region_key": scored["region_key"],
        "name": scored["name"],
        "address": scored["address"],
        "facility_type": scored["facility_type"],
        "lat": scored["lat"],
        "lon": scored["lon"],
        "demand_score": scored["demand_score"],
        "parking_score": scored["access_score"],
        "public_score": scored["public_score"],
        "access_score": scored["operation_score"],
        "final_score": scored["final_score"],
        "nearest_bus_stop_km": scored["nearest_bus_stop_km"],
        "nearby_bus_stop_count_500m": scored["nearby_bus_stop_count_500m"],
        "source_file": scored["source_file"],
    })

    optimizer_df.to_csv(OUT_CANDIDATES, index=False, encoding="utf-8-sig")
    scored.to_csv(OUT_DEBUG, index=False, encoding="utf-8-sig")

    print("[완료] 후보지 점수화 파일 생성")
    print(" -", OUT_CANDIDATES)
    print(" -", OUT_DEBUG)
    print("\n지역별 후보지 수:")
    print(optimizer_df.groupby("region_key").size())
    print("\n상위 후보지:")
    print(optimizer_df[["region_key", "name", "facility_type", "final_score", "nearest_bus_stop_km", "nearby_bus_stop_count_500m"]].head(20))


if __name__ == "__main__":
    main()