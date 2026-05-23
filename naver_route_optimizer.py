from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import folium
import pandas as pd
import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout as RequestsTimeout


try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional convenience dependency
    load_dotenv = None


ENV_FILES = (Path.cwd() / ".env", Path(__file__).resolve().parent / ".env")
GOOGLE_MAPS_API_KEY_NAMES = (
    "GOOGLE_MAPS_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_ROUTE_API_KEY",
    "GOOGLE_ROUTES_API_KEY",
    "GOOGLE_MAPS_PLATFORM_API_KEY",
)
NAVER_CLIENT_ID_NAMES = (
    "NAVER_CLIENT_ID",
    "NAVER_MAPS_CLIENT_ID",
    "NAVER_API_KEY_ID",
    "NCP_APIGW_API_KEY_ID",
)
NAVER_CLIENT_SECRET_NAMES = (
    "NAVER_CLIENT_SECRET",
    "NAVER_MAPS_CLIENT_SECRET",
    "NAVER_API_KEY",
    "NCP_APIGW_API_KEY",
)


def load_env_files() -> None:
    for env_file in ENV_FILES:
        if load_dotenv:
            load_dotenv(env_file)
            continue
        if not env_file.exists():
            continue
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key and key not in os.environ:
                os.environ[key] = value.strip().strip('"').strip("'")


def get_google_maps_api_key(explicit_key: Optional[str] = None) -> Tuple[Optional[str], str]:
    if explicit_key:
        return explicit_key, "--api-key"
    for key_name in GOOGLE_MAPS_API_KEY_NAMES:
        value = os.getenv(key_name)
        if value:
            return value, key_name
    return None, ""


def get_first_env(names: Sequence[str]) -> Tuple[Optional[str], str]:
    for name in names:
        value = os.getenv(name)
        if value:
            return value, name
    return None, ""


load_env_files()


GOOGLE_MAPS_API_KEY, GOOGLE_MAPS_API_KEY_SOURCE = get_google_maps_api_key()
NAVER_CLIENT_ID, NAVER_CLIENT_ID_SOURCE = get_first_env(NAVER_CLIENT_ID_NAMES)
NAVER_CLIENT_SECRET, NAVER_CLIENT_SECRET_SOURCE = get_first_env(NAVER_CLIENT_SECRET_NAMES)
GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
ROUTE_MATRIX_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
COMPUTE_ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
NAVER_GEOCODE_URL = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
NAVER_DIRECTION_URL = "https://maps.apigw.ntruss.com/map-direction/v1/driving"
GOOGLE_TRAVEL_MODE = os.getenv("GOOGLE_TRAVEL_MODE", "DRIVE").upper()
GOOGLE_MATRIX_MODE = GOOGLE_TRAVEL_MODE
GOOGLE_EFFECTIVE_TRAVEL_MODE = GOOGLE_TRAVEL_MODE
NAVER_DIRECTION_OPTION = os.getenv("NAVER_DIRECTION_OPTION", "trafast")
NAVER_API_SLEEP_SECONDS = float(os.getenv("NAVER_API_SLEEP_SECONDS", "0.5"))
NAVER_CONNECT_TIMEOUT = float(os.getenv("NAVER_CONNECT_TIMEOUT", "30"))
NAVER_READ_TIMEOUT = float(os.getenv("NAVER_READ_TIMEOUT", "90"))
NAVER_TIMEOUT = (NAVER_CONNECT_TIMEOUT, NAVER_READ_TIMEOUT)
NAVER_MAX_RETRIES = 4

STOP_MINUTES_PER_PLACE = 30
DEFAULT_BUSES_PER_REGION = 3
DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"
LIBRARY_CSV = "전북_도서관 위치.csv"
BUS_STOP_CSV = "전북_버스정류장_위치.csv"
NEARBY_BUS_STOP_RADIUS_KM = 0.5

ROUTE_COLORS = [
    "#e60000",
    "#0037ff",
    "#008a00",
    "#8b0099",
    "#ff9900",
    "#8b0000",
]


@dataclass(frozen=True)
class StopCandidate:
    name: str
    address: str
    facility_type: str
    demand_score: float
    parking_score: float
    public_score: float
    access_score: float
    lat: Optional[float] = None
    lon: Optional[float] = None

    def suitability_score(self) -> float:
        return (
            self.demand_score * 0.4
            + self.parking_score * 0.3
            + self.public_score * 0.2
            + self.access_score * 0.1
        )


@dataclass(frozen=True)
class Location:
    name: str
    address: str
    facility_type: str
    suitability_score: float
    lat: float
    lon: float
    nearest_bus_stop: str = ""
    nearest_bus_stop_km: Optional[float] = None
    nearby_bus_stop_count: int = 0


@dataclass
class LegInfo:
    distance_km: float
    duration_min: float
    path: List[Tuple[float, float]]
    source: str = "unknown"


@dataclass
class RouteGroup:
    name: str
    region: str
    region_key: str
    color: str
    hub: Location
    stops: List[Location]
    route: List[Location]
    path_segments: List[List[Tuple[float, float]]]
    details: List[Dict[str, object]]
    total_drive_km: float
    total_drive_min: float
    total_operation_min: float


class RouteLookupError(RuntimeError):
    pass


class NaverAuthenticationError(RuntimeError):
    pass


NaverRouteCacheKey = Tuple[float, float, float, float, str]
NAVER_ROUTE_CACHE: Dict[NaverRouteCacheKey, LegInfo] = {}
NAVER_ROUTE_CACHE_PATH: Optional[Path] = None


def naver_route_cache_key(start: Location, goal: Location) -> NaverRouteCacheKey:
    return (
        round(start.lat, 6),
        round(start.lon, 6),
        round(goal.lat, 6),
        round(goal.lon, 6),
        NAVER_DIRECTION_OPTION,
    )


def naver_route_cache_key_to_string(key: NaverRouteCacheKey) -> str:
    return "|".join(str(part) for part in key)


def naver_route_cache_key_from_string(value: str) -> Optional[NaverRouteCacheKey]:
    parts = value.split("|")
    if len(parts) != 5:
        return None
    try:
        return (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]), parts[4])
    except ValueError:
        return None


def leg_to_cache_payload(leg: LegInfo) -> Dict[str, object]:
    return {
        "distance_km": leg.distance_km,
        "duration_min": leg.duration_min,
        "path": leg.path,
        "source": leg.source,
    }


def leg_from_cache_payload(payload: Dict[str, object]) -> LegInfo:
    return LegInfo(
        distance_km=float(payload["distance_km"]),
        duration_min=float(payload["duration_min"]),
        path=[(float(lat), float(lon)) for lat, lon in payload.get("path", [])],
        source=str(payload.get("source", "naver")),
    )


def load_naver_route_cache(output_dir: Path) -> None:
    global NAVER_ROUTE_CACHE_PATH
    NAVER_ROUTE_CACHE_PATH = output_dir / "naver_route_cache.json"
    if not NAVER_ROUTE_CACHE_PATH.exists():
        return
    try:
        raw_cache = json.loads(NAVER_ROUTE_CACHE_PATH.read_text(encoding="utf-8"))
        for raw_key, payload in raw_cache.items():
            key = naver_route_cache_key_from_string(str(raw_key))
            if key and isinstance(payload, dict):
                NAVER_ROUTE_CACHE[key] = leg_from_cache_payload(payload)
        print(f"[Naver cache] loaded {len(NAVER_ROUTE_CACHE)} legs from {NAVER_ROUTE_CACHE_PATH}", file=sys.stderr)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"[Naver cache] cache load skipped: {exc}", file=sys.stderr)


