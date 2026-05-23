from pathlib import Path
import os
import time
import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(r"C:\PB_Data")
OUTPUT = ROOT / "output"
OUTPUT.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")

SERVICE_KEY = os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip()

if not SERVICE_KEY:
    raise RuntimeError(".env에 DATA_GO_KR_SERVICE_KEY를 넣어주세요.")

BASE_URL = "https://apis.data.go.kr/1613000/BusRouteInfoInqireService"


def get_json(endpoint: str, params: dict) -> dict:
    url = f"{BASE_URL}/{endpoint}"
    base_params = {
        "serviceKey": SERVICE_KEY,
        "_type": "json",
        "numOfRows": 1000,
        "pageNo": 1,
    }
    base_params.update(params)

    r = requests.get(url, params=base_params, timeout=30)
    time.sleep(0.3)

    if r.status_code != 200:
        raise RuntimeError(f"{endpoint} HTTP {r.status_code}: {r.text[:500]}")

    try:
        return r.json()
    except Exception as e:
        raise RuntimeError(f"{endpoint} JSON 파싱 실패: {r.text[:1000]}") from e


def items_from_response(data: dict) -> list[dict]:
    body = data.get("response", {}).get("body", {})
    items = body.get("items", {}).get("item", [])

    if isinstance(items, dict):
        items = [items]

    return items if isinstance(items, list) else []


def load_citycodes() -> pd.DataFrame:
    path = OUTPUT / "tago_citycodes.csv"
    if path.exists():
        return pd.read_csv(path, encoding="utf-8-sig")

    data = get_json("getCtyCodeList", {})
    items = items_from_response(data)
    df = pd.DataFrame(items)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return df


def main() -> None:
    city_df = load_citycodes()

    print("[도시코드 컬럼]", list(city_df.columns))

    if city_df.empty:
        raise RuntimeError("도시코드 데이터가 비어 있습니다.")

    # 컬럼명은 응답에 따라 citycode/cityname 또는 cityCode/cityName일 수 있음
    city_code_col = next((c for c in city_df.columns if c.lower() == "citycode"), None)
    city_name_col = next((c for c in city_df.columns if c.lower() == "cityname"), None)

    if not city_code_col or not city_name_col:
        raise RuntimeError(f"citycode/cityname 컬럼을 찾지 못했습니다: {list(city_df.columns)}")

    target = city_df[city_df[city_name_col].astype(str).str.contains("진안|임실|전북|전라북도|전북특별자치도", na=False)].copy()

    target.to_csv(OUTPUT / "tago_target_citycodes.csv", index=False, encoding="utf-8-sig")

    print("\n[진안/임실/전북 관련 cityCode 후보]")
    print(target)

    if target.empty:
        print("\n주의: TAGO 도시코드 목록에서 진안/임실이 직접 검색되지 않았습니다.")
        print("이 경우 전북 또는 인접 상위 도시코드를 기준으로 노선 목록을 확인해야 합니다.")
        return

    route_rows = []

    for _, row in target.iterrows():
        city_code = str(row[city_code_col])
        city_name = str(row[city_name_col])

        print(f"\n[노선목록 조회] {city_name} / cityCode={city_code}")

        try:
            data = get_json("getRouteNoList", {"cityCode": city_code})
            items = items_from_response(data)

            for item in items:
                item["citycode"] = city_code
                item["cityname"] = city_name
                route_rows.append(item)

            print(f"노선 수: {len(items)}")

        except Exception as e:
            print(f"[skip] {city_name}: {e}")

    route_df = pd.DataFrame(route_rows)

    if route_df.empty:
        print("\n노선 목록이 비어 있습니다.")
        return

    route_df.to_csv(OUTPUT / "tago_route_list.csv", index=False, encoding="utf-8-sig")

    print("\n[저장 완료]", OUTPUT / "tago_route_list.csv")
    print(route_df.head())


if __name__ == "__main__":
    main()