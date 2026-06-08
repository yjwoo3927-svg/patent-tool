"""
Google Sheets 내부 특허 데이터 연동 모듈
- 공개 CSV URL로 직접 읽기 (API 키 불필요)
- KIPRIS 다운로드 컬럼 구조 그대로 사용
"""
import pandas as pd
import streamlit as st
from datetime import datetime

SHEET_ID = "1GOoCEpfd72Ikonp6cvJSjDFDGgiG8MonefeUr4Wcu7U"
SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# KIPRIS 컬럼 → 내부 변수 매핑
COL_MAP = {
    "순번":           "index",
    "발명의명칭":      "title",
    "발명의명칭(영문)": "title_eng",
    "IPC분류":        "ipc_codes",
    "출원번호":        "patent_number",
    "출원일자":        "application_date",
    "출원인":          "assignee",
    "등록번호":        "register_number",
    "등록일자":        "publication_date",
    "공개일자":        "open_date",
    "법적상태":        "status",
    "심사진행상태":    "exam_status",
    "요약":            "abstract",
    "발명자":          "inventors",
    "지정국":          "country",
    "피인용 횟수":     "citations",
    "청구항":          "claims_count",
}

def _fmt_date(val):
    if pd.isna(val) or not str(val).strip():
        return ""
    s = str(val).strip().replace("/", "-").replace(".", "-")
    # 20210705 → 2021-07-05
    digits = s.replace("-", "")
    if len(digits) == 8 and digits.isdigit():
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}"
    return s

@st.cache_data(ttl=300)  # 5분 캐시
def load_internal_patents():
    """Google Sheets에서 내부 특허 데이터 로드"""
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        # 컬럼명 매핑
        df = df.rename(columns=COL_MAP)

        patents = []
        for _, row in df.iterrows():
            def g(col):
                val = row.get(col, "")
                return "" if pd.isna(val) else str(val).strip()

            # 국가 처리: 지정국이 없으면 출원번호로 추정
            country = g("country")
            if not country:
                pno = g("patent_number")
                if pno.startswith("KR") or pno.startswith("10-"):
                    country = "KR"
                elif pno.startswith("US"):
                    country = "US"
                elif pno.startswith("EP"):
                    country = "EP"
                else:
                    country = "KR"

            # 청구항 수 처리
            claims_raw = g("claims_count")
            try:
                claims_count = int(float(claims_raw)) if claims_raw else 0
            except:
                claims_count = len(claims_raw.split("\n")) if claims_raw else 0

            # 피인용 처리
            try:
                citations = int(float(g("citations"))) if g("citations") else 0
            except:
                citations = 0

            patents.append({
                "patent_number":    g("patent_number") or g("register_number"),
                "title":            g("title"),
                "title_eng":        g("title_eng"),
                "assignee":         g("assignee") or "네패스",
                "inventors":        g("inventors"),
                "ipc_codes":        g("ipc_codes"),
                "application_date": _fmt_date(g("application_date")),
                "publication_date": _fmt_date(g("publication_date") or g("open_date")),
                "country":          country,
                "abstract":         g("abstract"),
                "status":           g("status"),
                "exam_status":      g("exam_status"),
                "claims_count":     claims_count,
                "citations":        citations,
                "register_number":  g("register_number"),
                "tech_field":       "",
                "db_source":        "내부DB",
            })
        return patents, None
    except Exception as e:
        return [], str(e)


def filter_internal_patents(patents, keyword="", assignee="", ipc="",
                             date_from="", date_to="", status=""):
    """내부 특허 필터링"""
    filtered = patents.copy()

    if keyword:
        kw = keyword.lower()
        filtered = [p for p in filtered
                    if kw in p["title"].lower()
                    or kw in p.get("title_eng","").lower()
                    or kw in p.get("abstract","").lower()]
    if assignee:
        al = assignee.lower()
        filtered = [p for p in filtered if al in p["assignee"].lower()]
    if ipc:
        filtered = [p for p in filtered
                    if ipc.replace(" ","") in p["ipc_codes"].replace(" ","")]
    if status and status != "전체":
        filtered = [p for p in filtered if p["status"] == status]
    if date_from:
        try:
            df_dt = datetime.strptime(
                date_from+"-01-01" if len(date_from)==4 else date_from, "%Y-%m-%d")
            filtered = [p for p in filtered if p["application_date"] and
                        datetime.strptime(p["application_date"], "%Y-%m-%d") >= df_dt]
        except: pass
    if date_to:
        try:
            dt_dt = datetime.strptime(
                date_to+"-12-31" if len(date_to)==4 else date_to, "%Y-%m-%d")
            filtered = [p for p in filtered if p["application_date"] and
                        datetime.strptime(p["application_date"], "%Y-%m-%d") <= dt_dt]
        except: pass

    return filtered