def save_naver_route_cache() -> None:
    if NAVER_ROUTE_CACHE_PATH is None:
        return
    NAVER_ROUTE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        naver_route_cache_key_to_string(key): leg_to_cache_payload(leg)
        for key, leg in NAVER_ROUTE_CACHE.items()
    }
    NAVER_ROUTE_CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


REGION_HUBS = {
    "jinan": {
        "label": "진안군",
        "route_prefix": "진안",
        "hub_library_name": "전북특별자치도교육청진안도서관",
    },
    "imsil": {
        "label": "임실군",
        "route_prefix": "임실",
        "hub_library_name": "임실군립도서관",
    },
}


JINAN_HUB = StopCandidate(
    name="진안군립도서관",
    address="전북특별자치도 진안군 진안읍 중앙로 66 진안군립도서관",
    facility_type="hub_library",
    demand_score=0,
    parking_score=0,
    public_score=0,
    access_score=0,
    lat=35.7906,
    lon=127.4247,
)

IMSIL_HUB = StopCandidate(
    name="임실군립도서관",
    address="전북특별자치도 임실군 임실읍 봉황로 75 임실군립도서관",
    facility_type="hub_library",
    demand_score=0,
    parking_score=0,
    public_score=0,
    access_score=0,
    lat=35.6130,
    lon=127.2792,
)


JINAN_CANDIDATES = [
    StopCandidate("백운면사무소", "전북특별자치도 진안군 백운면사무소", "town_office", 4, 4, 5, 4, 35.6885, 127.3985),
    StopCandidate("성수면사무소", "전북특별자치도 진안군 성수면사무소", "town_office", 4, 4, 5, 4, 35.7081, 127.3237),
    StopCandidate("포동마을회관", "전북특별자치도 진안군 성수면 포동마을회관", "village_center", 3, 3, 4, 3, 35.7207, 127.3470),
    StopCandidate("마령면사무소", "전북특별자치도 진안군 마령면사무소", "town_office", 4, 4, 5, 4, 35.7355, 127.3707),
    StopCandidate("장성동마을회관", "전북특별자치도 진안군 장성동마을회관", "village_center", 3, 3, 4, 3, 35.7650, 127.3820),
    StopCandidate("부귀면사무소", "전북특별자치도 진안군 부귀면사무소", "town_office", 4, 4, 5, 4, 35.8370, 127.3605),
    StopCandidate("정천면사무소", "전북특별자치도 진안군 정천면사무소", "town_office", 4, 4, 5, 4, 35.8744, 127.4266),
    StopCandidate("주천면사무소", "전북특별자치도 진안군 주천면사무소", "town_office", 4, 4, 5, 4, 35.9751, 127.4273),
    StopCandidate("안천면사무소", "전북특별자치도 진안군 안천면사무소", "town_office", 3, 4, 5, 3, 35.8940, 127.5442),
]

IMSIL_CANDIDATES = [
    StopCandidate("오수면사무소", "전북특별자치도 임실군 오수면사무소", "town_office", 4, 4, 5, 4, 35.5394, 127.3281),
    StopCandidate("관촌면사무소", "전북특별자치도 임실군 관촌면사무소", "town_office", 4, 4, 5, 4, 35.6727, 127.2703),
    StopCandidate("강진면사무소", "전북특별자치도 임실군 강진면사무소", "town_office", 3, 4, 5, 3, 35.5306, 127.1601),
    StopCandidate("운암면사무소", "전북특별자치도 임실군 운암면사무소", "town_office", 3, 4, 5, 3, 35.6268, 127.1563),
    StopCandidate("신평면사무소", "전북특별자치도 임실군 신평면사무소", "town_office", 3, 4, 5, 3, 35.6664, 127.2215),
    StopCandidate("성수면사무소", "전북특별자치도 임실군 성수면사무소", "town_office", 3, 4, 5, 3, 35.6281, 127.3333),
    StopCandidate("지사면사무소", "전북특별자치도 임실군 지사면사무소", "town_office", 3, 4, 5, 3, 35.5630, 127.3566),
    StopCandidate("삼계면사무소", "전북특별자치도 임실군 삼계면사무소", "town_office", 3, 4, 5, 3, 35.5034, 127.2762),
    StopCandidate("덕치면사무소", "전북특별자치도 임실군 덕치면사무소", "town_office", 3, 4, 5, 3, 35.5059, 127.1530),
]


REGIONS = {
    "jinan": {
        "label": REGION_HUBS["jinan"]["label"],
        "route_prefix": REGION_HUBS["jinan"]["route_prefix"],
        "hub_library_name": REGION_HUBS["jinan"]["hub_library_name"],
        "hub": JINAN_HUB,
        "candidates": JINAN_CANDIDATES,
    },
    "imsil": {
        "label": REGION_HUBS["imsil"]["label"],
        "route_prefix": REGION_HUBS["imsil"]["route_prefix"],
        "hub_library_name": REGION_HUBS["imsil"]["hub_library_name"],
        "hub": IMSIL_HUB,
        "candidates": IMSIL_CANDIDATES,
    },
}


