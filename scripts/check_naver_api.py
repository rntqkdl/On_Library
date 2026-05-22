from pathlib import Path
import os
import requests
from dotenv import load_dotenv

BASE_DIR = Path(r"C:\PB_Data")
ENV_PATH = BASE_DIR / ".env"

print("=" * 70)
print("온-책 Naver Maps API 엔드포인트 진단")
print("=" * 70)

print("ENV_PATH:", ENV_PATH)
print("ENV 존재 여부:", ENV_PATH.exists())

load_dotenv(ENV_PATH)

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "").strip()
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "").strip()
NAVER_DIRECTION_OPTION = os.getenv("NAVER_DIRECTION_OPTION", "trafast").strip()

print("\n[키 확인]")
print("NAVER_CLIENT_ID 길이:", len(NAVER_CLIENT_ID))
print("NAVER_CLIENT_SECRET 길이:", len(NAVER_CLIENT_SECRET))

if NAVER_CLIENT_ID:
    print("NAVER_CLIENT_ID 일부:", NAVER_CLIENT_ID[:4] + "..." + NAVER_CLIENT_ID[-4:])

if NAVER_CLIENT_SECRET:
    print("NAVER_CLIENT_SECRET 일부:", NAVER_CLIENT_SECRET[:4] + "..." + NAVER_CLIENT_SECRET[-4:])

if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
    raise RuntimeError("C:\\PB_Data\\.env에 NAVER_CLIENT_ID, NAVER_CLIENT_SECRET을 설정하세요.")

headers = {
    "x-ncp-apigw-api-key-id": NAVER_CLIENT_ID,
    "x-ncp-apigw-api-key": NAVER_CLIENT_SECRET,
}

# 네이버 좌표 순서: 경도,위도
params = {
    "start": "127.4247,35.7906",
    "goal": "127.3985,35.6885",
    "option": NAVER_DIRECTION_OPTION,
}

direction_urls = [
    ("신규 Maps 엔드포인트", "https://maps.apigw.ntruss.com/map-direction/v1/driving"),
    ("기존 naveropenapi 엔드포인트", "https://naveropenapi.apigw.ntruss.com/map-direction/v1/driving"),
]

success_url = None

for label, url in direction_urls:
    print("\n" + "-" * 70)
    print(f"[Directions 테스트] {label}")
    print("URL:", url)

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=20,
        )

        print("HTTP 상태코드:", response.status_code)
        print("응답 앞부분:")
        print(response.text[:1200])

        data = response.json()

        if response.status_code == 200 and "route" in data:
            route_list = data["route"].get(NAVER_DIRECTION_OPTION) or data["route"].get("trafast")

            if route_list:
                route = route_list[0]
                summary = route["summary"]

                distance_km = summary["distance"] / 1000
                duration_min = summary["duration"] / 1000 / 60

                print("\nDirections API 연결 성공")
                print(f"성공 엔드포인트: {url}")
                print(f"도로 주행거리: {distance_km:.2f} km")
                print(f"예상 주행시간: {duration_min:.1f} 분")

                success_url = url
                break

    except Exception as e:
        print("요청 실패:", e)

if success_url is None:
    print("\n결론: 두 엔드포인트 모두 실패했습니다.")
    print("이 경우 my-map-service의 인증정보를 다시 복사하거나, Maps Subscription 상태를 확인해야 합니다.")
else:
    print("\n결론: 아래 엔드포인트를 google_route_optimizer.py에 반영하세요.")
    print(success_url)


print("\n" + "=" * 70)
print("Geocoding 테스트")
print("=" * 70)

geocode_urls = [
    ("신규 Maps 엔드포인트", "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"),
    ("기존 naveropenapi 엔드포인트", "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode"),
]

geocode_params = {
    "query": "전북특별자치도 진안군 진안읍 중앙로 66"
}

for label, url in geocode_urls:
    print("\n" + "-" * 70)
    print(f"[Geocoding 테스트] {label}")
    print("URL:", url)

    try:
        response = requests.get(
            url,
            headers=headers,
            params=geocode_params,
            timeout=20,
        )

        print("HTTP 상태코드:", response.status_code)
        print("응답 앞부분:")
        print(response.text[:1000])

        data = response.json()

        if response.status_code == 200 and data.get("addresses"):
            item = data["addresses"][0]
            print("\nGeocoding API 연결 성공")
            print("성공 엔드포인트:", url)
            print("주소:", item.get("roadAddress") or item.get("jibunAddress"))
            print("경도:", item.get("x"))
            print("위도:", item.get("y"))
            break

    except Exception as e:
        print("요청 실패:", e)