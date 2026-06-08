import streamlit as st
import sys, os, io, tempfile
sys.path.insert(0, os.path.dirname(__file__))

from patent_engine import collect_patents
from excel_output import create_patent_excel
from report_output import create_patent_report
from map_output import create_patent_map

st.set_page_config(
    page_title="특허 서지정보 수집 도구",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 특허 · 선행기술 서지정보 수집")
st.caption("KIPRIS · USPTO · EPO · WIPO · CNIPA 통합 검색")

# ── 사이드바: 검색 조건 ──────────────────────────────────────────────────
with st.sidebar:
    st.header("검색 조건")

    keyword = st.text_input("🔑 검색 키워드", placeholder="예: 배터리, lithium ion")
    assignee = st.text_input("🏢 출원인 / 권리자", placeholder="예: 삼성SDI, LG Chem")
    ipc = st.text_input("📂 IPC 코드", placeholder="예: H01M 4/36")

    col1, col2 = st.columns(2)
    with col1:
        date_from = st.text_input("출원일 시작", value="2020")
    with col2:
        date_to = st.text_input("출원일 종료", value="2024")

    st.markdown("**검색 데이터베이스**")
    db_kipris = st.checkbox("🇰🇷 KIPRIS (한국)", value=True)
    db_uspto  = st.checkbox("🇺🇸 USPTO (미국)",  value=True)
    db_epo    = st.checkbox("🇪🇺 EPO (유럽)",    value=True)
    db_wipo   = st.checkbox("🌐 WIPO (국제)",    value=True)
    db_cnipa  = st.checkbox("🇨🇳 CNIPA (중국)",  value=False)

    use_demo = st.toggle("데모 데이터 사용 (API 키 없이)", value=True)

    search_btn = st.button("🔍 검색 시작", use_container_width=True, type="primary")

# ── 메인: 결과 ───────────────────────────────────────────────────────────
if search_btn:
    databases = []
    if db_kipris: databases.append("KIPRIS")
    if db_uspto:  databases.append("USPTO")
    if db_epo:    databases.append("EPO")
    if db_wipo:   databases.append("WIPO")
    if db_cnipa:  databases.append("CNIPA")

    if not databases:
        st.warning("데이터베이스를 하나 이상 선택하세요.")
        st.stop()

    with st.spinner("특허 서지정보 수집 중..."):
        patents = collect_patents(
            keyword=keyword, assignee=assignee, ipc=ipc,
            date_from=date_from, date_to=date_to,
            databases=databases, use_demo=use_demo,
        )

    if not patents:
        st.warning("검색 결과가 없습니다. 조건을 변경해 보세요.")
        st.stop()

    st.session_state["patents"] = patents
    st.session_state["keyword"] = keyword
    st.session_state["assignee"] = assignee

# 결과가 있을 때만 표시
if "patents" in st.session_state:
    patents  = st.session_state["patents"]
    keyword  = st.session_state.get("keyword", "")
    assignee = st.session_state.get("assignee", "")

    # 요약 지표
    from collections import Counter
    country_cnt  = Counter(p["country"]  for p in patents)
    assignee_cnt = Counter(p["assignee"] for p in patents)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("수집 특허", f"{len(patents)}건")
    m2.metric("국가 수",   f"{len(country_cnt)}개국")
    m3.metric("출원인 수", f"{len(assignee_cnt)}개사")
    m4.metric("총 피인용", f"{sum(p.get('citations',0) for p in patents)}회")

    st.divider()

    # 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs(["📋 서지정보 목록", "📊 특허지도", "⬇️ Excel 다운로드", "📄 보고서 다운로드"])

    # ── 탭1: 서지정보 목록 ──────────────────────────────────────────────
    with tab1:
        import pandas as pd

        FLAG = {"KR": "🇰🇷", "US": "🇺🇸", "EP": "🇪🇺", "WO": "🌐", "CN": "🇨🇳"}
        rows = []
        for p in patents:
            rows.append({
                "국가": FLAG.get(p["country"], p["country"]) + " " + p["country"],
                "출원번호": p["patent_number"],
                "발명의 명칭": p["title"],
                "출원인": p["assignee"],
                "IPC": p["ipc_codes"],
                "출원일": p["application_date"],
                "현황": p["status"],
                "피인용": p.get("citations", 0),
                "출처": p["db_source"],
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # 상세 보기
        st.subheader("상세 보기")
        sel = st.selectbox("특허 선택", [f"[{i+1}] {p['patent_number']} — {p['title'][:50]}" for i, p in enumerate(patents)])
        idx = int(sel.split("]")[0][1:]) - 1
        p = patents[idx]
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown(f"**출원번호:** {p['patent_number']}")
            st.markdown(f"**출원인:** {p['assignee']}")
            st.markdown(f"**발명자:** {p['inventors']}")
            st.markdown(f"**IPC:** {p['ipc_codes']}")
            st.markdown(f"**출원일:** {p['application_date']}")
            st.markdown(f"**현황:** {p['status']}")
        with c2:
            st.markdown(f"**발명의 명칭**")
            st.info(p["title"])
            st.markdown(f"**초록**")
            st.write(p.get("abstract", ""))

    # ── 탭2: 특허지도 ──────────────────────────────────────────────────
    with tab2:
        with st.spinner("특허지도 생성 중..."):
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                map_path = f.name
            create_patent_map(patents, map_path)

        st.image(map_path, use_container_width=True)

        with open(map_path, "rb") as f:
            st.download_button(
                "⬇️ 특허지도 PNG 다운로드",
                data=f.read(),
                file_name="특허지도.png",
                mime="image/png",
                use_container_width=True,
            )
        os.unlink(map_path)

    # ── 탭3: Excel ──────────────────────────────────────────────────────
    with tab3:
        st.markdown("출원번호, 출원인, 발명자, IPC, 초록 등 전체 서지정보 + 요약 통계 차트 포함")
        if st.button("📊 Excel 파일 생성", use_container_width=True):
            with st.spinner("Excel 생성 중..."):
                with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
                    xl_path = f.name
                create_patent_excel(patents, xl_path)
            with open(xl_path, "rb") as f:
                st.download_button(
                    "⬇️ 특허_서지정보.xlsx 다운로드",
                    data=f.read(),
                    file_name="특허_서지정보.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            os.unlink(xl_path)

    # ── 탭4: Word 보고서 ────────────────────────────────────────────────
    with tab4:
        st.markdown("조사 개요, 국가별·출원인별 현황 표, 특허 상세 서지정보, 분석 의견 포함")
        if st.button("📄 보고서 생성", use_container_width=True):
            with st.spinner("보고서 생성 중..."):
                with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
                    doc_path = f.name
                create_patent_report(patents, keyword, assignee, doc_path)
            with open(doc_path, "rb") as f:
                st.download_button(
                    "⬇️ 특허_조사보고서.docx 다운로드",
                    data=f.read(),
                    file_name="특허_조사보고서.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
            os.unlink(doc_path)