def read_csv_with_bom(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def load_library_data(data_dir: Path) -> pd.DataFrame:
    path = data_dir / LIBRARY_CSV
    if not path.exists():
        return pd.DataFrame()
    return read_csv_with_bom(path)


def load_bus_stop_data(data_dir: Path) -> pd.DataFrame:
    path = data_dir / BUS_STOP_CSV
    if not path.exists():
        return pd.DataFrame()

    df = read_csv_with_bom(path)
    df = df.rename(columns={"위도": "lat", "경도": "lon"})
    df = df.dropna(subset=["정류장명", "lat", "lon", "도시명"])
    df = df[~df["정류장명"].astype(str).str.contains("미정차", na=False)].copy()
    return df


def region_bus_stops(bus_df: pd.DataFrame, region_label: str) -> pd.DataFrame:
    if bus_df.empty:
        return pd.DataFrame()
    return bus_df[bus_df["도시명"].astype(str).str.contains(region_label, na=False)].copy()


def require_column(df: pd.DataFrame, column_name: str, context: str) -> str:
    if column_name not in df.columns:
        available = ", ".join(str(column) for column in df.columns)
        raise RuntimeError(f"{context}에 '{column_name}' 컬럼이 없습니다. 현재 컬럼: {available}")
    return column_name


def choose_hub_from_library(
    library_df: pd.DataFrame,
    region_label: str,
    hub_library_name: str,
) -> StopCandidate:
    if library_df.empty:
        raise RuntimeError(f"{region_label} 허브 도서관 '{hub_library_name}'을 {LIBRARY_CSV}에서 찾지 못했습니다.")

    name_col = require_column(library_df, "도서관명", LIBRARY_CSV)
    region_col = require_column(library_df, "시군구명", LIBRARY_CSV)
    lat_col = require_column(library_df, "위도", LIBRARY_CSV)
    lon_col = require_column(library_df, "경도", LIBRARY_CSV)

    region_df = library_df[library_df[region_col].astype(str).str.contains(region_label, na=False)].copy()
    search_df = region_df if not region_df.empty else library_df

    exact = search_df[search_df[name_col].astype(str).str.strip() == hub_library_name]
    if exact.empty:
        preferred = search_df[search_df[name_col].astype(str).str.contains(hub_library_name, na=False, regex=False)]
    else:
        preferred = exact

    if preferred.empty:
        raise RuntimeError(f"{region_label} 허브 도서관 '{hub_library_name}'을 {LIBRARY_CSV}에서 찾지 못했습니다.")

    row = preferred.iloc[0]
    address = str(row["주소"]) if "주소" in library_df.columns and pd.notna(row["주소"]) else f"전북특별자치도 {region_label} {hub_library_name}"
    lat = float(row[lat_col]) if pd.notna(row[lat_col]) else None
    lon = float(row[lon_col]) if pd.notna(row[lon_col]) else None
    return StopCandidate(
        name=str(row[name_col]),
        address=address,
        facility_type="hub_library",
        demand_score=0,
        parking_score=0,
        public_score=0,
        access_score=0,
        lat=lat,
        lon=lon,
    )


def infer_facility_type(stop_name: str) -> Optional[str]:
    name = str(stop_name)
    if "면사무소" in name or "군청" in name:
        return "town_office"
    if "마을회관" in name or "경로당" in name:
        return "village_center"
    if "초교" in name or "초등학교" in name or "중학교" in name or "고등학교" in name or "학교" in name:
        return "school"
    if "도서관" in name:
        return "library"
    if "보건" in name or "의료원" in name:
        return "health_center"
    if "터미널" in name or "버스정류소" in name:
        return "terminal"
    return None


def candidate_scores_for_facility(facility_type: str) -> Tuple[float, float, float, float]:
    if facility_type == "town_office":
        return 4.2, 4.0, 5.0, 4.4
    if facility_type == "village_center":
        return 3.6, 3.4, 4.5, 3.7
    if facility_type == "school":
        return 4.0, 3.4, 4.3, 3.9
    if facility_type == "health_center":
        return 4.1, 3.5, 4.6, 4.0
    if facility_type == "terminal":
        return 4.3, 4.2, 4.4, 5.0
    if facility_type == "library":
        return 3.8, 3.4, 4.7, 3.8
    return 3.0, 3.0, 3.5, 3.0


def bus_stop_candidates(
    bus_df: pd.DataFrame,
    region_label: str,
    limit: int,
) -> List[StopCandidate]:
    region_df = region_bus_stops(bus_df, region_label)
    if region_df.empty or limit <= 0:
        return []

    rows = []
    for _, row in region_df.iterrows():
        name = str(row["정류장명"])
        facility_type = infer_facility_type(name)
        if not facility_type:
            continue
        rows.append(
            {
                "name": name,
                "facility_type": facility_type,
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
            }
        )

    if not rows:
        return []

    dedup = pd.DataFrame(rows).groupby(["name", "facility_type"], as_index=False).agg({"lat": "mean", "lon": "mean"})
    candidates = []
    for _, row in dedup.iterrows():
        demand, parking, public, access = candidate_scores_for_facility(str(row["facility_type"]))
        candidates.append(
            StopCandidate(
                name=str(row["name"]),
                address=f"전북특별자치도 {region_label}군 {row['name']}",
                facility_type=str(row["facility_type"]),
                demand_score=demand,
                parking_score=parking,
                public_score=public,
                access_score=access,
                lat=float(row["lat"]),
                lon=float(row["lon"]),
            )
        )

    candidates.sort(key=lambda candidate: candidate.suitability_score(), reverse=True)
    return candidates[:limit]


def merge_candidates(primary: Sequence[StopCandidate], extra: Sequence[StopCandidate]) -> List[StopCandidate]:
    merged: List[StopCandidate] = []
    seen_names = set()
    for candidate in [*primary, *extra]:
        key = candidate.name.replace(" ", "")
        if key in seen_names:
            continue
        seen_names.add(key)
        merged.append(candidate)
    return merged


def nearest_bus_stop(location: Location, bus_stops: pd.DataFrame) -> Tuple[str, Optional[float], int]:
    if bus_stops.empty:
        return "", None, 0

    nearest_name = ""
    nearest_distance: Optional[float] = None
    nearby_count = 0

    for _, stop in bus_stops.iterrows():
        distance = haversine_km(location.lat, location.lon, float(stop["lat"]), float(stop["lon"]))
        if nearest_distance is None or distance < nearest_distance:
            nearest_distance = distance
            nearest_name = str(stop["정류장명"])
        if distance <= NEARBY_BUS_STOP_RADIUS_KM:
            nearby_count += 1

    return nearest_name, nearest_distance, nearby_count


def geocode_google(address: str) -> Tuple[float, float]:
    if not GOOGLE_MAPS_API_KEY:
        raise EnvironmentError("Google Geocoding API를 사용하려면 GOOGLE_MAPS_API_KEY를 설정하세요.")
    params = {
        "address": address,
        "key": GOOGLE_MAPS_API_KEY,
        "language": "ko",
        "region": "kr",
    }
    response = requests.get(GEOCODING_URL, params=params, timeout=10)
    raise_for_google_response(response, "Google Geocoding")
    data = response.json()
    if data.get("status") != "OK" or not data.get("results"):
        raise RuntimeError(f"Google Geocoding failed: {address} / {data.get('status')}")
    location = data["results"][0]["geometry"]["location"]
    return float(location["lat"]), float(location["lng"])


def naver_headers() -> Dict[str, str]:
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        accepted_id_names = ", ".join(NAVER_CLIENT_ID_NAMES)
        accepted_secret_names = ", ".join(NAVER_CLIENT_SECRET_NAMES)
        raise EnvironmentError(
            "네이버 지도 API를 사용하려면 Client ID와 Client Secret/API Key를 설정하세요. "
            f"ID 후보: {accepted_id_names} / Secret 후보: {accepted_secret_names}"
        )
    return {
        "x-ncp-apigw-api-key-id": NAVER_CLIENT_ID,
        "x-ncp-apigw-api-key": NAVER_CLIENT_SECRET,
    }


def raise_for_naver_response(response: requests.Response, context: str) -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        body = response.text[:1000]
        raise RuntimeError(f"{context} failed: HTTP {response.status_code} / {body}") from exc


def naver_retry_wait_seconds(attempt: int, response: Optional[requests.Response] = None) -> float:
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(float(retry_after), 0.0)
            except ValueError:
                pass
    return min(2 ** (attempt - 1), 12)


def naver_get_with_retry(
    url: str,
    *,
    headers: Dict[str, str],
    params: Dict[str, object],
    context: str,
) -> Optional[requests.Response]:
    last_error: Optional[BaseException] = None

    for attempt in range(1, NAVER_MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=NAVER_TIMEOUT)
            if NAVER_API_SLEEP_SECONDS:
                time.sleep(NAVER_API_SLEEP_SECONDS)

            if response.status_code in (401, 403):
                body = response.text[:1000]
                raise NaverAuthenticationError(
                    f"[Naver auth] {context}: HTTP {response.status_code}. "
                    f"Naver API Key ID/Key and Maps API permissions must be checked. {body}"
                )

            if response.status_code == 429 or 500 <= response.status_code < 600:
                last_error = RuntimeError(
                    f"{context}: retryable HTTP {response.status_code} / {response.text[:300]}"
                )
                if attempt < NAVER_MAX_RETRIES:
                    wait_seconds = naver_retry_wait_seconds(attempt, response)
                    print(
                        f"[Naver retry] {context} attempt {attempt + 1}/{NAVER_MAX_RETRIES} "
                        f"after HTTP {response.status_code}; wait {wait_seconds:.1f}s",
                        file=sys.stderr,
                    )
                    time.sleep(wait_seconds)
                    continue
                break

            return response
        except (RequestsTimeout, RequestsConnectionError) as exc:
            last_error = exc
            if attempt < NAVER_MAX_RETRIES:
                wait_seconds = naver_retry_wait_seconds(attempt)
                print(
                    f"[Naver retry] {context} attempt {attempt + 1}/{NAVER_MAX_RETRIES} "
                    f"after {exc.__class__.__name__}: {exc}; wait {wait_seconds:.1f}s",
                    file=sys.stderr,
                )
                time.sleep(wait_seconds)
                continue
            break

    print(
        f"[Naver retry] {context} failed after {NAVER_MAX_RETRIES} attempts: {last_error}",
        file=sys.stderr,
    )
    return None


def geocode_naver(address: str) -> Tuple[float, float]:
    response = naver_get_with_retry(
        NAVER_GEOCODE_URL,
        headers=naver_headers(),
        params={"query": address},
        context=f"Naver Geocoding address={address}",
    )
    if response is None:
        raise RuntimeError(f"Naver Geocoding failed after retry: {address}")
    raise_for_naver_response(response, "Naver Geocoding")
    addresses = response.json().get("addresses", [])
    if not addresses:
        raise RuntimeError(f"Naver Geocoding failed: {address}")
    item = addresses[0]
    return float(item["y"]), float(item["x"])


def candidate_to_location(
    candidate: StopCandidate,
    provider: str,
    bus_stops: Optional[pd.DataFrame] = None,
) -> Location:
    if candidate.lat is not None and candidate.lon is not None:
        lat, lon = candidate.lat, candidate.lon
    elif provider == "google":
        lat, lon = geocode_google(candidate.address)
    elif provider == "naver":
        lat, lon = geocode_naver(candidate.address)
    else:
        raise RuntimeError(f"No offline coordinates for {candidate.name}")

    base_location = Location(
        name=candidate.name,
        address=candidate.address,
        facility_type=candidate.facility_type,
        suitability_score=round(candidate.suitability_score(), 2),
        lat=lat,
        lon=lon,
    )
    if bus_stops is None or bus_stops.empty:
        return base_location

    nearest_name, nearest_distance, nearby_count = nearest_bus_stop(base_location, bus_stops)
    return Location(
        name=base_location.name,
        address=base_location.address,
        facility_type=base_location.facility_type,
        suitability_score=base_location.suitability_score,
        lat=base_location.lat,
        lon=base_location.lon,
        nearest_bus_stop=nearest_name,
        nearest_bus_stop_km=round(nearest_distance, 3) if nearest_distance is not None else None,
        nearby_bus_stop_count=nearby_count,
    )



def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return radius_km * 2 * math.asin(math.sqrt(a))


def estimate_drive_from_haversine(start: Location, goal: Location, source: str = "haversine") -> LegInfo:
    straight_km = haversine_km(start.lat, start.lon, goal.lat, goal.lon)
    distance_km = straight_km * 1.28
    duration_min = distance_km / 35 * 60
    return LegInfo(
        distance_km=distance_km,
        duration_min=duration_min,
        path=[(start.lat, start.lon), (goal.lat, goal.lon)],
        source=source,
    )


def google_waypoint(location: Location) -> Dict[str, object]:
    return {
        "waypoint": {
            "location": {
                "latLng": {
                    "latitude": location.lat,
                    "longitude": location.lon,
                }
            }
        }
    }


def parse_google_duration_seconds(value: str) -> float:
    if not value.endswith("s"):
        raise RuntimeError(f"Unknown Google duration format: {value}")
    return float(value[:-1])


def raise_for_google_response(response: requests.Response, context: str) -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        body = response.text[:1000]
        raise RuntimeError(f"{context} failed: HTTP {response.status_code} / {body}") from exc


def google_matrix_body(locations: Sequence[Location], travel_mode: str) -> Dict[str, object]:
    body: Dict[str, object] = {
        "origins": [google_waypoint(location) for location in locations],
        "destinations": [google_waypoint(location) for location in locations],
        "travelMode": travel_mode,
        "languageCode": "ko-KR",
        "units": "METRIC",
    }
    if travel_mode in {"DRIVE", "TWO_WHEELER"}:
        body["routingPreference"] = "TRAFFIC_AWARE"
    return body


def parse_google_route_matrix(
    locations: Sequence[Location],
    response_data: Sequence[Dict[str, object]],
) -> Tuple[Dict[Tuple[int, int], LegInfo], int, int]:
    matrix: Dict[Tuple[int, int], LegInfo] = {}
    fallback_legs: List[Tuple[int, int, str]] = []
    google_leg_count = 0

    for element in response_data:
        origin_idx = int(element["originIndex"])
        destination_idx = int(element["destinationIndex"])
        if origin_idx == destination_idx:
            continue
        status = element.get("status")
        if isinstance(status, dict) and status.get("code"):
            reason = str(status)
            matrix[(origin_idx, destination_idx)] = estimate_drive_from_haversine(
                locations[origin_idx],
                locations[destination_idx],
                source="haversine_fallback",
            )
            fallback_legs.append((origin_idx, destination_idx, reason))
            continue
        if element.get("condition") and element["condition"] != "ROUTE_EXISTS":
            reason = str(element["condition"])
            matrix[(origin_idx, destination_idx)] = estimate_drive_from_haversine(
                locations[origin_idx],
                locations[destination_idx],
                source="haversine_fallback",
            )
            fallback_legs.append((origin_idx, destination_idx, reason))
            continue
        if "distanceMeters" not in element or "duration" not in element:
            reason = f"incomplete response: {element}"
            matrix[(origin_idx, destination_idx)] = estimate_drive_from_haversine(
                locations[origin_idx],
                locations[destination_idx],
                source="haversine_fallback",
            )
            fallback_legs.append((origin_idx, destination_idx, reason))
            continue
        matrix[(origin_idx, destination_idx)] = LegInfo(
            distance_km=float(element["distanceMeters"]) / 1000,
            duration_min=parse_google_duration_seconds(str(element["duration"])) / 60,
            path=[],
            source="google",
        )
        google_leg_count += 1

    for origin_idx, origin in enumerate(locations):
        for destination_idx, destination in enumerate(locations):
            if origin_idx == destination_idx or (origin_idx, destination_idx) in matrix:
                continue
            matrix[(origin_idx, destination_idx)] = estimate_drive_from_haversine(
                origin,
                destination,
                source="haversine_fallback",
            )
            fallback_legs.append((origin_idx, destination_idx, "missing matrix element"))

    if fallback_legs:
        examples = ", ".join(
            f"{locations[start].name}->{locations[goal].name}({reason})"
            for start, goal, reason in fallback_legs[:3]
        )
        suffix = " ..." if len(fallback_legs) > 3 else ""
        print(
            f"[provider] Google Matrix에서 {len(fallback_legs)}개 구간을 찾지 못해 해당 구간만 "
            f"Haversine 추정값을 사용했습니다: {examples}{suffix}",
            file=sys.stderr,
        )

    return matrix, google_leg_count, len(fallback_legs)


def request_google_route_matrix(
    locations: Sequence[Location],
    travel_mode: str,
) -> Tuple[Dict[Tuple[int, int], LegInfo], int, int]:
    if not GOOGLE_MAPS_API_KEY:
        raise EnvironmentError("Google Routes API를 사용하려면 GOOGLE_MAPS_API_KEY를 설정하세요.")
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "originIndex,destinationIndex,duration,distanceMeters,status,condition",
    }
    body = google_matrix_body(locations, travel_mode)
    response = requests.post(ROUTE_MATRIX_URL, headers=headers, json=body, timeout=30)
    raise_for_google_response(response, "Google Route Matrix")
    return parse_google_route_matrix(locations, response.json())


