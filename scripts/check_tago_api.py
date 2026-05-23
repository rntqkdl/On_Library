from pathlib import Path
import os
import requests
from dotenv import load_dotenv

ROOT = Path(r"C:\PB_Data")
load_dotenv(ROOT / ".env")

SERVICE_KEY = os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip()

if not SERVICE_KEY:
    raise RuntimeError(".env에 DATA_GO_KR_SERVICE_KEY를 넣어주세요.")

url = "https://apis.data.go.kr/1613000/BusRouteInfoInqireService/getCtyCodeList"

params = {
    "serviceKey": SERVICE_KEY,
    "_type": "json",
    "numOfRows": 100,
    "pageNo": 1,
}

response = requests.get(url, params=params, timeout=30)

print("HTTP 상태코드:", response.status_code)
print("요청 URL 앞부분:")
print(response.url[:300])
print("\n응답 앞부분:")
print(response.text[:2000])