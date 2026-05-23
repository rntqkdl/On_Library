from pathlib import Path
import os
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

url = "https://apis.data.go.kr/1613000/BusRouteInfoInqireService/getCtyCodeList"

params = {
    "serviceKey": SERVICE_KEY,
    "_type": "json",
    "numOfRows": 1000,
    "pageNo": 1,
}

response = requests.get(url, params=params, timeout=30)

print("HTTP 상태코드:", response.status_code)
print("응답 앞부분:")
print(response.text[:1000])

data = response.json()

items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])

if isinstance(items, dict):
    items = [items]

df = pd.DataFrame(items)

if df.empty:
    raise RuntimeError("도시코드 목록을 가져오지 못했습니다. 인증키 또는 API 활용 신청 상태를 확인하세요.")

df.to_csv(OUTPUT / "tago_citycodes.csv", index=False, encoding="utf-8-sig")

print("\n[저장 완료]", OUTPUT / "tago_citycodes.csv")
print("\n진안/임실 관련 도시코드 후보:")
print(df[df.astype(str).agg(" ".join, axis=1).str.contains("진안|임실|전북|전라북도|전북특별자치도", na=False)])