def build_google_route_matrix(locations: Sequence[Location]) -> Dict[Tuple[int, int], LegInfo]:
    global GOOGLE_EFFECTIVE_TRAVEL_MODE, GOOGLE_MATRIX_MODE

    matrix, google_leg_count, _ = request_google_route_matrix(locations, GOOGLE_MATRIX_MODE)
    GOOGLE_EFFECTIVE_TRAVEL_MODE = GOOGLE_MATRIX_MODE
    if google_leg_count == 0 and GOOGLE_MATRIX_MODE == "DRIVE":
        print(
            "[provider] Google DRIVE 경로가 없어 이후 Matrix 계산은 TRANSIT 모드를 사용합니다.",
            file=sys.stderr,
        )
        matrix, google_leg_count, _ = request_google_route_matrix(locations, "TRANSIT")
        if google_leg_count:
            GOOGLE_MATRIX_MODE = "TRANSIT"
            GOOGLE_EFFECTIVE_TRAVEL_MODE = "TRANSIT"

    return matrix


def decode_polyline(encoded: str) -> List[Tuple[float, float]]:
    index = 0
    lat = 0
    lng = 0
    coordinates: List[Tuple[float, float]] = []

    while index < len(encoded):
        result = 0
        shift = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        delta_lat = ~(result >> 1) if result & 1 else result >> 1
        lat += delta_lat

        result = 0
        shift = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        delta_lng = ~(result >> 1) if result & 1 else result >> 1
        lng += delta_lng

        coordinates.append((lat / 1e5, lng / 1e5))

    return coordinates


