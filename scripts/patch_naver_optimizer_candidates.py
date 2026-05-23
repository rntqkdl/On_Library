from pathlib import Path

ROOT = Path(r"C:\PB_Data")
TARGET = ROOT / "naver_route_optimizer.py"

if not TARGET.exists():
    raise FileNotFoundError(TARGET)

text = TARGET.read_text(encoding="utf-8")

insert_code = r'''

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
'''

if "ON_LIBRARY_DATA_DRIVEN_CANDIDATES" not in text:
    marker = "\ndef parse_args() -> argparse.Namespace:"
    if marker not in text:
        raise RuntimeError("parse_args 위치를 찾지 못했습니다.")
    text = text.replace(marker, insert_code + marker, 1)

# main() 안에서 data_dir, output_dir 설정 뒤 후보지 적용 코드 삽입
old = """    output_dir = Path(args.output_dir)
    data_dir = Path(args.data_dir)
    library_df = load_library_data(data_dir)
    bus_df = load_bus_stop_data(data_dir)

    provider = resolve_provider(args.provider)
"""

new = """    output_dir = Path(args.output_dir)
    data_dir = Path(args.data_dir)
    library_df = load_library_data(data_dir)
    bus_df = load_bus_stop_data(data_dir)

    apply_config_candidates(Path(__file__).resolve().parent / "config")

    provider = resolve_provider(args.provider)
"""

if old in text and "apply_config_candidates(Path(__file__).resolve().parent / \"config\")" not in text:
    text = text.replace(old, new, 1)
else:
    print("[patch] main 삽입부는 이미 적용됐거나 패턴이 다릅니다.")

# 기본 provider를 naver로 바꾸고 싶을 경우
text = text.replace('default="auto",\n        help="auto는 네이버 키가 있으면 naver', 'default="naver",\n        help="기본값은 naver. auto는 네이버 키가 있으면 naver')

# output 기본값이 다른 경우 보정
text = text.replace('default="PBGround/output"', 'default="output"')

TARGET.write_text(text, encoding="utf-8")
print("[완료] naver_route_optimizer.py 후보지 config 패치 적용")