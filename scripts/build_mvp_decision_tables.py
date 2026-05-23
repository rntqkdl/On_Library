from pathlib import Path
import pandas as pd

ROOT = Path(r"C:\PB_Data")
OUTPUT = ROOT / "output"

SITE_SCORE_CSV = OUTPUT / "site_selection_candidate_scores.csv"
ROUTE_SUMMARY_CSV = OUTPUT / "all_naver_route_summary.csv"
ROUTE_RESULT_CSV = OUTPUT / "all_naver_route_result.csv"

OUT_CANDIDATE = OUTPUT / "mvp_candidate_decision_table.csv"
OUT_ROUTE = OUTPUT / "mvp_route_decision_summary.csv"


def reason_from_scores(row: pd.Series) -> str:
    reasons = []

    demand = float(row.get("demand_score", 0))
    access = float(row.get("access_score", 0))
    public = float(row.get("public_score", 0))
    operation = float(row.get("operation_score", 0))
    nearby = int(row.get("nearby_bus_stop_count_500m", 0))
    nearest = float(row.get("nearest_bus_stop_km", 999))

    if demand >= 4.0:
        reasons.append("고령층·청소년 수요가 높은 지역")
    elif demand >= 3.0:
        reasons.append("기본 수요가 확인되는 지역")

    if access >= 4.0:
        reasons.append("정류장 접근성이 우수한 지점")
    elif nearby == 0 or nearest >= 1:
        reasons.append("대중교통 접근성 보완이 필요한 지점")
    else:
        reasons.append("생활권 내 접근 가능한 지점")

    if public >= 4.5:
        reasons.append("공공거점성이 높은 시설")
    elif public >= 4.0:
        reasons.append("주민 공동 이용 가능성이 있는 시설")

    if operation >= 4.0:
        reasons.append("이동식 도서관 정차 운영에 적합")
    elif operation >= 3.5:
        reasons.append("운영 가능성이 있는 후보지")

    if not reasons:
        reasons.append("생활거점 후보지로 검토 가능")

    return " / ".join(reasons[:3])


def grade_score(score: float) -> str:
    if score >= 4.3:
        return "매우 높음"
    if score >= 3.8:
        return "높음"
    if score >= 3.2:
        return "보통"
    return "낮음"


def build_candidate_table() -> pd.DataFrame:
    if not SITE_SCORE_CSV.exists():
        raise FileNotFoundError(f"{SITE_SCORE_CSV} 파일이 없습니다. 먼저 python scripts\\build_site_candidates.py 실행하세요.")

    df = pd.read_csv(SITE_SCORE_CSV, encoding="utf-8-sig")

    needed = ["region_key", "name", "facility_type", "final_score"]
    for col in needed:
        if col not in df.columns:
            raise RuntimeError(f"{SITE_SCORE_CSV.name}에 {col} 컬럼이 없습니다.")

    df = df.copy()
    df["선정등급"] = df["final_score"].astype(float).map(grade_score)
    df["선정근거"] = df.apply(reason_from_scores, axis=1)

    display_cols = [
        "region_key",
        "region_label",
        "name",
        "facility_type",
        "final_score",
        "선정등급",
        "선정근거",
        "demand_score",
        "access_score",
        "public_score",
        "operation_score",
        "nearest_bus_stop_km",
        "nearby_bus_stop_count_500m",
        "source_file",
        "address",
        "lat",
        "lon",
    ]

    display_cols = [col for col in display_cols if col in df.columns]

    out = df[display_cols].sort_values(["region_key", "final_score"], ascending=[True, False])
    out.to_csv(OUT_CANDIDATE, index=False, encoding="utf-8-sig")
    return out


def build_route_summary_table() -> pd.DataFrame:
    if not ROUTE_SUMMARY_CSV.exists():
        print(f"[skip] {ROUTE_SUMMARY_CSV} 없음")
        return pd.DataFrame()

    summary = pd.read_csv(ROUTE_SUMMARY_CSV, encoding="utf-8-sig")
    summary = summary.copy()

    if "total_operation_min" in summary.columns:
        summary["운영판정"] = summary["total_operation_min"].apply(
            lambda x: "운영 가능" if float(x) <= 360 else "조정 필요"
        )

    if "total_drive_min" in summary.columns and "total_stop_min" in summary.columns:
        summary["운영시간구성"] = summary.apply(
            lambda r: f"이동 {float(r['total_drive_min']):.1f}분 + 정차 {float(r['total_stop_min']):.1f}분",
            axis=1,
        )

    if "total_operation_min" in summary.columns:
        summary["운영근거"] = summary.apply(
            lambda r: (
                f"총 운영시간 {float(r['total_operation_min']):.1f}분으로 360분 기준 이내"
                if float(r["total_operation_min"]) <= 360
                else f"총 운영시간 {float(r['total_operation_min']):.1f}분으로 정차지 수 또는 정차시간 조정 필요"
            ),
            axis=1,
        )

    summary.to_csv(OUT_ROUTE, index=False, encoding="utf-8-sig")
    return summary


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    candidate = build_candidate_table()
    route = build_route_summary_table()

    print("[완료] MVP 의사결정 테이블 생성")
    print(" -", OUT_CANDIDATE)
    print(" -", OUT_ROUTE)

    print("\n[후보지 상위 10개]")
    print(candidate.head(10)[["region_key", "name", "facility_type", "final_score", "선정등급", "선정근거"]])

    if not route.empty:
        print("\n[노선 운영 요약]")
        cols = [c for c in ["route", "region", "total_operation_min", "운영판정", "운영근거"] if c in route.columns]
        print(route[cols])


if __name__ == "__main__":
    main()