def get_google_route_polyline(start: Location, goal: Location) -> List[Tuple[float, float]]:
    if not GOOGLE_MAPS_API_KEY:
        raise EnvironmentError("Google Routes API를 사용하려면 GOOGLE_MAPS_API_KEY를 설정하세요.")
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "routes.polyline.encodedPolyline",
    }
    body = {
        "origin": google_waypoint(start)["waypoint"],
        "destination": google_waypoint(goal)["waypoint"],
        "travelMode": GOOGLE_EFFECTIVE_TRAVEL_MODE,
        "languageCode": "ko-KR",
        "units": "METRIC",
    }
    if GOOGLE_EFFECTIVE_TRAVEL_MODE in {"DRIVE", "TWO_WHEELER"}:
        body["routingPreference"] = "TRAFFIC_AWARE"
    response = requests.post(COMPUTE_ROUTES_URL, headers=headers, json=body, timeout=30)
    raise_for_google_response(response, "Google Compute Routes")
    routes = response.json().get("routes", [])
    if not routes:
        return [(start.lat, start.lon), (goal.lat, goal.lon)]
    return decode_polyline(routes[0]["polyline"]["encodedPolyline"])


def get_naver_drive_info(start: Location, goal: Location) -> LegInfo:
    cache_key = naver_route_cache_key(start, goal)
    cached = NAVER_ROUTE_CACHE.get(cache_key)
    if cached is not None:
        print(
            f"[Naver cache] {start.name} -> {goal.name}: "
            f"{cached.distance_km:.2f}km / {cached.duration_min:.1f}min",
            file=sys.stderr,
        )
        return cached

    params = {
        "start": f"{start.lon},{start.lat}",
        "goal": f"{goal.lon},{goal.lat}",
        "option": NAVER_DIRECTION_OPTION,
    }
    context = f"{start.name} -> {goal.name}"

    try:
        response = naver_get_with_retry(
            NAVER_DIRECTION_URL,
            headers=naver_headers(),
            params=params,
            context=context,
        )
        if response is None:
            raise RouteLookupError(f"Naver Directions failed after retry: {context}")
        raise_for_naver_response(response, "Naver Directions")
        data = response.json()
        if data.get("code") not in (0, "0", None):
            raise RouteLookupError(f"Naver Directions failed: {context}: {data}")
        routes = data.get("route", {}).get(NAVER_DIRECTION_OPTION) or data.get("route", {}).get("trafast")
        if not routes:
            raise RouteLookupError(f"Naver Directions returned no route: {context}: {data}")
        route = routes[0]
        summary = route["summary"]
        leg = LegInfo(
            distance_km=float(summary["distance"]) / 1000,
            duration_min=float(summary["duration"]) / 1000 / 60,
            path=[(float(lat), float(lon)) for lon, lat in route.get("path", [])],
            source="naver",
        )
        NAVER_ROUTE_CACHE[cache_key] = leg
        print(
            f"[Naver] success: {leg.distance_km:.2f}km / {leg.duration_min:.1f}min",
            file=sys.stderr,
        )
        return leg
    except NaverAuthenticationError:
        raise
    except (RouteLookupError, RuntimeError, ValueError, KeyError) as exc:
        leg = estimate_drive_from_haversine(start, goal, source="haversine_fallback")
        NAVER_ROUTE_CACHE[cache_key] = leg
        print(
            f"[Naver fallback] {start.name} -> {goal.name}: "
            f"Naver API failed; Haversine estimate used: {exc}",
            file=sys.stderr,
        )
        return leg


def build_naver_route_matrix(locations: Sequence[Location]) -> Dict[Tuple[int, int], LegInfo]:
    matrix: Dict[Tuple[int, int], LegInfo] = {}
    total = len(locations) * (len(locations) - 1)
    progress = 0
    for start_idx, start in enumerate(locations):
        for goal_idx, goal in enumerate(locations):
            if start_idx == goal_idx:
                continue
            progress += 1
            print(
                f"[Naver] matrix {progress}/{total}: {start.name} -> {goal.name}",
                file=sys.stderr,
            )
            matrix[(start_idx, goal_idx)] = get_naver_drive_info(start, goal)
    return matrix


def build_matrix(locations: Sequence[Location], provider: str) -> Dict[Tuple[int, int], LegInfo]:
    if provider == "google":
        return build_google_route_matrix(locations)
    if provider == "naver":
        return build_naver_route_matrix(locations)

    matrix: Dict[Tuple[int, int], LegInfo] = {}
    for start_idx, start in enumerate(locations):
        for goal_idx, goal in enumerate(locations):
            if start_idx != goal_idx:
                matrix[(start_idx, goal_idx)] = estimate_drive_from_haversine(start, goal)
    return matrix


def route_duration(route_indices: Sequence[int], matrix: Dict[Tuple[int, int], LegInfo]) -> float:
    return sum(
        matrix[(start_idx, goal_idx)].duration_min
        for start_idx, goal_idx in zip(route_indices, route_indices[1:])
    )


def optimize_route_exact(locations: Sequence[Location], matrix: Dict[Tuple[int, int], LegInfo]) -> List[int]:
    if len(locations) <= 1:
        return [0]

    hub_idx = 0
    candidate_indices = range(1, len(locations))
    best_route: Optional[List[int]] = None
    best_minutes = float("inf")

    for order in itertools.permutations(candidate_indices):
        route = [hub_idx, *order, hub_idx]
        minutes = route_duration(route, matrix)
        if minutes < best_minutes:
            best_route = route
            best_minutes = minutes

    return best_route or [hub_idx, hub_idx]


def split_candidates_for_buses(candidates: Sequence[Location], buses: int) -> List[List[Location]]:
    if buses <= 1:
        return [list(candidates)]

    sorted_candidates = sorted(candidates, key=lambda loc: math.atan2(loc.lat, loc.lon))
    groups = [[] for _ in range(buses)]
    for index, candidate in enumerate(sorted_candidates):
        groups[index % buses].append(candidate)
    return [group for group in groups if group]


