from pathlib import Path

TARGET = Path(r"C:\PB_Data\google_route_optimizer.py")

if not TARGET.exists():
    raise FileNotFoundError(TARGET)

text = TARGET.read_text(encoding="utf-8")

# 1. 네이버 신규 Maps 엔드포인트 보정
text = text.replace(
    "https://naveropenapi.apigw.ntruss.com/map-direction/v1/driving",
    "https://maps.apigw.ntruss.com/map-direction/v1/driving"
)

text = text.replace(
    "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode",
    "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
)

# 2. timeout=20을 더 넉넉하게 변경
text = text.replace("timeout=20", "timeout=(30, 90)")

# 3. requests.get 자동 재시도 패치 삽입
patch_marker = "# === ONBOOK_NAVER_RETRY_PATCH ==="

retry_patch = r'''
# === ONBOOK_NAVER_RETRY_PATCH ===
import time as _onbook_retry_time
from requests.exceptions import Timeout as _OnbookTimeout
from requests.exceptions import ConnectionError as _OnbookConnectionError

_original_requests_get = requests.get

def _onbook_requests_get_with_retry(*args, **kwargs):
    """
    Naver Maps API 호출 중 일시적인 SSL handshake timeout,
    read timeout, connection error가 발생하면 자동 재시도한다.
    """
    if kwargs.get("timeout") == 20 or kwargs.get("timeout") is None:
        kwargs["timeout"] = (30, 90)

    last_error = None

    for attempt in range(1, 5):
        try:
            return _original_requests_get(*args, **kwargs)
        except (_OnbookTimeout, _OnbookConnectionError) as e:
            last_error = e
            wait_sec = min(3 * attempt, 12)
            print(f"[Naver retry] {attempt}/4 요청 실패: {e}")
            print(f"[Naver retry] {wait_sec}초 대기 후 재시도합니다.")
            _onbook_retry_time.sleep(wait_sec)

    raise last_error

requests.get = _onbook_requests_get_with_retry
# === ONBOOK_NAVER_RETRY_PATCH_END ===
'''

if patch_marker not in text:
    if "import requests" not in text:
        raise RuntimeError("google_route_optimizer.py에서 import requests를 찾지 못했습니다.")

    text = text.replace("import requests", "import requests" + retry_patch, 1)

TARGET.write_text(text, encoding="utf-8")

print("패치 완료:", TARGET)
print("적용 내용:")
print("- Naver 신규 Maps 엔드포인트 반영")
print("- timeout=(30, 90) 적용")
print("- requests.get 자동 재시도 4회 적용")