def build_route_details(
    route_indices: Sequence[int],
    locations: Sequence[Location],
    matrix: Dict[Tuple[int, int], LegInfo],
) -> List[Dict[str, object]]:
    details = []
    cumulative_operation_min = 0.0
    for order, (start_idx, goal_idx) in enumerate(zip(route_indices, route_indices[1:]), start=1):
        start = locations[start_idx]
        goal = locations[goal_idx]
        leg = matrix[(start_idx, goal_idx)]
        stop_min = 0 if goal_idx == 0 else STOP_MINUTES_PER_PLACE
        drive_min = round(leg.duration_min, 1)
        cumulative_operation_min += drive_min + stop_min
        path = [[round(lat, 7), round(lon, 7)] for lat, lon in leg.path]
        details.append(
            {
                "order": order,
                "from_name": start.name,
                "to_name": goal.name,
                "to_facility_type": goal.facility_type,
                "to_suitability_score": goal.suitability_score,
                "to_nearest_bus_stop": goal.nearest_bus_stop,
                "to_nearest_bus_stop_km": goal.nearest_bus_stop_km,
                "to_nearby_bus_stop_count_500m": goal.nearby_bus_stop_count,
                "haversine_km": round(haversine_km(start.lat, start.lon, goal.lat, goal.lon), 2),
                "drive_km": round(leg.distance_km, 2),
                "drive_min": drive_min,
                "stop_min": stop_min,
                "cumulative_operation_min": round(cumulative_operation_min, 1),
                "source": leg.source,
                "route_path_json": json.dumps(path, ensure_ascii=False, separators=(",", ":")),
            }
        )
    return details


def build_route_group(
    name: str,
    region: str,
    region_key: str,
    color: str,
    hub: Location,
    stops: Sequence[Location],
    provider: str,
) -> RouteGroup:
    locations = [hub, *stops]
    matrix = build_matrix(locations, provider)
    route_indices = optimize_route_exact(locations, matrix)
    route = [locations[index] for index in route_indices]
    details = build_route_details(route_indices, locations, matrix)

    total_drive_km = sum(row["drive_km"] for row in details)
    total_drive_min = sum(row["drive_min"] for row in details)
    total_operation_min = total_drive_min + len(stops) * STOP_MINUTES_PER_PLACE

    if provider == "google":
        for start_idx, goal_idx in zip(route_indices, route_indices[1:]):
            leg = matrix[(start_idx, goal_idx)]
            if not leg.path:
                leg.path = get_google_route_polyline(locations[start_idx], locations[goal_idx])

    path_segments = [
        matrix[(start_idx, goal_idx)].path
        for start_idx, goal_idx in zip(route_indices, route_indices[1:])
    ]

    return RouteGroup(
        name=name,
        region=region,
        region_key=region_key,
        color=color,
        hub=hub,
        stops=list(stops),
        route=route,
        path_segments=path_segments,
        details=details,
        total_drive_km=float(total_drive_km),
        total_drive_min=float(total_drive_min),
        total_operation_min=float(total_operation_min),
    )


def marker_html(text: str, color: str, border_radius: str = "50%") -> str:
    return f"""
    <div style="
        width: 30px;
        height: 30px;
        border-radius: {border_radius};
        background: {color};
        color: white;
        border: 3px solid white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 13px;
        font-weight: 800;
        box-shadow: 0 1px 5px rgba(0,0,0,0.4);
    ">{text}</div>
    """


def legend_html(route_groups: Sequence[RouteGroup], provider_label: str) -> str:
    rows = "".join(
        f"""
        <div style="display:flex; align-items:center; gap:6px; margin:3px 0;">
            <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background:{group.color};"></span>
            <span>{group.name}: {len(group.stops)}개 정류장, {group.total_operation_min:.0f}분</span>
        </div>
        """
        for group in route_groups
    )
    return f"""
    <div style="
        position: fixed;
        bottom: 24px;
        right: 16px;
        z-index: 9999;
        background: rgba(255,255,255,0.94);
        padding: 12px 14px;
        border-radius: 8px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.18);
        font-size: 13px;
        line-height: 1.35;
        min-width: 220px;
    ">
        <div style="font-weight:800; margin-bottom:6px;">온-책 노선망</div>
        <div style="color:#555; margin-bottom:8px;">{provider_label}</div>
        {rows}
        <div style="border-top:1px solid #ddd; margin-top:8px; padding-top:8px;">
            <div><span style="display:inline-block; width:24px; border-top:3px solid #333; margin-right:6px;"></span>Naver 실제 도로 경로</div>
            <div><span style="display:inline-block; width:24px; border-top:3px dashed #333; margin-right:6px;"></span>Haversine fallback</div>
            <div>H: 허브 도서관</div>
            <div>숫자 마커: 방문 순서</div>
        </div>
    </div>
    """


def summary_box_html(route_groups: Sequence[RouteGroup]) -> str:
    route_rows = "".join(
        f"<div>{group.name}: {group.total_operation_min:.1f}분</div>"
        for group in route_groups
    )
    total_stops = sum(len(group.stops) for group in route_groups)
    return f"""
    <div style="
        position: fixed;
        top: 80px;
        left: 16px;
        z-index: 9999;
        background: rgba(255,255,255,0.94);
        padding: 12px 14px;
        border-radius: 8px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.18);
        font-size: 13px;
        line-height: 1.45;
        max-width: 320px;
    ">
        <div style="font-weight:800; margin-bottom:6px;">온-책 운영 요약</div>
        <div>총 노선 수: {len(route_groups)}개</div>
        <div>총 차량 수: {len(route_groups)}대</div>
        <div>하루 방문 거점 수: {total_stops}개</div>
        <div>지점당 정차시간: {STOP_MINUTES_PER_PLACE}분</div>
        <div>운영 가능 기준: 360분 이하</div>
        <div>진안 출발 허브: {REGION_HUBS["jinan"]["hub_library_name"]}</div>
        <div>임실 출발 허브: {REGION_HUBS["imsil"]["hub_library_name"]}</div>
        <div style="border-top:1px solid #ddd; margin-top:8px; padding-top:8px;">{route_rows}</div>
    </div>
    """


def render_route_map(route_groups: Sequence[RouteGroup], output_path: Path, provider_label: str) -> None:
    all_locations = [location for group in route_groups for location in group.route]
    center_lat = sum(location.lat for location in all_locations) / len(all_locations)
    center_lon = sum(location.lon for location in all_locations) / len(all_locations)

    m = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles="OpenStreetMap")

    rendered_hubs = set()
    for group in route_groups:
        hub_key = (round(group.hub.lat, 5), round(group.hub.lon, 5))
        if hub_key not in rendered_hubs:
            rendered_hubs.add(hub_key)
            folium.Marker(
                location=[group.hub.lat, group.hub.lon],
                tooltip=f"허브: {group.hub.name}",
                popup=(
                    f"허브명: {group.hub.name}<br>"
                    f"지역: {group.region}<br>"
                    f"위도: {group.hub.lat:.7f}<br>"
                    f"경도: {group.hub.lon:.7f}"
                ),
                icon=folium.DivIcon(html=marker_html("H", "#333", "8px")),
            ).add_to(m)

        route_layer = folium.FeatureGroup(name=group.name, show=True)
        stop_details = [row for row in group.details if int(row["stop_min"]) > 0]
        for row, stop in zip(stop_details, group.route[1:-1]):
            folium.Marker(
                location=[stop.lat, stop.lon],
                tooltip=f"{group.name} {row['order']}. {stop.name}",
                popup=(
                    f"노선명: {group.name}<br>"
                    f"허브명: {group.hub.name}<br>"
                    f"방문순서: {row['order']}<br>"
                    f"정차지명: {stop.name}<br>"
                    f"정차지 유형: {stop.facility_type}<br>"
                    f"도로 주행거리: {row['drive_km']}km<br>"
                    f"도로 주행시간: {row['drive_min']}분<br>"
                    f"정차시간: {row['stop_min']}분<br>"
                    f"누적 운영시간: {row['cumulative_operation_min']}분<br>"
                    f"source: {row['source']}"
                ),
                icon=folium.DivIcon(html=marker_html(str(row["order"]), group.color)),
            ).add_to(route_layer)

        for row in group.details:
            path = json.loads(str(row["route_path_json"]))
            if len(path) < 2:
                continue
            folium.PolyLine(
                path,
                color=group.color,
                weight=5,
                opacity=0.82,
                dash_array="8,8" if row["source"] == "haversine_fallback" else None,
                tooltip=f"{group.name}: {row['from_name']} -> {row['to_name']}",
                popup=(
                    f"노선명: {group.name}<br>"
                    f"{row['from_name']} -> {row['to_name']}<br>"
                    f"도로 주행거리: {row['drive_km']}km<br>"
                    f"도로 주행시간: {row['drive_min']}분<br>"
                    f"source: {row['source']}"
                ),
            ).add_to(route_layer)

        route_layer.add_to(m)

    m.get_root().html.add_child(folium.Element(legend_html(route_groups, provider_label)))
    m.get_root().html.add_child(folium.Element(summary_box_html(route_groups)))
    folium.LayerControl(collapsed=False).add_to(m)
    m.save(output_path)


def save_outputs(route_groups: Sequence[RouteGroup], output_dir: Path, prefix: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    candidate_rows = []
    detail_rows = []
    summary_rows = []
    for group in route_groups:
        for stop in group.stops:
            candidate_rows.append(
                {
                    "route": group.name,
                    "region": group.region,
                    "hub_name": group.hub.name,
                    "name": stop.name,
                    "facility_type": stop.facility_type,
                    "address": stop.address,
                    "suitability_score": stop.suitability_score,
                    "nearest_bus_stop": stop.nearest_bus_stop,
                    "nearest_bus_stop_km": stop.nearest_bus_stop_km,
                    "nearby_bus_stop_count_500m": stop.nearby_bus_stop_count,
                    "lat": stop.lat,
                    "lon": stop.lon,
                }
            )
        for row in group.details:
            detail_rows.append(
                {
                    "route": group.name,
                    "region": group.region,
                    "hub_name": group.hub.name,
                    "order": row["order"],
                    "from_name": row["from_name"],
                    "to_name": row["to_name"],
                    "to_facility_type": row["to_facility_type"],
                    "drive_km": row["drive_km"],
                    "drive_min": row["drive_min"],
                    "stop_min": row["stop_min"],
                    "cumulative_operation_min": row["cumulative_operation_min"],
                    "source": row["source"],
                    "route_path_json": row["route_path_json"],
                }
            )
        summary_rows.append(
            {
                "route": group.name,
                "region": group.region,
                "hub_name": group.hub.name,
                "stop_count": len(group.stops),
                "total_drive_km": round(group.total_drive_km, 2),
                "total_drive_min": round(group.total_drive_min, 1),
                "total_stop_min": len(group.stops) * STOP_MINUTES_PER_PLACE,
                "total_operation_min": round(group.total_operation_min, 1),
                "operation_status": "운영 가능" if group.total_operation_min <= 360 else "조정 필요",
            }
        )

    pd.DataFrame(candidate_rows).to_csv(output_dir / f"{prefix}_stop_candidates.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(detail_rows).to_csv(output_dir / f"{prefix}_route_result.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(summary_rows).to_csv(output_dir / f"{prefix}_route_summary.csv", index=False, encoding="utf-8-sig")


def build_region_routes(
    region_key: str,
    buses: int,
    provider: str,
    color_offset: int,
    library_df: pd.DataFrame,
    bus_df: pd.DataFrame,
    data_candidate_limit: int,
    stops_per_bus: int,
) -> List[RouteGroup]:
    region = REGIONS[region_key]
    region_label = str(region["label"])
    region_bus_df = region_bus_stops(bus_df, region_label)
    hub_candidate = choose_hub_from_library(library_df, region_label, str(region["hub_library_name"]))
    extra_candidates = bus_stop_candidates(region_bus_df, region_label, data_candidate_limit)
    merged_candidates = merge_candidates(region["candidates"], extra_candidates)
    merged_candidates = sorted(
        merged_candidates,
        key=lambda candidate: candidate.suitability_score(),
        reverse=True,
    )[: buses * stops_per_bus]

    hub = candidate_to_location(hub_candidate, provider, region_bus_df)
    candidates = [
        candidate_to_location(candidate, provider, region_bus_df)
        for candidate in merged_candidates
    ]
    candidate_groups = split_candidates_for_buses(candidates, buses)

    route_groups = []
    for index, stops in enumerate(candidate_groups):
        color = ROUTE_COLORS[(color_offset + index) % len(ROUTE_COLORS)]
        route_groups.append(
            build_route_group(
                name=f"{region['route_prefix']} {index + 1}호차",
                region=region_label,
                region_key=region_key,
                color=color,
                hub=hub,
                stops=stops,
                provider=provider,
            )
        )
    return route_groups



# === ON_LIBRARY_DATA_DRIVEN_CANDIDATES ===
def load_config_candidates(candidate_csv: Path) -> Dict[str, List[StopCandidate]]:
    """
    config/manual_candidates.csv에서 데이터 기반 입지 후보지를 읽어온다.
    주의: 기존 StopCandidate.suitability_score() 공식과 호환하기 위해
    parking_score 필드에는 접근성지수,
    access_score 필드에는 운영가능성지수를 넣는다.
    """
    if not candidate_csv.exists():
        print(f"[site candidates] 후보지 CSV 없음: {candidate_csv}", file=sys.stderr)
        return {}

    df = pd.read_csv(candidate_csv, encoding="utf-8-sig")
    result: Dict[str, List[StopCandidate]] = {}

    for region_key, group in df.groupby("region_key"):
        candidates: List[StopCandidate] = []
        group = group.sort_values("final_score", ascending=False) if "final_score" in group.columns else group

        for _, row in group.iterrows():
            try:
                candidates.append(
                    StopCandidate(
                        name=str(row["name"]),
                        address=str(row["address"]),
                        facility_type=str(row["facility_type"]),
                        demand_score=float(row.get("demand_score", 3.0)),
                        parking_score=float(row.get("parking_score", row.get("access_score", 3.0))),
                        public_score=float(row.get("public_score", 3.5)),
                        access_score=float(row.get("access_score", row.get("operation_score", 3.0))),
                        lat=float(row["lat"]) if pd.notna(row["lat"]) else None,
                        lon=float(row["lon"]) if pd.notna(row["lon"]) else None,
                    )
                )
            except Exception as exc:
                print(f"[site candidates] 후보지 로드 실패: {row.to_dict()} / {exc}", file=sys.stderr)

        if candidates:
            result[str(region_key)] = candidates

    return result


def apply_config_candidates(config_dir: Path) -> None:
    candidate_csv = config_dir / "manual_candidates.csv"
    loaded = load_config_candidates(candidate_csv)

    for region_key, candidates in loaded.items():
        if region_key in REGIONS and candidates:
            REGIONS[region_key]["candidates"] = candidates
            print(
                f"[site candidates] {region_key}: config/manual_candidates.csv에서 {len(candidates)}개 후보지 적용",
                file=sys.stderr,
            )
# === ON_LIBRARY_DATA_DRIVEN_CANDIDATES_END ===

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PBGround 온-책 이동식 도서관 노선망 생성기")
    parser.add_argument(
        "--region",
        choices=["jinan", "imsil", "all"],
        default="all",
        help="생성할 지역",
    )
    parser.add_argument(
        "--buses",
        type=int,
        default=DEFAULT_BUSES_PER_REGION,
        help="지역당 버스 수",
    )
    parser.add_argument(
        "--stops-per-bus",
        type=int,
        default=6,
        help="버스 1대당 최대 정류장 수",
    )
    parser.add_argument(
        "--provider",
        choices=["auto", "naver", "google", "haversine"],
        default="naver",
        help="기본값은 naver. auto는 네이버 키가 있으면 naver, 없으면 google, haversine은 내장 좌표 기반 샘플 지도",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Google Maps Platform API 키. 없으면 .env/환경변수에서 찾음",
    )
    parser.add_argument(
        "--google-travel-mode",
        choices=["DRIVE", "TRANSIT", "WALK", "BICYCLE", "TWO_WHEELER"],
        default=GOOGLE_TRAVEL_MODE,
        help="Google Routes API 이동 모드. DRIVE가 전부 실패하면 TRANSIT를 자동 재시도",
    )
    parser.add_argument(
        "--naver-client-id",
        default=None,
        help="네이버 Cloud Maps API Key ID. 없으면 .env/환경변수에서 찾음",
    )
    parser.add_argument(
        "--naver-client-secret",
        default=None,
        help="네이버 Cloud Maps API Key. 없으면 .env/환경변수에서 찾음",
    )
    parser.add_argument(
        "--naver-direction-option",
        choices=["trafast", "tracomfort", "traoptimal", "traavoidtoll", "traavoidcaronly"],
        default=NAVER_DIRECTION_OPTION,
        help="네이버 Directions 경로 옵션",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="결과 CSV/HTML 저장 디렉터리",
    )
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help="도서관/버스정류장 CSV가 있는 디렉터리",
    )
    parser.add_argument(
        "--data-candidate-limit",
        type=int,
        default=12,
        help="버스정류장 CSV에서 지역별로 추가할 공공거점 후보 수",
    )
    return parser.parse_args()


def resolve_provider(provider: str) -> str:
    if provider == "haversine":
        print("[provider] Haversine sample mode를 사용합니다.", file=sys.stderr)
        return "haversine"

    if provider in {"auto", "naver"} and NAVER_CLIENT_ID and NAVER_CLIENT_SECRET:
        print(
            f"[provider] Naver Maps API를 사용합니다. key source: "
            f"{NAVER_CLIENT_ID_SOURCE}/{NAVER_CLIENT_SECRET_SOURCE}",
            file=sys.stderr,
        )
        return "naver"

    if provider == "naver":
        accepted_id_names = ", ".join(NAVER_CLIENT_ID_NAMES)
        accepted_secret_names = ", ".join(NAVER_CLIENT_SECRET_NAMES)
        raise EnvironmentError(
            "Naver API 모드가 선택됐지만 인증 정보를 찾지 못했습니다. "
            f"ID는 --naver-client-id 또는 {accepted_id_names}, "
            f"Secret/API Key는 --naver-client-secret 또는 {accepted_secret_names} 중 하나로 설정하세요."
        )

    if provider in {"auto", "google"} and GOOGLE_MAPS_API_KEY:
        print(
            f"[provider] Google API를 사용합니다. key source: {GOOGLE_MAPS_API_KEY_SOURCE}",
            file=sys.stderr,
        )
        return "google"

    if provider == "google":
        accepted_names = ", ".join(GOOGLE_MAPS_API_KEY_NAMES)
        raise EnvironmentError(
            "Google API 모드가 선택됐지만 API 키를 찾지 못했습니다. "
            f"--api-key 또는 다음 환경변수 중 하나를 설정하세요: {accepted_names}"
        )

    print(
        "[provider] 네이버/Google API 키를 찾지 못해 Haversine sample mode를 사용합니다. "
        "--provider naver 또는 --provider google을 쓰면 키 누락 시 즉시 실패합니다.",
        file=sys.stderr,
    )
    return "haversine"


def provider_label(provider: str) -> str:
    if provider == "haversine":
        return "Haversine sample mode"
    if provider == "naver":
        return f"Naver Maps Directions API ({NAVER_DIRECTION_OPTION})"
    if GOOGLE_MATRIX_MODE == GOOGLE_TRAVEL_MODE:
        return f"Google Routes API ({GOOGLE_EFFECTIVE_TRAVEL_MODE})"
    return f"Google Routes API ({GOOGLE_TRAVEL_MODE} -> {GOOGLE_MATRIX_MODE})"


def main() -> None:
    global GOOGLE_MAPS_API_KEY, GOOGLE_MAPS_API_KEY_SOURCE, GOOGLE_TRAVEL_MODE, GOOGLE_MATRIX_MODE, GOOGLE_EFFECTIVE_TRAVEL_MODE
    global NAVER_CLIENT_ID, NAVER_CLIENT_ID_SOURCE, NAVER_CLIENT_SECRET, NAVER_CLIENT_SECRET_SOURCE, NAVER_DIRECTION_OPTION

    args = parse_args()
    explicit_key, explicit_source = get_google_maps_api_key(args.api_key)
    if explicit_key:
        GOOGLE_MAPS_API_KEY = explicit_key
        GOOGLE_MAPS_API_KEY_SOURCE = explicit_source
    if args.naver_client_id:
        NAVER_CLIENT_ID = args.naver_client_id
        NAVER_CLIENT_ID_SOURCE = "--naver-client-id"
    if args.naver_client_secret:
        NAVER_CLIENT_SECRET = args.naver_client_secret
        NAVER_CLIENT_SECRET_SOURCE = "--naver-client-secret"
    GOOGLE_TRAVEL_MODE = args.google_travel_mode
    GOOGLE_MATRIX_MODE = GOOGLE_TRAVEL_MODE
    GOOGLE_EFFECTIVE_TRAVEL_MODE = GOOGLE_TRAVEL_MODE
    NAVER_DIRECTION_OPTION = args.naver_direction_option

    output_dir = Path(args.output_dir)
    data_dir = Path(args.data_dir)
    library_df = load_library_data(data_dir)
    bus_df = load_bus_stop_data(data_dir)

    apply_config_candidates(Path(__file__).resolve().parent / "config")

    provider = resolve_provider(args.provider)
    if provider == "naver":
        load_naver_route_cache(output_dir)

    region_keys = ["jinan", "imsil"] if args.region == "all" else [args.region]

    all_route_groups: List[RouteGroup] = []
    color_offset = 0
    for region_key in region_keys:
        route_groups = build_region_routes(
            region_key=region_key,
            buses=args.buses,
            provider=provider,
            color_offset=color_offset,
            library_df=library_df,
            bus_df=bus_df,
            data_candidate_limit=args.data_candidate_limit,
            stops_per_bus=args.stops_per_bus,
        )
        prefix = f"{region_key}_{provider if provider != 'haversine' else 'sample'}"
        save_outputs(route_groups, output_dir, prefix)
        render_route_map(route_groups, output_dir / f"{prefix}_route_map.html", provider_label(provider))
        all_route_groups.extend(route_groups)
        color_offset += len(route_groups)

    if len(region_keys) > 1:
        prefix = f"all_{provider if provider != 'haversine' else 'sample'}"
        save_outputs(all_route_groups, output_dir, prefix)
        render_route_map(all_route_groups, output_dir / f"{prefix}_route_map.html", provider_label(provider))

    if provider == "naver":
        save_naver_route_cache()

    manifest = {
        "provider": provider_label(provider),
        "output_dir": str(output_dir),
        "maps": sorted(str(path) for path in output_dir.glob("*_route_map.html")),
        "csv": sorted(str(path) for path in output_dir.glob("*.csv")),
    }
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
